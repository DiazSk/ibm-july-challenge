"""
Analyze tab endpoint — Why Engine post-mortem.

Uses plain `def` because WhyEngine.analyze() is a synchronous Ollama call.
"""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api.dependencies import get_why_engine, get_recovery_brief_generator, get_confidence_scorer
from api.routers.repurpose import run_repurpose_pipeline, _jobs as _repurpose_jobs

router = APIRouter()

_CLUSTER_ID_LABELS = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}


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
def run_why_engine(req: WhyEngineRequest, background_tasks: BackgroundTasks) -> dict:
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

    try:
        context_summary = (
            f"Post type: {req.post_type}; views={req.views} reach={req.reach} "
            f"likes={req.likes} comments={req.comments} shares={req.shares} saves={req.saves}"
        )
        output_summary = f"Verdict: {result.get('verdict', '')}. {result.get('diagnosis', '')}"
        result["confidence"] = get_confidence_scorer().score(context_summary, output_summary)
    except Exception:
        pass  # non-fatal — confidence badge just won't render if this fails

    # Closed-Loop Repurposing Orchestrator: a success auto-fans-out into
    # Reel/Carousel/Static drafts in the background, no user click needed.
    if result.get("verdict", "").lower() == "succeeded":
        try:
            job_id = str(uuid4())
            _repurpose_jobs[job_id] = {"status": "queued", "progress": 0, "message": "Starting..."}
            metrics = {
                "views": req.views, "reach": req.reach, "likes": req.likes,
                "comments": req.comments, "shares": req.shares, "saves": req.saves,
            }
            cluster_label = _CLUSTER_ID_LABELS.get(req.cluster_id, f"Cluster {req.cluster_id}")
            background_tasks.add_task(
                run_repurpose_pipeline, job_id, req.caption.strip(), metrics, req.cluster_id, cluster_label,
            )
            result["repurpose_job_id"] = job_id
        except Exception:
            pass  # non-fatal — Why Engine result returns even if this fails to kick off

    return result
