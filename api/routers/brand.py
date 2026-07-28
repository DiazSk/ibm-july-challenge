"""
Brand data endpoints — static reads from data/ directory.
These are fast (pure JSON load) so they're defined as async.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_brand_drift_analyzer, get_sentence_embedder
from src.data.pillars import pillar_label

router = APIRouter()

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"



def _unique(items: list) -> list:
    seen: set = set()
    out: list = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _load_profile() -> dict:
    if not _PROFILE_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="brand_profile.json not found. Run `python run_pipeline.py` first.",
        )
    return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))


@router.get("/profile")
async def get_profile():
    raw = _load_profile()

    tone_descriptors : list[str] = []
    signature_phrases: list[str] = []
    avoided_terms    : list[str] = []
    recurring_words  : list[str] = []
    content_pillars  : list[str] = []

    for cp in raw.get("cluster_profiles", []):
        p = cp.get("profile", {})
        if p.get("parse_error"):
            continue
        pillar = pillar_label(cp["cluster_id"])
        if pillar and pillar not in content_pillars:
            content_pillars.append(pillar)
        tone_descriptors  += p.get("tone_descriptors", [])
        avoided_terms     += p.get("avoided_terms", [])
        voc = p.get("vocabulary_patterns", {})
        signature_phrases += voc.get("signature_phrases", [])
        recurring_words   += voc.get("recurring_words", [])

    return {
        "brand_name"      : raw["brand_name"],
        "handle"          : raw["ig_handle"],
        "timezone"        : raw.get("timezone") or "UTC",
        "content_pillars" : content_pillars,
        "tone_descriptors": _unique(tone_descriptors),
        "signature_phrases": _unique(signature_phrases),
        "avoided_terms"   : _unique(avoided_terms),
        "recurring_words" : _unique(recurring_words),
        "visual_style_notes": (
            "Warm, intimate home-kitchen atmosphere. "
            "Soft natural window light, muted warm tones — cream, caramel, chocolate brown. "
            "Artisanal textures and imperfect handmade details."
        ),
        "target_audience": (
            "Instagram dessert lovers seeking homemade artisanal cakes and bomboloni "
            "in Navi Mumbai."
        ),
    }


@router.get("/clusters")
async def get_clusters():
    if not _CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="clusters.json not found. Run `python run_pipeline.py` first.",
        )
    raw_clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))
    profile      = _load_profile()

    # Build a lookup: cluster_id → profile data
    profile_by_id: dict[int, dict] = {
        cp["cluster_id"]: cp
        for cp in profile.get("cluster_profiles", [])
    }

    result: dict[str, dict] = {}
    for cid_str, posts in raw_clusters.get("clusters", {}).items():
        cid = int(cid_str)
        cp  = profile_by_id.get(cid, {})
        p   = cp.get("profile", {})
        voc = p.get("vocabulary_patterns", {})
        result[cid_str] = {
            "cluster_id"      : cid,
            "pillar"          : pillar_label(cid),
            "post_count"      : cp.get("post_count", len(posts)),
            "tone_descriptors": p.get("tone_descriptors", []),
            "signature_phrases": voc.get("signature_phrases", []),
            "recurring_words" : voc.get("recurring_words", []),
            "avoided_terms"   : p.get("avoided_terms", []),
            "sample_captions" : [
                post["marketing_hook"] for post in posts[:3]
                if post.get("marketing_hook")
            ],
        }

    return result


class DriftCheckRequest(BaseModel):
    pasted_posts: list[str]


@router.post("/drift-check")
def check_brand_drift(req: DriftCheckRequest) -> dict:
    """
    Granite Call #19 — BrandDriftAnalyzer.
    Auto-detects the nearest content pillar for a pasted batch of recent
    posts (via embedding similarity, no manual cluster picker), then Granite
    explains specifically how the batch has drifted from that pillar's
    locked brand voice profile.
    """
    posts = [p.strip() for p in req.pasted_posts if p.strip()]
    if len(posts) < 3:
        raise HTTPException(status_code=422, detail="paste at least 3 recent posts to compare")

    if not _CLUSTERS_PATH.exists():
        raise HTTPException(status_code=503, detail="clusters.json not found")
    clusters_data = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))

    embedder = get_sentence_embedder()
    from src.generation.brand_drift import detect_nearest_cluster_and_signal

    nearest_cluster_id, similarity_signal = detect_nearest_cluster_and_signal(
        posts, clusters_data, embedder,
    )
    cluster_label = pillar_label(nearest_cluster_id)

    analysis = get_brand_drift_analyzer().analyze_drift(posts, nearest_cluster_id, similarity_signal)

    return {
        "nearest_cluster_id": nearest_cluster_id,
        "cluster_label": cluster_label,
        "similarity_signal": similarity_signal,
        **analysis,
    }
