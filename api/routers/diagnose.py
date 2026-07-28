"""
Diagnose tab — per-post diagnosis for the whole account.

Split by cost, the same way strategy.py does it:
  /posts             — pure Python, instant: every synced post grouped by pillar,
                       with a deterministic algorithm-weighted tier badge.
  /posts/{shortcode} — one Granite Why Engine call (~10s), disk-cached forever
                       after, so the page stays instant on re-expand.

Diagnoses persist to data/diagnoses/{shortcode}.json rather than workbench.db
(that table is user-facing and its PATCH triggers recovery jobs) and rather
than lru_cache alone (which evaporates on uvicorn --reload).
"""

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.dependencies import get_why_engine
from src.data.diagnose import (
    build_index, group_index, post_type_from_media, DIAGNOSES_DIR, SCRAPED_DIR,
)

router = APIRouter()

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"

# Marker WhyEngine writes when Granite returns unparseable JSON — never cache it.
_PARSE_FAIL = "Could not parse structured response."


def _load() -> tuple[dict, dict]:
    if not _PROFILE_PATH.exists() or not _CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Data files not found. Run `python run_pipeline.py` first.",
        )
    profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
    return profile, clusters


@lru_cache(maxsize=1)
def _posts() -> dict:
    profile, clusters = _load()
    rows = build_index(clusters, profile)
    return {"groups": group_index(rows, profile), "total": len(rows)}


@router.get("/posts")
def posts() -> dict:
    """Instant, no LLM: every synced post grouped by content pillar."""
    return _posts()


def _cache_path(shortcode: str) -> Path:
    return DIAGNOSES_DIR / f"{shortcode}.json"


def _read_cached(shortcode: str) -> dict | None:
    p = _cache_path(shortcode)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None  # corrupt cache → regenerate


def _scraped_record(shortcode: str) -> dict | None:
    p = SCRAPED_DIR / f"ig_text_{shortcode}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_row(shortcode: str) -> dict | None:
    for g in _posts()["groups"]:
        for r in g["posts"]:
            if r["shortcode"] == shortcode:
                return r
    return None


@router.get("/posts/{shortcode}/seed")
def post_seed(shortcode: str) -> dict:
    """
    Everything the script generator needs to build from an existing post.

    Exists so "write the fix" can be one click: the Create page used to make the
    creator paste a caption and hand-type six metric numbers for a post already
    stored in clusters.json. Instant — no LLM.
    """
    row = _find_row(shortcode)
    if not row:
        raise HTTPException(status_code=404, detail=f"Unknown post {shortcode}")

    rec = _scraped_record(shortcode) or {}
    content = rec.get("content") or {}
    # Prefer the cleaned hook (the line that actually did the work); fall back to
    # the raw caption for posts the pipeline never split.
    caption = (content.get("marketing_hook") or content.get("caption_raw") or "").strip()

    return {
        "shortcode" : shortcode,
        "caption"   : caption,
        "post_type" : row["post_type"],
        "cluster_id": row["cluster_id"],
        "metrics"   : {k: row[k] for k in ("reach", "views", "likes", "comments", "saves", "shares")},
    }


@router.get("/posts/{shortcode}")
def post_diagnosis(shortcode: str, force: bool = False) -> dict:
    """
    Granite Why Engine for one post — visual + caption + algorithm metrics.

    Cached on disk: first call ~10s, every later call instant. `force=true`
    re-runs and overwrites (use after metrics have moved).
    """
    if not force:
        cached = _read_cached(shortcode)
        if cached:
            return cached

    row = _find_row(shortcode)
    if not row:
        raise HTTPException(status_code=404, detail=f"Unknown post {shortcode}")

    rec = _scraped_record(shortcode)
    if not rec:
        raise HTTPException(status_code=404, detail=f"No scraped record for {shortcode}")
    content = rec.get("content") or {}

    caption = (content.get("caption_raw") or "").strip()
    if not caption:
        raise HTTPException(status_code=422, detail="Post has no caption to diagnose.")

    try:
        result = get_why_engine().analyze(
            caption            = caption,
            post_type          = row["post_type"],
            views              = row["views"],
            reach              = row["reach"],
            likes              = row["likes"],
            comments           = row["comments"],
            shares             = row["shares"],
            saves              = row["saves"],
            # Minimal-caption posts have no pillar; WhyEngine falls back to
            # cluster_profiles[0] for brand-voice context.
            cluster_id         = row["cluster_id"] if row["cluster_id"] is not None else 0,
            visual_description = content.get("visual_description", "") or "",
        )
    except Exception as exc:  # noqa: BLE001 — surface the model failure
        raise HTTPException(status_code=502, detail=f"Why Engine failed: {exc}")

    # Granite occasionally returns unparseable JSON; WhyEngine degrades to a stub
    # instead of raising. Don't persist that — leave no file so a retry can win.
    if not (result.get("diagnosis") or "").strip() or result.get("what_failed") == _PARSE_FAIL:
        raise HTTPException(status_code=502, detail="Granite returned an unparseable response. Try again.")

    payload = {
        **result,
        "shortcode"    : shortcode,
        "post_type"    : row["post_type"],
        "generated_at" : datetime.now(timezone.utc).isoformat(),
        "metrics_at_generation": {
            k: row[k] for k in ("reach", "views", "likes", "comments", "saves", "shares")
        },
    }
    try:
        DIAGNOSES_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(shortcode).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _posts.cache_clear()  # has_diagnosis flags are now stale
    except Exception:
        pass  # caching is best-effort; the diagnosis still returns

    return payload
