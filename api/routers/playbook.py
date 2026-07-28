"""
Self-Improving Playbook router.

POST /api/playbook/reflect          Run the reflection agent (background) → job_id
GET  /api/playbook/reflect/{job_id} Poll for {learned, rules, applied, ...}
GET  /api/playbook/rules            The current procedural playbook the copywriter follows

ponytail: in-memory job store, demo scale (same pattern as recovery/agent_run).
"""

import threading
import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_memory_store, get_playbook_agent
from src.memory.outcomes import gather_tagged_outcomes

router = APIRouter()

_jobs: dict[str, dict] = {}


@router.post("/reflect")
def reflect() -> dict:
    agent = get_playbook_agent()
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}

    def worker():
        try:
            winners, losers = gather_tagged_outcomes()
            _jobs[job_id]["result"] = agent.reflect(winners, losers)
            _jobs[job_id]["status"] = "done"
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)

    threading.Thread(target=worker, daemon=True).start()
    return {"job_id": job_id}


@router.get("/reflect/{job_id}")
def reflect_status(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]


@router.get("/rules")
def current_rules(memory=Depends(get_memory_store)) -> list[dict]:
    """The procedural playbook CopywritingAgent reads on every generation."""
    hits = memory.search_procedural("instagram caption content rule", n_results=12)
    return [
        {
            "rule_name": h.metadata.get("rule_name"),
            "text": h.text,
            "source": h.metadata.get("source", "seed"),
        }
        for h in hits
    ]
