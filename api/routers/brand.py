"""
Brand data endpoints — static reads from data/ directory.
These are fast (pure JSON load) so they're defined as async.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"


@router.get("/profile")
async def get_profile():
    if not _PROFILE_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="brand_profile.json not found. Run `python run_pipeline.py` first.",
        )
    return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))


@router.get("/clusters")
async def get_clusters():
    if not _CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="clusters.json not found. Run `python run_pipeline.py` first.",
        )
    return json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
