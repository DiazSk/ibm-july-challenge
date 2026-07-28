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

from api.dependencies import (
    get_voice_timeline,
    get_strategic_insights,
    get_boost_advisor,
    get_confidence_scorer,
)
from src.data.pillars import all_pillar_labels

router = APIRouter()

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH  = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"

_ALL_CLUSTER_COLS = ["C0", "C1", "C2", "C3", "C4"]


# Synthesised engagement figures for clusters where real metrics are unavailable
# (Instagram official export provides captions only, not views/saves/comments).
# Numbers are plausible for a ~1,400-follower artisanal food account.
_DEMO_ENGAGEMENT: dict[str, dict] = {
    "0": {
        "cluster_name"   : "Homemade Classics",
        "post_count"     : 34,
        "avg_views"      : 780,
        "avg_saves"      : 24,
        "avg_comments"   : 5,
        "engagement_rate": 6.4,
        "best_post_hook" : (
            "100% Homemade eggless donuts — soft, fresh & chocolate-loaded 🍫🍩\n"
            "Made with love & fried to perfection ✨"
        ),
    },
    "1": {
        "cluster_name"   : "Fusion Specials",
        "post_count"     : 22,
        "avg_views"      : 1650,
        "avg_saves"      : 48,
        "avg_comments"   : 14,
        "engagement_rate": 11.2,
        "best_post_hook" : (
            "one bite of rasmalai cake & all diet plans got cancelled 😌✨ "
            "Soft. Milky. Royal. 💛"
        ),
    },
    "2": {
        "cluster_name"   : "Behind the Scenes",
        "post_count"     : 15,
        "avg_views"      : 1020,
        "avg_saves"      : 41,
        "avg_comments"   : 17,
        "engagement_rate": 9.6,
        "best_post_hook" : "I'll stick to baking… not voiceovers 😅  We all know 'tomorrow' never comes 🤍",
    },
    "3": {
        "cluster_name"   : "Nutella Series",
        "post_count"     : 15,
        "avg_views"      : 1920,
        "avg_saves"      : 56,
        "avg_comments"   : 11,
        "engagement_rate": 12.8,
        "best_post_hook" : (
            "Soft, gooey & loaded with rich Nutella in every bite 🤤🍪✨\n"
            "Freshly made & packed with love ❤️"
        ),
    },
    "4": {
        "cluster_name"   : "Bomboloni",
        "post_count"     : 27,
        "avg_views"      : 2140,
        "avg_saves"      : 63,
        "avg_comments"   : 9,
        "engagement_rate": 11.6,
        "best_post_hook" : (
            "There's something about freshly fried Bomboloni, hot coffee & old songs… "
            "it just feels like comfort in every bite ☕🍩🎶"
        ),
    },
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

    pillar_labels = {f"C{cid}": label for cid, label in all_pillar_labels().items()}

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

    # Instagram official export has no engagement metrics; fall back to demo values
    real_engagement = clusters.get("cluster_engagement")
    cluster_engagement = real_engagement or _DEMO_ENGAGEMENT

    si     = get_strategic_insights()
    scores = si.compute_richness_scores(profile, clusters)

    advisor = get_boost_advisor()
    result  = advisor.generate(scores, cluster_engagement, profile)
    # Be honest about where the numbers came from — Instagram's official export
    # ships captions only, so engagement is illustrative unless a richer source
    # supplied real metrics.
    result["engagement_is_synthetic"] = not real_engagement

    try:
        context_summary = (
            f"Boost recommendation for {result.get('boost_cluster_name', '')} "
            f"vs avoiding {result.get('dont_boost_cluster_name', '')}"
        )
        output_summary = result.get("reasoning", "")
        result["confidence"] = get_confidence_scorer().score(context_summary, output_summary)
    except Exception:
        pass  # non-fatal — confidence badge just won't render if this fails

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
    return _compute_boost_advisor()
