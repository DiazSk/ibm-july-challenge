"""
Instagram Graph API ingestion — the real-time replacement for the manual
Meta data-export (7-day wait) and the ban-prone public scrape.

The app user connects their own Business/Creator account via OAuth
("Instagram API with Instagram Login"). We then pull their media (and
engagement insights) on demand and write each post into scraped_dataset/ in
the EXACT schema parse_instagram_export / instaloader_scraper produce, so the
downstream 3-stage pipeline is completely unchanged.

Config (from .env / environment):
    IG_APP_ID, IG_APP_SECRET, IG_REDIRECT_URI

Self-check (no network):
    python src/scrapers/instagram_api.py
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

_PROJECT_ROOT   = Path(__file__).resolve().parent.parent.parent
_SCRAPED_DIR    = _PROJECT_ROOT / "scraped_dataset"
CONNECTION_PATH = _PROJECT_ROOT / "data" / "ig_connection.json"

# Instagram Login (graph.instagram.com) endpoints
_AUTH_URL       = "https://www.instagram.com/oauth/authorize"
_TOKEN_URL      = "https://api.instagram.com/oauth/access_token"
_GRAPH          = "https://graph.instagram.com"
_SCOPES         = "instagram_business_basic,instagram_business_manage_insights,instagram_business_manage_comments"

_MEDIA_FIELDS   = "id,caption,media_type,media_product_type,permalink,timestamp,media_url,thumbnail_url"
_PERMALINK_RE   = re.compile(r"instagram\.com/(?:p|reel|tv)/([^/?]+)", re.I)
_TIMEOUT        = 30


# ── Config / connection persistence ─────────────────────────────────────────

def _cfg(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"{name} is not set. Add it to your .env (see .env.example)."
        )
    return val


def load_connection() -> dict | None:
    """Return the saved connection dict, or None if not connected."""
    if not CONNECTION_PATH.exists():
        return None
    try:
        return json.loads(CONNECTION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_connection(conn: dict) -> None:
    CONNECTION_PATH.parent.mkdir(exist_ok=True)
    CONNECTION_PATH.write_text(
        json.dumps(conn, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def disconnect() -> None:
    CONNECTION_PATH.unlink(missing_ok=True)


# ── OAuth ────────────────────────────────────────────────────────────────────

def build_authorize_url() -> str:
    """URL to send the user to so they can authorize their IG account.

    force_reauth=true makes Instagram re-show the permissions screen instead of
    silently re-issuing previously granted scopes — required so a newly added
    scope (e.g. manage_comments) is actually presented and granted on reconnect.
    """
    params = {
        "client_id"    : _cfg("IG_APP_ID"),
        "redirect_uri" : _cfg("IG_REDIRECT_URI"),
        "response_type": "code",
        "scope"        : _SCOPES,
        "force_reauth" : "true",
    }
    return _AUTH_URL + "?" + "&".join(f"{k}={requests.utils.quote(v)}" for k, v in params.items())


def exchange_code(code: str) -> dict:
    """Exchange the OAuth ?code for a long-lived token; save + return the connection."""
    # 1. code → short-lived token (also returns the IG user id)
    resp = requests.post(
        _TOKEN_URL,
        data={
            "client_id"    : _cfg("IG_APP_ID"),
            "client_secret": _cfg("IG_APP_SECRET"),
            "grant_type"   : "authorization_code",
            "redirect_uri" : _cfg("IG_REDIRECT_URI"),
            "code"         : code.rstrip("#_"),  # IG appends #_ on redirect
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    short = resp.json()
    short_token = short["access_token"]
    ig_user_id  = str(short.get("user_id", ""))
    granted     = short.get("permissions", "")  # what the user actually consented to
    print(f"[connect] granted permissions: {granted}", file=sys.stderr)

    # 2. short-lived → long-lived (60 days)
    long_resp = requests.get(
        f"{_GRAPH}/access_token",
        params={
            "grant_type"   : "ig_exchange_token",
            "client_secret": _cfg("IG_APP_SECRET"),
            "access_token" : short_token,
        },
        timeout=_TIMEOUT,
    )
    long_resp.raise_for_status()
    long = long_resp.json()
    token      = long["access_token"]
    expires_in = int(long.get("expires_in", 60 * 24 * 3600))

    username = _fetch_username(token)
    conn = {
        "access_token"       : token,
        "ig_user_id"         : ig_user_id,
        "username"           : username,
        "token_expires_at"   : time.time() + expires_in,
        "last_sync_utc"      : None,
        "granted_permissions": granted,
    }
    save_connection(conn)
    return conn


def refresh_if_stale(conn: dict) -> dict:
    """Refresh the long-lived token if it expires within 7 days. Best-effort."""
    if time.time() < conn.get("token_expires_at", 0) - 7 * 24 * 3600:
        return conn
    try:
        resp = requests.get(
            f"{_GRAPH}/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": conn["access_token"]},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        conn["access_token"]     = data["access_token"]
        conn["token_expires_at"] = time.time() + int(data.get("expires_in", 60 * 24 * 3600))
        save_connection(conn)
    except Exception as exc:  # noqa: BLE001 — refresh is opportunistic
        print(f"Token refresh skipped: {exc}", file=sys.stderr)
    return conn


def _fetch_username(token: str) -> str:
    try:
        resp = requests.get(
            f"{_GRAPH}/me", params={"fields": "username", "access_token": token}, timeout=_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json().get("username", "")
    except Exception:
        return ""


# ── Fetching ──────────────────────────────────────────────────────────────────

def fetch_media(token: str, since: float | None = None) -> list[dict]:
    """Fetch media items from /me/media, paginating. `since` is a Unix timestamp."""
    params = {"fields": _MEDIA_FIELDS, "access_token": token, "limit": 50}
    if since:
        params["since"] = int(since)
    url = f"{_GRAPH}/me/media"
    items: list[dict] = []
    while url:
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        items.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        params = {}  # `next` is a fully-formed URL
    return items


def fetch_insights(token: str, media_id: str, media_product_type: str) -> dict:
    """Best-effort engagement metrics for one media item. Returns {} on any error."""
    is_reel = (media_product_type or "").upper() == "REELS"
    metrics = "reach,likes,comments,saved,shares" + (",views" if is_reel else "")
    try:
        resp = requests.get(
            f"{_GRAPH}/{media_id}/insights",
            params={"metric": metrics, "access_token": token},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        out = {}
        for row in resp.json().get("data", []):
            vals = row.get("values") or [{}]
            out[row["name"]] = vals[0].get("value")
        return out
    except Exception:
        return {}


# ── Comments (inbox triage) ─────────────────────────────────────────────────

def _fetch_media_with_counts(token: str) -> list[dict]:
    """/me/media with comments_count — one paginated pass, no per-media calls."""
    params = {"fields": "id,permalink,timestamp,comments_count", "access_token": token, "limit": 50}
    url = f"{_GRAPH}/me/media"
    items: list[dict] = []
    while url:
        resp = requests.get(url, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        items.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        params = {}
    return items


def fetch_recent_comments(token: str, media_limit: int = 15, cap: int = 20,
                          own_username: str = "") -> list[dict]:
    """
    Top-level comments across the posts that actually have comments, newest first.

    Skips empty comments and the owner's own replies. Raises PermissionError if
    posts have comments (comments_count > 0) but the Comments API returns none —
    that's how a token missing the instagram_business_manage_comments scope
    behaves (silent 200 with empty data, not a 403), so the router can prompt
    re-auth instead of falsely reporting "no comments."
    """
    media = _fetch_media_with_counts(token)
    total_expected = sum(int(m.get("comments_count") or 0) for m in media)
    have = [m for m in media if int(m.get("comments_count") or 0) > 0]
    have.sort(key=lambda m: m.get("timestamp", ""), reverse=True)

    own = (own_username or "").lstrip("@").lower()
    out: list[dict] = []
    raw_seen = 0
    for m in have[:media_limit]:
        resp = requests.get(
            f"{_GRAPH}/{m['id']}/comments",
            params={"fields": "id,text,username,timestamp", "access_token": token, "limit": 50},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()  # explicit 400/403 also bubbles to the router
        data = resp.json().get("data", [])
        raw_seen += len(data)
        permalink = m.get("permalink") or ""
        shortcode = _shortcode_from_permalink(permalink)
        for c in data:
            text = (c.get("text") or "").strip()
            uname = (c.get("username") or "").lstrip("@")
            if not text or (own and uname.lower() == own):
                continue
            out.append({
                "id"             : c.get("id", ""),
                "text"           : text,
                "username"       : uname,
                "timestamp"      : c.get("timestamp", ""),
                "media_permalink": permalink,
                "media_shortcode": shortcode,
            })
        if len(out) >= cap:
            break

    if raw_seen == 0 and total_expected > 0:
        raise PermissionError("comments exist but the API returned none (missing manage_comments scope)")

    out.sort(key=lambda c: c["timestamp"], reverse=True)
    return out[:cap]


def reply_to_comment(token: str, comment_id: str, message: str) -> dict:
    """Post a public reply to a comment. Returns {"id": <new comment id>}."""
    resp = requests.post(
        f"{_GRAPH}/{comment_id}/replies",
        data={"message": message, "access_token": token},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ── Mapping ────────────────────────────────────────────────────────────────────

def _shortcode_from_permalink(permalink: str) -> str:
    m = _PERMALINK_RE.search(permalink or "")
    return m.group(1) if m else ""


def _map_to_canonical(media: dict, account: str, engagement: dict | None = None) -> dict:
    """Map a Graph API media item to the scraped_dataset/ schema (see ig_scraper.py)."""
    caption   = media.get("caption") or ""
    permalink = media.get("permalink") or ""
    shortcode = _shortcode_from_permalink(permalink)
    ts        = media.get("timestamp") or ""  # already ISO-8601 from the API
    data = {
        "source_url"   : permalink or (f"https://www.instagram.com/p/{shortcode}/" if shortcode else ""),
        "shortcode"    : shortcode,
        "owner_id"     : "",
        "author"       : account,
        "timestamp_utc": ts,
        "content": {
            "caption_raw"       : caption,
            "hashtags"          : re.findall(r"#(\w+)", caption),
            "mentions"          : re.findall(r"@(\w+)", caption),
            "accessibility_text": "",
            # Media for the vision preprocessor. URLs are short-lived CDN links,
            # so the vision backfill must run right after sync (see sync_account).
            "media_type"        : media.get("media_type", ""),
            "media_url"         : media.get("media_url", ""),
            "thumbnail_url"     : media.get("thumbnail_url", ""),
        },
    }
    if engagement:
        # Extra key ignored by the caption-driven pipeline; available for later
        # wiring into episodic memory / the why-engine.
        data["engagement"] = engagement
    return data


# ── Sync ───────────────────────────────────────────────────────────────────────

def sync_account(full: bool = False) -> int:
    """
    Fetch new posts from the connected account, write them into
    scraped_dataset/, then re-run the 3-stage pipeline so brand_profile.json
    reflects the latest content. Returns the number of new posts written.

    full=True  → clear scraped_dataset/ and re-fetch everything (initial sync).
    full=False → incremental: only fetch media newer than last_sync_utc,
                 keeping already-converted files (dedup by shortcode filename).
    """
    conn = load_connection()
    if not conn:
        raise RuntimeError("No Instagram account connected. Authorize one first.")
    conn  = refresh_if_stale(conn)
    token = conn["access_token"]

    _SCRAPED_DIR.mkdir(exist_ok=True)
    if full:
        for f in _SCRAPED_DIR.glob("ig_text_*.json"):
            f.unlink()

    since = None if full else conn.get("last_sync_utc")
    media = fetch_media(token, since=since)

    written = 0
    for m in media:
        shortcode = _shortcode_from_permalink(m.get("permalink", ""))
        file_id   = shortcode or m.get("id", "")
        if not file_id:
            continue
        out = _SCRAPED_DIR / f"ig_text_{file_id}.json"
        if out.exists() and not full:
            continue
        engagement = fetch_insights(token, m["id"], m.get("media_product_type", ""))
        record = _map_to_canonical(m, conn.get("username") or "my_account", engagement)
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        written += 1

    # Vision preprocessing: describe each post's image/Reel frames while Granite
    # is idle (media URLs are short-lived, so this must run now, before the
    # text pipeline). Additive — never block the build if the vision model is
    # missing or a media URL is dead.
    if written or full:
        try:
            from src.generation.vision_describer import backfill_descriptions
            backfill_descriptions(_SCRAPED_DIR)
        except Exception as exc:  # noqa: BLE001
            print(f"vision backfill skipped: {exc}", file=sys.stderr)

    # Refresh derived artifacts only if there is anything to (re)build.
    if written or full:
        from run_pipeline import run_full_pipeline
        handle = f"@{conn.get('username')}" if conn.get("username") else "@my_account"
        brand_name = (conn.get("username") or "my_account").replace("_", " ").title()
        run_full_pipeline(brand_name=brand_name, handle=handle)

    conn["last_sync_utc"] = time.time()
    save_connection(conn)
    return written


# ── Offline self-check ──────────────────────────────────────────────────────────

def _demo() -> None:
    assert _shortcode_from_permalink("https://www.instagram.com/p/ABC123/") == "ABC123"
    assert _shortcode_from_permalink("https://www.instagram.com/reel/XyZ_9/?igsh=1") == "XyZ_9"
    assert _shortcode_from_permalink("") == ""

    media = {
        "id": "1789",
        "caption": "Fresh bakes today! #bread @flourfriend",
        "permalink": "https://www.instagram.com/p/ABC123/",
        "timestamp": "2026-07-20T10:00:00+0000",
        "media_product_type": "FEED",
    }
    rec = _map_to_canonical(media, "hot_cakesbakes", {"reach": 500, "likes": 42})
    assert rec["shortcode"] == "ABC123"
    assert rec["author"] == "hot_cakesbakes"
    assert rec["content"]["caption_raw"].startswith("Fresh bakes")
    assert rec["content"]["hashtags"] == ["bread"]
    assert rec["content"]["mentions"] == ["flourfriend"]
    assert set(rec["content"]) == {
        "caption_raw", "hashtags", "mentions", "accessibility_text",
        "media_type", "media_url", "thumbnail_url",
    }
    # media fields default to "" when the API omits them (as in this fixture)
    assert rec["content"]["media_url"] == "" and rec["content"]["media_type"] == ""
    assert rec["engagement"] == {"reach": 500, "likes": 42}
    print("instagram_api self-check passed.")


if __name__ == "__main__":
    _demo()
