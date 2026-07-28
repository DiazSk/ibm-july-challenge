"""
Insights tab endpoint — the real content-analytics dashboard.

Derives headline KPIs, a top-posts leaderboard, engagement-by-pillar, and a
best-time-to-post grid from the real per-post metrics now carried through
clusters.json. Pure aggregation (no LLM), cached like discover.py so repeated
dashboard loads are instant; the cache is cleared on re-sync via
onboard._clear_caches.
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.data.insights import compute_overview

router = APIRouter()

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"


@lru_cache(maxsize=1)
def _compute_overview_cached() -> dict:
    if not _CLUSTERS_PATH.exists() or not _PROFILE_PATH.exists():
        raise HTTPException(status_code=404, detail="No brand profile yet. Connect or onboard an account first.")
    clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
    profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    return compute_overview(clusters, profile)


@router.get("/overview")
def overview():
    """Headline KPIs, top posts, engagement-by-pillar, and best-time grid."""
    return _compute_overview_cached()
