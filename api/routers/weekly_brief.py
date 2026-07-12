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

_CLUSTER_ID_LABELS = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
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


def _run_weekly_brief_pipeline(job_id: str, n: int) -> None:
    try:
        _update_job(job_id, 5, "Reviewing your content strategy...")
        profile = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
        clusters = json.loads(_CLUSTERS_PATH.read_text(encoding="utf-8"))

        from api.routers.discover import _compute_strategic_insights, _DEMO_ENGAGEMENT

        insights = _compute_strategic_insights()  # cached — free after first Discover visit
        underutilized_id = insights.get("underutilized_cluster")
        if underutilized_id is None:
            underutilized_id = 0

        cluster_profile = next(
            (cp for cp in profile["cluster_profiles"] if cp["cluster_id"] == underutilized_id),
            profile["cluster_profiles"][0],
        )
        cluster_label = _CLUSTER_ID_LABELS.get(underutilized_id, f"Cluster {underutilized_id}")
        tone = cluster_profile["profile"].get("tone_descriptors", [])
        cluster_context = (
            f"Pillar: {cluster_profile['profile'].get('content_pillar', '')}, "
            f"tone: {', '.join(tone) if tone else 'not specified'}. "
            f"This pillar is underutilized relative to how richly-developed its voice is."
        )

        _update_job(job_id, 12, f"Researching trends for {cluster_label}...")
        from src.generation.jarvis_agent import search_creators

        snippets = search_creators(cluster_label, niche=profile.get("brand_bio", "artisan bakery")[:40])

        _update_job(job_id, 20, "IBM Granite is planning this week's content...")
        from api.dependencies import (
            get_weekly_brief_planner,
            get_moment_analyzer,
            get_direction_generator,
            get_caption_generator,
            get_image_generator,
        )

        scenarios = get_weekly_brief_planner().generate(
            cluster_label=cluster_label,
            cluster_context=cluster_context,
            trend_snippets=snippets,
            brand_name=profile["brand_name"],
            n=n,
        )

        batch_id = str(uuid4())
        step = 65 // max(n, 1)

        for i, scenario in enumerate(scenarios):
            base = 25 + i * step
            scenario_text = scenario["scenario_text"]

            _update_job(job_id, base, f"Scenario {i + 1}/{n}: analyzing the moment...")
            moment_analysis = get_moment_analyzer().analyze(scenario_text)

            _update_job(job_id, base + step // 3, f"Scenario {i + 1}/{n}: creative direction...")
            directions = get_direction_generator().generate(moment_analysis, scenario_text)
            direction = directions[0] if directions else {}

            _update_job(job_id, base + 2 * step // 3, f"Scenario {i + 1}/{n}: writing captions...")
            best_cluster_id = moment_analysis.get("best_cluster_id", underutilized_id)
            captions = get_caption_generator().generate(
                product=direction.get("direction_title", cluster_label),
                occasion="Weekly content plan",
                desired_feel=direction.get("angle", "on-brand and engaging"),
                cluster_id=best_cluster_id,
            )
            caption_text = captions[0]["caption"] if captions else ""

            _update_job(job_id, base + step - 1, f"Scenario {i + 1}/{n}: image direction...")
            image = get_image_generator().generate(caption=caption_text, product=cluster_label)

            content = {
                "batch_id": batch_id,
                "scenario_index": i,
                "scenario_text": scenario_text,
                "rationale": scenario.get("rationale", ""),
                "caption": caption_text,
                "image_prompt": image.get("prompt", ""),
                "style_notes": image.get("style_notes", ""),
            }

            conn = _get_wb_conn()
            conn.execute(
                "INSERT INTO workbench_assets "
                "(id, asset_type, cluster_label, cluster_id, content, source_tab) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    "weekly_brief_draft",
                    cluster_label,
                    best_cluster_id,
                    json.dumps(content),
                    "weekly_brief",
                ),
            )
            conn.commit()
            conn.close()

        _jobs[job_id]["batch_id"] = batch_id
        _jobs[job_id]["cluster_label"] = cluster_label
        _jobs[job_id]["notified"] = False
        _update_job(job_id, 100, f"{len(scenarios)} drafts ready — open Workbench to review.", status="done")
    except Exception as exc:
        current_pct = _jobs.get(job_id, {}).get("progress", 0)
        _update_job(job_id, current_pct, str(exc), status="error")


class WeeklyBriefRequest(BaseModel):
    n: int = 2


@router.post("/generate")
def start_weekly_brief(req: WeeklyBriefRequest, background_tasks: BackgroundTasks) -> dict:
    n = max(1, min(req.n, 3))
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
