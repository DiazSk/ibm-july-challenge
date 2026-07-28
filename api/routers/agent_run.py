"""
Autonomous agent run — start / poll / answer.

POST /api/agent-run/start        Kick off a Weekly Autopilot run (background thread)
GET  /api/agent-run/{job_id}     Poll live status + reasoning trace + results
POST /api/agent-run/{job_id}/answer   Answer the agent's question so it can resume

The agent runs in a background thread and streams its reasoning into job["trace"].
When it hits a genuine strategic fork it calls ask_user, which flips the job to
"awaiting_input" and BLOCKS on a threading.Event until /answer fires it — real
pause/resume, not a flag.

ponytail: in-memory job store + threading.Event, single-server demo scale (same
pattern as onboard/weekly-brief). Move to a real task queue if multi-worker.
"""

import threading
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import get_autopilot

router = APIRouter()

_JOBS: dict[str, dict] = {}
_ANSWER_TIMEOUT_SECS = 600  # a never-answered run resumes with no answer rather than hanging forever


class StartRequest(BaseModel):
    steer: str = ""
    target_count: int = 3
    platform: str = "instagram"
    confidence_threshold: int = 75


class AnswerRequest(BaseModel):
    answer: str


def _public(job: dict) -> dict:
    """Job view without the internal threading.Event."""
    return {
        "status": job["status"],
        "trace": job["trace"],
        "reasoning": job["reasoning"],
        "posts": job["posts"],
        "summary": job["summary"],
        "pending_question": job["pending_question"],
        "error": job["error"],
    }


def start_autopilot_job(
    steer: str = "",
    target_count: int = 3,
    platform: str = "instagram",
    confidence_threshold: int = 75,
) -> str:
    """
    Kick off a Weekly Autopilot run in a background thread and return its job_id.
    Shared by the /start endpoint and by JARVIS (voice) so both start the same
    kind of resumable, pollable run against the same in-memory job store.
    """
    job_id = uuid.uuid4().hex[:12]
    job = {
        "status": "running",
        "trace": [],
        "reasoning": "",
        "posts": [],
        "summary": "",
        "pending_question": None,
        "answer": None,
        "answer_event": threading.Event(),
        "error": None,
    }
    _JOBS[job_id] = job
    pilot = get_autopilot()

    def worker():
        try:
            def trace_cb(entry: dict):
                job["trace"].append(entry)

            def ask_user_cb(question: str, options: list[str]) -> str:
                job["pending_question"] = {"question": question, "options": options}
                job["status"] = "awaiting_input"
                job["answer_event"].wait(timeout=_ANSWER_TIMEOUT_SECS)
                job["answer_event"].clear()
                job["pending_question"] = None
                job["status"] = "running"
                return job["answer"] or ""

            result = pilot.run(
                steer=steer,
                target_count=target_count,
                platform=platform,
                confidence_threshold=confidence_threshold,
                trace=trace_cb,
                ask_user=ask_user_cb,
            )
            job["reasoning"] = result["reasoning"]
            job["posts"] = result["posts"]
            job["summary"] = result["summary"]
            job["status"] = "done"
        except Exception as exc:  # never leave a thread crashing silently
            job["error"] = str(exc)
            job["status"] = "error"

    threading.Thread(target=worker, daemon=True).start()
    return job_id


@router.post("/start")
def start_run(req: StartRequest) -> dict:
    return {"job_id": start_autopilot_job(
        steer=req.steer,
        target_count=req.target_count,
        platform=req.platform,
        confidence_threshold=req.confidence_threshold,
    )}


@router.get("/{job_id}")
def get_run(job_id: str) -> dict:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return _public(job)


@router.post("/{job_id}/answer")
def answer_run(job_id: str, req: AnswerRequest) -> dict:
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    if job["status"] != "awaiting_input":
        raise HTTPException(status_code=409, detail="Agent is not awaiting input")
    job["answer"] = req.answer
    job["answer_event"].set()
    return {"status": "ok"}
