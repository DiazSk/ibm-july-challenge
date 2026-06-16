"""
Analyze tab endpoint — Why Engine post-mortem.

Uses plain `def` because WhyEngine.analyze() is a synchronous Ollama call.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_why_engine, get_recovery_brief_generator

router = APIRouter()


class WhyEngineRequest(BaseModel):
    caption: str
    post_type: str                       # "Reel" | "Carousel" | "Static Photo"
    views: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    avg_watch_time_secs: Optional[float] = None
    cluster_id: int = 0


@router.post("/why-engine")
def run_why_engine(req: WhyEngineRequest) -> dict:
    """
    Granite Call #4 — WhyEngine.
    Returns verdict, diagnosis, what_worked, what_failed,
    brand_voice_gap, change_next_time, verdict_label.
    """
    if not req.caption.strip():
        raise HTTPException(status_code=422, detail="caption is required")
    result = get_why_engine().analyze(
        caption             = req.caption.strip(),
        post_type           = req.post_type,
        views               = req.views,
        reach               = req.reach,
        likes               = req.likes,
        comments            = req.comments,
        shares              = req.shares,
        saves               = req.saves,
        avg_watch_time_secs = req.avg_watch_time_secs,
        cluster_id          = req.cluster_id,
    )
    if result.get("verdict", "").lower() in ("underperformed", "failed"):
        try:
            recovery = get_recovery_brief_generator().generate(
                diagnosis       = result.get("diagnosis", ""),
                what_failed     = result.get("what_failed", ""),
                brand_voice_gap = result.get("brand_voice_gap", ""),
                cluster_id      = req.cluster_id,
            )
            result["recovery_brief"] = recovery
        except Exception:
            pass  # non-fatal — Why Engine result returns even if this fails
    return result
