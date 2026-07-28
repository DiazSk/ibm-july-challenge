"""
StyleSync FastAPI application.

Run:
    uvicorn api.main:app --reload --port 8000

Interactive API docs:
    http://localhost:8000/docs
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # read IG_* (and any other) secrets from .env into the environment

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import brand, create, analyze, discover, onboard, workbench, agent, voice, repurpose, weekly_brief, triage, orchestrate, agent_run, recovery, playbook, connect, insights, strategy, inbox, diagnose, today


async def _instagram_poll_loop() -> None:
    """
    Keep the connected account's brand profile fresh by polling Instagram on
    an interval. Instagram has no reliable 'new post' webhook, so polling is
    the only real option.

    ponytail: single in-process loop, single account. Move to a real
    worker/cron if this goes multi-tenant or needs durability across restarts.
    """
    interval = int(os.getenv("IG_POLL_INTERVAL_SECS", str(3 * 3600)))
    from src.scrapers.instagram_api import load_connection
    from api.routers.connect import run_sync_and_refresh
    while True:
        await asyncio.sleep(interval)
        if not load_connection():
            continue
        try:
            written = await asyncio.get_event_loop().run_in_executor(None, run_sync_and_refresh, False)
            print(f"[ig-poll] sync complete — {written} new post(s).")
        except Exception as exc:  # noqa: BLE001 — a failed poll must not kill the loop
            print(f"[ig-poll] sync failed: {exc}", file=sys.stderr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_instagram_poll_loop())
    yield
    task.cancel()


app = FastAPI(
    title       = "StyleSync API",
    description = "Creative Intelligence Platform — IBM Granite-powered endpoints",
    version     = "2.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins       = ["http://localhost:3000", "http://127.0.0.1:3000"],
    # VS Code port-forwarding (Dev Tunnels) serves the app from a random
    # "<id>-3000.<region>.devtunnels.ms" origin each session — match the
    # domain instead of hardcoding a URL that changes every time.
    allow_origin_regex  = r"https://.*\.devtunnels\.ms",
    allow_credentials   = True,
    allow_methods       = ["*"],
    allow_headers       = ["*"],
)

app.include_router(today.router,    prefix="/api/today",    tags=["Today"])
app.include_router(onboard.router,  prefix="/api/onboard",  tags=["Onboard"])
app.include_router(connect.router,  prefix="/api/connect",  tags=["Connect"])
app.include_router(insights.router, prefix="/api/insights", tags=["Insights"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["Strategy"])
app.include_router(diagnose.router, prefix="/api/diagnose", tags=["Diagnose"])
app.include_router(inbox.router,    prefix="/api/inbox",    tags=["Inbox"])
app.include_router(brand.router,    prefix="/api/brand",    tags=["Brand"])
app.include_router(create.router,   prefix="/api/create",   tags=["Create"])
app.include_router(analyze.router,  prefix="/api/analyze",  tags=["Analyze"])
app.include_router(discover.router,   prefix="/api/discover",   tags=["Discover"])
app.include_router(workbench.router,  prefix="/api/workbench",  tags=["Workbench"])
app.include_router(agent.router,      prefix="/api/agent",      tags=["Agent"])
app.include_router(voice.router,      prefix="/api/voice",      tags=["Voice"])
app.include_router(repurpose.router,  prefix="/api/repurpose",  tags=["Repurpose"])
app.include_router(weekly_brief.router, prefix="/api/weekly-brief", tags=["Weekly Brief"])
app.include_router(triage.router,       prefix="/api/triage",       tags=["Triage"])
app.include_router(orchestrate.router,  prefix="/api/orchestrate",  tags=["Orchestrate"])
app.include_router(agent_run.router,    prefix="/api/agent-run",    tags=["Autopilot"])
app.include_router(recovery.router,     prefix="/api/recovery",     tags=["Recovery"])
app.include_router(playbook.router,     prefix="/api/playbook",     tags=["Playbook"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "StyleSync API"}
