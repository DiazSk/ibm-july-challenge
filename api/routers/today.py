"""
Today tab — the daily creator briefing.

The capabilities this composes already existed; what was missing was the
assembly. `derive_moves`, `rank_posts`, the Why Engine and the Trend Agent lived
on four different pages, so answering "what do I post today?" meant visiting all
four and holding the answer in your head.

Split by cost, the same way strategy.py and diagnose.py do it:
  /              — pure Python, instant: today's move, its format, and the
                   in-pillar reference post the script gets seeded from.
  /trend         — Granite (Trend Agent), slow, cached: first-party trend read.

The performance lesson is NOT re-derived here — the page lazy-loads the existing
/api/strategy/diagnoses, which is already cached, so the Why Engine runs once per
process no matter how many pages ask for it.
"""

from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter

from api.routers.strategy import _load, _overview
from src.data.strategy import best_post_in_pillar

router = APIRouter()

# Which format serves which job. Instagram rewards Reels for discovery and
# carousels for saved, returnable value, so the move's lever picks the format
# rather than asking the creator to decide. Deterministic — no LLM.
_FORMAT_FOR_LEVER = {
    "sends"      : "Reel",
    "saves"      : "Carousel",
    "consistency": "Reel",
}

_WHY_FORMAT = {
    "Reel"    : "Reels are Instagram's discovery surface — this move is about reach.",
    "Carousel": "Carousels earn saves, which is what this move is trying to grow.",
}


def _local_now(profile: dict) -> datetime:
    """Now in the brand's timezone — 'today' must mean the creator's today."""
    try:
        return datetime.now(ZoneInfo(profile.get("timezone") or "UTC"))
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now(ZoneInfo("UTC"))


@router.get("")
def today() -> dict:
    """Instant, no LLM: today's single recommendation + its seed post."""
    profile, clusters = _load()
    ov = _overview()
    now = _local_now(profile)

    moves = ov.get("moves") or []
    if not moves:
        return {
            "date": now.date().isoformat(), "weekday": now.strftime("%A"),
            "recommendation": None, "seed_post": None,
            "posts_counted": ov["scorecard"]["posts_counted"],
        }

    move = moves[0]
    fmt  = _FORMAT_FOR_LEVER.get(move.get("lever"), "Reel")

    # Seed from the best post *inside the pillar the move names*, so the script
    # hand-off is consistent with the recommendation above it. Falls back to the
    # account-wide winner when that pillar has nothing usable.
    cid  = move.get("cluster_id")
    seed = (best_post_in_pillar(clusters, profile, cid) if cid is not None
            else ov["what_worked"].get("winner"))

    return {
        "date"          : now.date().isoformat(),
        "weekday"       : now.strftime("%A"),
        "recommendation": {**move, "format": fmt, "why_format": _WHY_FORMAT.get(fmt, "")},
        "seed_post"     : seed,
        "other_moves"   : moves[1:],
        "posts_counted" : ov["scorecard"]["posts_counted"],
    }


@lru_cache(maxsize=1)
def _trend() -> dict:
    """
    First-party trend read: pillar velocity + the account's own comments.

    There is no external trend feed behind this — the Trend Agent is explicit
    about which signals it used, and returns empty lists rather than inventing
    trends when it has none. The response carries that provenance through so the
    UI can say so plainly.
    """
    from api.dependencies import get_trend_agent
    from src.agents.base import AgentTask

    profile, _ = _load()
    try:
        res = get_trend_agent().run(AgentTask(
            task_type="trend_briefing",
            payload={"niche": profile.get("brand_bio", "artisan bakery")[:60]},
        ))
    except Exception as exc:  # noqa: BLE001 — a dead trend read must not kill the briefing
        return {"available": False, "reason": str(exc)}

    if not res.success:
        return {"available": False, "reason": res.error_message or "Trend agent failed."}
    return {"available": True, **(res.output or {})}


@router.get("/trend")
def trend() -> dict:
    """Granite Trend Agent, first-party signals only. Cached after first call."""
    return _trend()
