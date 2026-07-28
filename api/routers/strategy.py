"""
Strategy tab endpoints — performance-first, algorithm-grounded.

Split by cost so the page has immediate value and Granite is progressive:
  /overview   — pure Python, instant: scorecard + timeline + moves + winner/loser.
  /diagnoses  — Granite (Why Engine ×2), slow, cached: why the winner/loser landed.
  /brief      — Granite, slow, cached: warm plain-English strategic brief.

All results are static within a session (data files don't change), so each is
memoised with lru_cache — Granite runs once, later requests are instant.
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.dependencies import get_why_engine, get_strategic_insights
from src.data.strategy import (
    compute_algo_scorecard, monthly_timeseries, rank_posts, derive_moves,
)

router = APIRouter()

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
_SCRAPED_DIR   = _PROJECT_ROOT / "scraped_dataset"


def _visual_descriptions() -> dict[str, str]:
    """{shortcode: visual_description} from scraped_dataset, for the Why Engine."""
    out: dict[str, str] = {}
    if not _SCRAPED_DIR.exists():
        return out
    for f in _SCRAPED_DIR.glob("ig_text_*.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        sc  = rec.get("shortcode", "")
        vd  = rec.get("content", {}).get("visual_description", "")
        if sc and vd:
            out[sc] = vd
    return out


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
def _overview() -> dict:
    profile, clusters = _load()
    scorecard = compute_algo_scorecard(clusters, profile)
    ranked    = rank_posts(clusters, profile)
    return {
        "scorecard"  : scorecard,
        "timeline"   : monthly_timeseries(clusters, profile),
        "moves"      : derive_moves(scorecard["by_pillar"], ranked),
        "what_worked": ranked,
    }


@lru_cache(maxsize=1)
def _diagnoses() -> dict:
    ranked = _overview()["what_worked"]
    we = get_why_engine()
    vds = _visual_descriptions()

    total = _overview()["scorecard"]["posts_counted"]

    def diag(post: dict | None, peer_context: str = "") -> dict | None:
        if not post:
            return None
        return we.analyze(
            caption            = post["hook"],  # only the hook is stored per post; it's the key line
            post_type          = "Reel",
            views              = post["views"],
            reach              = post["reach"],
            likes              = post["likes"],
            comments           = post["comments"],
            shares             = post["shares"],
            saves              = post["saves"],
            cluster_id         = post["cluster_id"],
            visual_description = vds.get(post.get("shortcode", ""), ""),
            peer_context       = peer_context,
        )

    return {
        "winner_diagnosis": diag(
            ranked.get("winner"),
            f"This is the single BEST performing post out of {total} — it ranks #1 for "
            "share-throughs per person reached. Explain what made it work; do not call it "
            "underperforming.",
        ),
        "loser_diagnosis" : diag(
            ranked.get("loser"),
            f"This post reached real people but ranks LAST of {total} for share-throughs "
            "per person reached. Explain what held it back.",
        ),
    }


@lru_cache(maxsize=1)
def _brief() -> dict:
    profile, _ = _load()
    ov = _overview()
    si = get_strategic_insights()
    return si.generate_performance_brief(
        ov["scorecard"]["by_pillar"], ov["moves"], profile["brand_name"]
    )


@router.get("/overview")
def overview() -> dict:
    """Instant, pure-Python: scorecard, performance timeline, moves, winner/loser."""
    return _overview()


@router.get("/diagnoses")
def diagnoses() -> dict:
    """Granite Why Engine on the auto-selected winner + loser. Cached after first call."""
    return _diagnoses()


@router.get("/brief")
def brief() -> dict:
    """Granite performance brief + experiment. Cached after first call."""
    return _brief()
