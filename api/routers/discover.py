"""
Discover tab endpoints — Voice Timeline + Strategic Insights.

Both endpoints are computationally expensive (Granite calls + data processing)
but the inputs never change within a session (data files are static).
Results are cached via functools.lru_cache so Granite runs exactly once —
the first request triggers computation (~60-120s on CPU), every subsequent
request returns the cached result instantly.

Use plain `def` (not async) because VoiceTimeline and StrategicInsights
both make synchronous Ollama calls.
"""

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.dependencies import get_voice_timeline, get_strategic_insights, get_boost_advisor

router = APIRouter()

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"

_ALL_CLUSTER_COLS = ["C0", "C1", "C2", "C3", "C4"]

_CLUSTER_ID_LABELS = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}


@lru_cache(maxsize=1)
def _compute_voice_timeline() -> dict:
    profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))

    vt = get_voice_timeline()
    pct_df, raw_counts = vt.compute_monthly_distribution(clusters)

    # Ensure all 5 cluster columns exist (some months may lack certain clusters)
    for col in _ALL_CLUSTER_COLS:
        if col not in pct_df.columns:
            pct_df[col] = 0.0

    pct_df = pct_df[_ALL_CLUSTER_COLS]

    # Convert to list of records for Recharts
    monthly_pct = [
        {"month": month, **{col: float(row[col]) for col in _ALL_CLUSTER_COLS}}
        for month, row in pct_df.iterrows()
    ]

    narrative_result = vt.narrate_evolution(raw_counts, profile)

    pillar_labels = {f"C{cid}": label for cid, label in _CLUSTER_ID_LABELS.items()}

    return {
        "monthly_pct"  : monthly_pct,
        "narrative"    : narrative_result.get("narrative", ""),
        "key_shift"    : narrative_result.get("key_shift", ""),
        "pillar_labels": pillar_labels,
    }


@lru_cache(maxsize=1)
def _compute_strategic_insights() -> dict:
    profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))

    si      = get_strategic_insights()
    scores  = si.compute_richness_scores(profile, clusters)
    tensions = si.detect_tensions(scores)
    brief   = si.generate_strategy_brief(scores, tensions, profile)

    return {
        "scores"               : scores,
        "tensions"             : tensions,
        "strategic_brief"      : brief.get("strategic_brief", ""),
        "experiment"           : brief.get("experiment", ""),
        "underutilized_cluster": brief.get("underutilized_cluster"),
        "overused_cluster"     : brief.get("overused_cluster"),
    }


@router.get("/voice-timeline")
def voice_timeline() -> dict:
    """
    Granite Call #5 — VoiceTimeline.
    Returns monthly cluster distribution percentages + narrative.
    Cached after first call.
    """
    if not _PROFILE_PATH.exists() or not _CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Data files not found. Run `python run_pipeline.py` first.",
        )
    return _compute_voice_timeline()


@router.get("/strategic-insights")
def strategic_insights() -> dict:
    """
    Granite Call #8 — StrategicInsights.
    Returns richness scores, tensions, strategy brief, experiment.
    Cached after first call.
    """
    if not _PROFILE_PATH.exists() or not _CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Data files not found. Run `python run_pipeline.py` first.",
        )
    return _compute_strategic_insights()


@lru_cache(maxsize=1)
def _compute_boost_advisor() -> dict:
    profile  = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))

    cluster_engagement = clusters.get("cluster_engagement", {})
    if not cluster_engagement:
        raise ValueError(
            "No cluster_engagement data found. "
            "Run the pipeline with demo data or add engagement data to clusters.json."
        )

    # Reuse already-computed richness scores (cached) if available, else compute fresh
    si     = get_strategic_insights()
    scores = si.compute_richness_scores(profile, clusters)

    advisor = get_boost_advisor()
    result  = advisor.generate(scores, cluster_engagement, profile)
    return result


@router.get("/boost-advisor")
def boost_advisor() -> dict:
    """
    Granite Call #11 — BoostAdvisor.
    Returns recommendation for which post/cluster to boost on Instagram.
    Cached after first call.
    """
    if not _PROFILE_PATH.exists() or not _CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Data files not found. Run `python run_pipeline.py` first.",
        )
    try:
        return _compute_boost_advisor()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
