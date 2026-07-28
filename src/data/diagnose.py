"""
Per-post diagnosis index — pure Python, no LLM.

Builds one row per synced post so the Diagnose page can list the whole account
instantly, then fetch the expensive Granite narrative lazily per post.

The instant half is a deterministic **algorithm score** using the same weighting
the rest of the app ranks by (sends-per-reach × 3 + saves-per-reach × 1, see
src/data/strategy.py). That is what fills the tier badge; the LLM verdict is a
separate, slower thing and the two are labelled differently in the UI because
they can legitimately disagree.

Posts fall into two kinds:
  - clustered (have a content pillar, from clusters.json)
  - "minimal caption" — real caption + metrics + visual description, but
    pipeline.py skipped them for clustering because the extracted hook was
    < 15 chars (hashtag/emoji-only copy). Still diagnosable; grouped separately
    rather than given a fabricated pillar.

Reuses src/data/insights.py for metric plumbing (_num, _has_metrics, _rate,
_pillar_names).

Self-check (no network):
    python src/data/diagnose.py
"""

import json
import sys
from pathlib import Path

# Make `src` importable when run standalone (uvicorn already does this).
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data.insights import _num, _has_metrics, _rate, _pillar_names

# Same 3:1 sends:saves weighting strategy.py ranks by.
_WEIGHT_SENDS = 3.0
_WEIGHT_SAVES = 1.0

SCRAPED_DIR    = _ROOT / "scraped_dataset"
DIAGNOSES_DIR  = _ROOT / "data" / "diagnoses"

MINIMAL_GROUP = "minimal_caption"

# Graph API media_type → the post_type the Why Engine prompt expects.
_POST_TYPES = {
    "VIDEO"          : "Reel",
    "CAROUSEL_ALBUM" : "Carousel",
    "IMAGE"          : "Static",
}


def post_type_from_media(media_type: str) -> str:
    """VIDEO→Reel, CAROUSEL_ALBUM→Carousel, IMAGE→Static. Unknown→Static.

    Matters because the benchmarks differ: watch-time and replay-ratio lines
    only make sense for Reels.
    """
    return _POST_TYPES.get((media_type or "").upper(), "Static")


def weighted_score(eng: dict) -> float:
    """Algorithm-weighted score: sends-per-reach ×3 + saves-per-reach ×1."""
    reach = _num(eng.get("reach"))
    if reach <= 0:
        return 0.0
    return (_num(eng.get("shares")) / reach) * _WEIGHT_SENDS + \
           (_num(eng.get("saves")) / reach) * _WEIGHT_SAVES


def tier(score: float, median: float, has_metrics: bool) -> str:
    """Deterministic performance tier, relative to this account's median."""
    if not has_metrics:
        return "No data"
    if median <= 0:                 # degenerate account (no shares/saves at all)
        return "Solid" if score > 0 else "Weak"
    if score >= 2 * median:
        return "Top"
    if score >= median:
        return "Solid"
    return "Weak"


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def _load_scraped(scraped_dir: Path) -> dict[str, dict]:
    """{shortcode: record} from scraped_dataset — the source of caption + visual."""
    out: dict[str, dict] = {}
    for f in scraped_dir.glob("ig_text_*.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        sc = rec.get("shortcode", "")
        if sc:
            out[sc] = rec
    return out


def has_diagnosis(shortcode: str, diagnoses_dir: Path = DIAGNOSES_DIR) -> bool:
    return (diagnoses_dir / f"{shortcode}.json").exists()


def build_index(
    clusters      : dict,
    brand_profile : dict,
    scraped_dir   : Path = SCRAPED_DIR,
    diagnoses_dir : Path = DIAGNOSES_DIR,
) -> list[dict]:
    """One row per synced post (clustered and not), newest first."""
    names   = _pillar_names(brand_profile)
    scraped = _load_scraped(scraped_dir)

    # shortcode → cluster_id for the clustered posts, and their engagement
    # (clusters.json carries the normalised metrics the rest of the app reads).
    cmap: dict[str, int] = {sc: int(cid) for sc, cid in (clusters.get("cluster_map") or {}).items()}
    eng_by_sc: dict[str, dict] = {}
    hook_by_sc: dict[str, str] = {}
    for cid, posts in (clusters.get("clusters") or {}).items():
        for p in posts:
            sc = p.get("shortcode", "")
            if not sc:
                continue
            eng_by_sc[sc]  = p.get("engagement") or {}
            hook_by_sc[sc] = p.get("marketing_hook", "") or ""

    rows: list[dict] = []
    for sc, rec in scraped.items():
        content = rec.get("content") or {}
        # clusters.json metrics win (normalised "saved"→"saves"); fall back to raw.
        eng = eng_by_sc.get(sc) or dict(rec.get("engagement") or {})
        if "saved" in eng and "saves" not in eng:
            eng["saves"] = eng.pop("saved")

        cid       = cmap.get(sc)
        metrics   = _has_metrics({"engagement": eng})
        reach     = _num(eng.get("reach"))
        score     = weighted_score(eng)
        caption   = (content.get("caption_raw") or "").strip()

        rows.append({
            "shortcode"       : sc,
            "cluster_id"      : cid,
            "pillar"          : names.get(cid, "Minimal caption") if cid is not None else "Minimal caption",
            "group_key"       : str(cid) if cid is not None else MINIMAL_GROUP,
            "caption"         : caption,
            "hook"            : hook_by_sc.get(sc, "") or caption[:200],
            "timestamp_utc"   : rec.get("timestamp_utc", ""),
            "permalink"       : rec.get("source_url", ""),
            "media_type"      : content.get("media_type", ""),
            "post_type"       : post_type_from_media(content.get("media_type", "")),
            "reach"           : round(reach),
            "views"           : round(_num(eng.get("views"))),
            "likes"           : round(_num(eng.get("likes"))),
            "comments"        : round(_num(eng.get("comments"))),
            "saves"           : round(_num(eng.get("saves"))),
            "shares"          : round(_num(eng.get("shares"))),
            "sends_per_reach" : round(_num(eng.get("shares")) / reach * 100, 2) if reach else 0.0,
            "saves_per_reach" : round(_num(eng.get("saves")) / reach * 100, 2) if reach else 0.0,
            "engagement_rate" : _rate(eng),
            "has_metrics"     : metrics,
            "score"           : round(score, 4),
            "has_diagnosis"   : has_diagnosis(sc, diagnoses_dir),
        })

    med = _median([r["score"] for r in rows if r["has_metrics"]])
    for r in rows:
        r["tier"] = tier(r["score"], med, r["has_metrics"])

    rows.sort(key=lambda r: r.get("timestamp_utc", ""), reverse=True)
    return rows


def group_index(rows: list[dict], brand_profile: dict) -> list[dict]:
    """Group rows into the 5 pillars (by cluster_id) then minimal-caption last.

    Clusters 2 and 4 carry near-identical pillar names in this account, so the
    post count is part of the label to keep the groups distinguishable.
    """
    names = _pillar_names(brand_profile)
    buckets: dict[str, list[dict]] = {}
    for r in rows:
        buckets.setdefault(r["group_key"], []).append(r)

    def sort_key(k: str) -> tuple:
        return (1, 0) if k == MINIMAL_GROUP else (0, int(k))

    groups = []
    for key in sorted(buckets, key=sort_key):
        posts = sorted(buckets[key], key=lambda r: r["score"], reverse=True)
        is_min = key == MINIMAL_GROUP
        cid = None if is_min else int(key)
        groups.append({
            "group_key"  : key,
            "cluster_id" : cid,
            "pillar"     : "Minimal caption" if is_min else names.get(cid, f"Cluster {cid}"),
            "note"       : ("Real captions but no hook copy (hashtags/emoji only), so these have no "
                            "content pillar. Still fully diagnosable — but their brand-voice "
                            "comparison falls back to your main pillar, so read that section "
                            "loosely.") if is_min else "",
            "post_count" : len(posts),
            "posts"      : posts,
        })
    return groups


def _demo() -> None:
    """Runnable self-check against the real data files."""
    profile  = json.loads((_ROOT / "data" / "brand_profile.json").read_text(encoding="utf-8"))
    clusters = json.loads((_ROOT / "data" / "clusters.json").read_text(encoding="utf-8"))

    # media → post_type
    assert post_type_from_media("VIDEO") == "Reel"
    assert post_type_from_media("CAROUSEL_ALBUM") == "Carousel"
    assert post_type_from_media("IMAGE") == "Static"
    assert post_type_from_media("") == "Static"

    # tier boundaries
    assert tier(0.0, 1.0, False) == "No data"
    assert tier(2.0, 1.0, True) == "Top"
    assert tier(1.0, 1.0, True) == "Solid"
    assert tier(0.5, 1.0, True) == "Weak"

    # weighted score: 3 shares + 1 save on 100 reach → 3*(0.03) + 1*(0.01)
    assert abs(weighted_score({"reach": 100, "shares": 3, "saves": 1}) - 0.10) < 1e-9
    assert weighted_score({"reach": 0, "shares": 5}) == 0.0

    rows = build_index(clusters, profile)
    n_scraped = len(list(SCRAPED_DIR.glob("ig_text_*.json")))
    assert len(rows) == n_scraped, f"{len(rows)} rows vs {n_scraped} scraped files"

    pillared = [r for r in rows if r["cluster_id"] is not None]
    minimal  = [r for r in rows if r["cluster_id"] is None]
    assert len(pillared) + len(minimal) == len(rows)
    assert all(r["tier"] in ("Top", "Solid", "Weak", "No data") for r in rows)
    assert all(r["post_type"] in ("Reel", "Carousel", "Static") for r in rows)

    groups = group_index(rows, profile)
    assert sum(g["post_count"] for g in groups) == len(rows)
    assert groups[-1]["group_key"] == MINIMAL_GROUP, "minimal-caption group must sort last"

    tiers = {}
    for r in rows:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    print(f"OK — {len(rows)} rows ({len(pillared)} pillared, {len(minimal)} minimal-caption)")
    print(f"   groups: {[(g['pillar'], g['post_count']) for g in groups]}")
    print(f"   tiers : {tiers}")
    print(f"   types : ", {t: sum(1 for r in rows if r['post_type'] == t) for t in ('Reel', 'Carousel', 'Static')})


if __name__ == "__main__":
    _demo()
