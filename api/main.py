"""
StyleSync FastAPI application.

Run:
    uvicorn api.main:app --reload --port 8000

Interactive API docs:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import brand, create, analyze, discover, onboard, workbench, agent, voice, repurpose, weekly_brief, triage

app = FastAPI(
    title       = "StyleSync API",
    description = "Creative Intelligence Platform — IBM Granite-powered endpoints",
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(onboard.router,  prefix="/api/onboard",  tags=["Onboard"])
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "StyleSync API"}
