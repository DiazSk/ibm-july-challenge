"""
Weekly Brief Agent — proactive content planning.

Background job that: (1) finds the creator's underutilized-but-rich content
cluster from the already-cached Strategic Insights, (2) researches real web
trends for it, (3) proposes n content scenarios (Granite #17), (4) runs each
scenario through the existing, unmodified Blank Page Solver -> Caption ->
Image Direction chain, (5) lands the finished drafts directly in the
Workbench. No scheduler exists in this codebase, so this is on-demand
triggered (FastAPI BackgroundTasks), not truly recurring — see NEW-FEATURES.md.

A lightweight "pending notice" flag lets JARVIS proactively greet the founder
with a finished brief the next time the widget opens, instead of only
surfacing it as a passive Dashboard banner.
"""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"
_CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
_DB_PATH = _PROJECT_ROOT / "data" / "workbench.db"

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


def _run_weekly_brief_pipeline(job_id: str, n: int) -> None:
    try:
        _update_job(job_id, 5, "Reviewing your content strategy...")
        profile = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))

        from api.routers.discover import _compute_strategic_insights

        insights = _compute_strategic_insights()  # cached — free after first Discover visit
        underutilized_id = insights.get("underutilized_cluster")
        if underutilized_id is None:
            underutilized_id = 0

        # Real pillar names from the brand profile (not hardcoded demo labels).
        pillar_labels = {
            cp["cluster_id"]: cp["profile"].get("content_pillar", f"Cluster {cp['cluster_id']}")
            for cp in profile["cluster_profiles"]
        }
        cluster_profile = next(
            (cp for cp in profile["cluster_profiles"] if cp["cluster_id"] == underutilized_id),
            profile["cluster_profiles"][0],
        )
        cluster_label = pillar_labels.get(underutilized_id, f"Cluster {underutilized_id}")
        tone = cluster_profile["profile"].get("tone_descriptors", [])
        cluster_context = (
            f"tone: {', '.join(tone) if tone else 'not specified'}. "
            f"This pillar is underutilized relative to how richly-developed its voice is."
        )

        # What actually worked / flopped for this creator (Workbench tags).
        from src.memory.outcomes import gather_tagged_outcomes
        winners, losers = gather_tagged_outcomes()

        _update_job(job_id, 20, f"Researching trends for {cluster_label}...")
        from api.dependencies import get_trend_agent, get_weekly_brief_planner
        from src.agents.base import AgentTask

        trend_angles = []
        try:
            trend_result = get_trend_agent().run(AgentTask(
                task_type="trend_briefing",
                payload={"niche": profile.get("brand_bio", "artisan bakery")[:60], "topic": cluster_label},
            ))
            if trend_result.success:
                trend_angles = (trend_result.output or {}).get("suggested_angles", [])
        except Exception:
            trend_angles = []  # network/LLM failure → planner leans on winner + pillar

        _update_job(job_id, 45, "IBM Granite is planning this week's content...")
        cards = get_weekly_brief_planner().generate(
            cluster_label=cluster_label,
            cluster_context=cluster_context,
            pillar_labels=pillar_labels,
            winners=winners,
            losers=losers,
            trend_angles=trend_angles,
            brand_name=profile["brand_name"],
            underutilized_id=underutilized_id,
            n=n,
        )

        _update_job(job_id, 80, "Saving your weekly slate...")
        batch_id = str(uuid4())
        conn = _get_wb_conn()
        for i, card in enumerate(cards):
            content = {
                "batch_id": batch_id,
                "scenario_index": i,
                "scenario_text": card["scenario_text"],
                "rationale": card.get("rationale", ""),
                "format": card.get("format", "Reel"),
                "source": card.get("source", "pillar"),
            }
            conn.execute(
                "INSERT INTO workbench_assets "
                "(id, asset_type, cluster_label, cluster_id, content, source_tab) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    "weekly_brief_draft",
                    card.get("pillar", cluster_label),
                    card.get("cluster_id", underutilized_id),
                    json.dumps(content),
                    "weekly_brief",
                ),
            )
        conn.commit()
        conn.close()

        _jobs[job_id]["batch_id"] = batch_id
        _jobs[job_id]["cluster_label"] = cluster_label
        _jobs[job_id]["notified"] = False
        _update_job(job_id, 100, f"{len(cards)} content ideas ready — open Workbench to review.", status="done")
    except Exception as exc:
        current_pct = _jobs.get(job_id, {}).get("progress", 0)
        _update_job(job_id, current_pct, str(exc), status="error")


class WeeklyBriefRequest(BaseModel):
    n: int = 5


@router.post("/generate")
def start_weekly_brief(req: WeeklyBriefRequest, background_tasks: BackgroundTasks) -> dict:
    n = max(3, min(req.n, 7))
    job_id = str(uuid4())
    _jobs[job_id] = {"status": "queued", "progress": 0, "message": "Starting...", "n": n}
    background_tasks.add_task(_run_weekly_brief_pipeline, job_id, n)
    return {"job_id": job_id}


@router.get("/status/{job_id}")
def get_weekly_brief_status(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]


@router.get("/pending-notice")
def get_pending_notice() -> dict:
    """
    Returns the most recently completed, not-yet-surfaced job (if any), then
    immediately marks it as notified so it only ever surfaces once. Used by
    JarvisWidget to proactively greet the founder on next open.
    """
    candidates = [
        (job_id, job)
        for job_id, job in _jobs.items()
        if job.get("status") == "done" and job.get("notified") is False
    ]
    if not candidates:
        return {"pending": False}

    job_id, job = candidates[-1]
    job["notified"] = True
    return {
        "pending": True,
        "job_id": job_id,
        "batch_id": job.get("batch_id"),
        "n": job.get("n", 0),
        "cluster_label": job.get("cluster_label", "your content"),
    }
