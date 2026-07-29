"""
Closed-Loop Repurposing Orchestrator.

Fans one caption out to every ScriptGenerator format (Reel/Carousel/Static/Story)
as a background job, landing the drafts directly in the Workbench. No new Granite
classes.

Two entry points:
  • automatic — /api/analyze/why-engine fires it when a verdict is "succeeded"
  • on demand — the creator asks for it after a shoot, without waiting for a post
    to be published and graded first. One bake produces a week of formats, which
    was the whole point; gating it on a "succeeded" verdict meant she could only
    repurpose content that was already out and already working.

Runs as a FastAPI BackgroundTask (same pattern as onboard.py's pipeline — no
scheduler/cron infrastructure exists in this codebase) because the sequential
script-generation calls take several minutes on this hardware.
"""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.data.pillars import pillar_label

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "workbench.db"

_FORMATS = ("Reel", "Carousel", "Static", "Story")
_ASSET_TYPE_FOR_FORMAT = {
    "Reel": "reel_script",
    "Carousel": "carousel",
    "Static": "static_script",
    "Story": "story_script",
}

# In-memory job store (single-server, demo-scale — same pattern as onboard.py)
_jobs: dict[str, dict] = {}


def _update_job(job_id: str, pct: int, message: str, status: str = "running") -> None:
    existing = _jobs.get(job_id, {})
    _jobs[job_id] = {**existing, "progress": pct, "message": message, "status": status}


def _get_wb_conn() -> sqlite3.Connection:
    """Lightweight workbench DB connection — same schema/pattern as agent.py's helper."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workbench_assets (
            id           TEXT PRIMARY KEY,
            asset_type   TEXT NOT NULL,
            cluster_label TEXT,
            cluster_id   INTEGER,
            content      TEXT NOT NULL,
            pinned       INTEGER NOT NULL DEFAULT 0,
            source_tab   TEXT,
            actual_outcome       TEXT,
            recovery_brief_generated INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def run_repurpose_pipeline(
    job_id: str,
    caption: str,
    metrics: dict,
    cluster_id: int,
    cluster_label: str,
) -> None:
    """
    Fans a successful caption out to all 3 ScriptGenerator formats, writing
    each result directly into workbench_assets as it completes.
    """
    try:
        from api.dependencies import get_script_generator

        generator = get_script_generator()
        batch_id = str(uuid4())
        step = 90 // len(_FORMATS)

        for i, fmt in enumerate(_FORMATS):
            _update_job(job_id, 5 + i * step, f"Drafting the {fmt} version...")
            script = generator.generate(
                reference_caption=caption,
                metrics=metrics,
                content_format=fmt,
                cluster_id=cluster_id,
            )
            content = {**script, "batch_id": batch_id, "reference_caption": caption}

            conn = _get_wb_conn()
            conn.execute(
                "INSERT INTO workbench_assets "
                "(id, asset_type, cluster_label, cluster_id, content, source_tab) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    _ASSET_TYPE_FOR_FORMAT[fmt],
                    cluster_label,
                    cluster_id,
                    json.dumps(content),
                    "closed_loop_repurpose",
                ),
            )
            conn.commit()
            conn.close()

        _jobs[job_id]["batch_id"] = batch_id
        _update_job(job_id, 100, f"{len(_FORMATS)} formats ready — check Workbench.", status="done")
    except Exception as exc:
        current_pct = _jobs.get(job_id, {}).get("progress", 0)
        _update_job(job_id, current_pct, str(exc), status="error")


class RepurposeRequest(BaseModel):
    caption: str
    cluster_id: int = 0
    # Optional: a just-shot bake has no metrics yet. The formats don't need them —
    # they only colour the reference framing in the ScriptGenerator prompt.
    views: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0


@router.post("")
def start_repurpose(req: RepurposeRequest, background_tasks: BackgroundTasks) -> dict:
    """
    Start a fan-out on demand, without waiting for a post to be published and
    graded "succeeded" by the Why Engine.

    This is the entry point for "I just finished a bake" — the case the automatic
    trigger structurally cannot serve, since it needs a live post with metrics.
    """
    caption = req.caption.strip()
    if not caption:
        raise HTTPException(status_code=422, detail="caption is required")

    job_id = str(uuid4())
    _jobs[job_id] = {"status": "queued", "progress": 0, "message": "Starting…"}
    background_tasks.add_task(
        run_repurpose_pipeline,
        job_id,
        caption,
        {"views": req.views, "reach": req.reach, "likes": req.likes,
         "comments": req.comments, "shares": req.shares, "saves": req.saves},
        req.cluster_id,
        pillar_label(req.cluster_id),
    )
    return {"job_id": job_id, "formats": list(_FORMATS)}


@router.get("/status/{job_id}")
def get_repurpose_status(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]
