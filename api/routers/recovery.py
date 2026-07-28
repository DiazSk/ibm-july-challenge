"""
Autonomous Recovery Agent.

Proactive, unprompted: when the creator tags a Workbench post "underperformed"
or "failed", this agent kicks off on its own (via the workbench PATCH endpoint)
and:

  1. DIAGNOSE  — runs the Why Engine on the caption (why did it flop?).
  2. DECIDE    — if the diagnosis is confident, salvage it; if it can't diagnose
                 clearly, it ESCALATES (flags for human review) instead of
                 fabricating a fix — "act autonomously, ask when unsure".
  3. RECOVER   — produces a fresh recovery post via the orchestrator's
                 produce_post pipeline, steered by the diagnosis, and drops it
                 in the Workbench.

Runs as a FastAPI BackgroundTask (same pattern as repurpose.py). A single
latest-recovery notice is exposed so JARVIS can announce it proactively.

ponytail: in-memory job store + single latest notice, demo scale.
"""

import json
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "data" / "workbench.db"

_jobs: dict[str, dict] = {}
# Most-recent completed recovery, surfaced once to JARVIS then cleared on read.
_notice: dict = {"pending": False}


def _extract_caption(content) -> str:
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content
    if isinstance(content, dict):
        return str(content.get("caption") or content.get("hook") or "")
    return ""


def _wb_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_recovery(
    job_id: str,
    original_caption: str,
    cluster_id: int,
    cluster_label: str | None,
) -> None:
    """Diagnose → decide → recover. Never raises (records error in job)."""
    global _notice
    try:
        from api.dependencies import get_orchestrator, get_why_engine

        _jobs[job_id] = {"status": "running", "message": "Diagnosing the post…"}

        why = get_why_engine().analyze(
            caption=original_caption, post_type="Static",
            views=0, reach=0, likes=0, comments=0, shares=0, saves=0,
            cluster_id=cluster_id,
        )
        diagnosis = str(why.get("diagnosis", "")).strip()
        change = str(why.get("change_next_time", "")).strip()

        # DECIDE — escalate rather than fabricate if the diagnosis is too thin.
        if len(diagnosis) < 25 or not change:
            _jobs[job_id] = {"status": "needs_review", "message": "Diagnosis unclear — flagged for your review."}
            _notice = {
                "pending": True, "needs_review": True,
                "original_caption": original_caption[:160],
                "cluster_label": cluster_label,
            }
            return

        # RECOVER — steer a fresh post by what the Why Engine said to change.
        _jobs[job_id] = {"status": "running", "message": "Producing a recovery post…"}
        post = get_orchestrator().produce_post({
            "product": original_caption[:100],
            "occasion": "Recovery post — fix the diagnosed weakness",
            "desired_feel": f"Fix this: {change}",
            "cluster_id": cluster_id,
            "platform": "instagram",
            "confidence_threshold": 75,
        })
        recovery_caption = post.get("draft", "")
        confidence = (post.get("confidence", {}) or {}).get("score")

        conn = _wb_conn()
        conn.execute(
            "INSERT INTO workbench_assets "
            "(id, asset_type, cluster_label, cluster_id, content, source_tab) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()), "recovery_post", cluster_label, cluster_id,
                json.dumps({
                    "caption": recovery_caption,
                    "diagnosis": diagnosis,
                    "change_next_time": change,
                    "confidence": confidence,
                    "image_prompt": (post.get("image_prompt", {}) or {}).get("prompt", ""),
                    "original_caption": original_caption,
                }),
                "recovery_agent",
            ),
        )
        conn.commit()
        conn.close()

        _jobs[job_id] = {"status": "done", "message": "Recovery post ready in Workbench."}
        _notice = {
            "pending": True, "needs_review": False,
            "original_caption": original_caption[:160],
            "recovery_caption": recovery_caption[:200],
            "confidence": confidence,
            "cluster_label": cluster_label,
        }
    except Exception as exc:
        _jobs[job_id] = {"status": "error", "message": str(exc)}


def start_recovery_job(
    caption: str,
    cluster_id: int | None = 0,
    cluster_label: str | None = None,
) -> str:
    """Start a diagnose→recover run in a background thread; returns the job_id.
    Shared by the workbench outcome trigger and by JARVIS (voice)."""
    job_id = uuid4().hex[:12]
    _jobs[job_id] = {"status": "queued", "message": "Recovery queued."}
    threading.Thread(
        target=run_recovery,
        args=(job_id, caption, int(cluster_id or 0), cluster_label),
        daemon=True,
    ).start()
    return job_id


def trigger_recovery(
    outcome: str,
    content,
    cluster_id: int | None,
    cluster_label: str | None,
) -> bool:
    """Called by the workbench PATCH endpoint. Returns True if a run was started."""
    if outcome not in ("underperformed", "failed"):
        return False
    caption = _extract_caption(content)
    if not caption:
        return False
    start_recovery_job(caption, cluster_id, cluster_label)
    return True


def latest_unrecovered_flop() -> tuple[str, int, str | None] | None:
    """Most recent underperformed/failed post not itself a recovery. For JARVIS
    'fix my last flop' with no caption given. Returns (caption, cluster_id, label)."""
    try:
        conn = _wb_conn()
        rows = conn.execute(
            "SELECT content, cluster_id, cluster_label FROM workbench_assets "
            "WHERE actual_outcome IN ('underperformed','failed') "
            "AND source_tab != 'recovery_agent' ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        conn.close()
    except Exception:
        return None
    for r in rows:
        caption = _extract_caption(r["content"])
        if caption:
            return caption, int(r["cluster_id"] or 0), r["cluster_label"]
    return None


@router.get("/pending-notice")
def pending_notice() -> dict:
    """Return the latest recovery notice once, then clear the pending flag."""
    global _notice
    notice = dict(_notice)
    _notice = {"pending": False}
    return notice


@router.get("/status/{job_id}")
def recovery_status(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]
