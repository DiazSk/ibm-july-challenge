"""
Orchestrate router — single entry point for the multi-agent system.

POST /api/orchestrate          Run a full agent pipeline
GET  /api/orchestrate/memory-status  Debug: collection counts

Supported task_type values:
  single_caption   — parallel BrandVoice + Copywriting
  full_campaign    — hierarchical Copy → Critic loop → Visual + Analytics
  post_mortem      — sequential Analytics → Community
  trend_briefing   — parallel Trend + Analytics
  community_triage — flat Community alone
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import get_orchestrator, get_memory_store

router = APIRouter()


class OrchestrateRequest(BaseModel):
    task_type: str
    payload: dict = {}


class OrchestrateResponse(BaseModel):
    task_type:          str
    topology:           str
    results:            dict
    agents_used:        list[str]
    cycles:             int
    memory_written:     bool
    human_review_flag:  bool
    convergence_reason: str = "max_cycles"
    success:            bool
    error_message:      str | None = None


@router.post("", response_model=OrchestrateResponse)
def run_orchestration(
    req: OrchestrateRequest,
    orchestrator=Depends(get_orchestrator),
):
    result = orchestrator.run(req.task_type, req.payload)
    return OrchestrateResponse(
        task_type=result.task_type,
        topology=result.topology,
        results=result.results,
        agents_used=result.agents_used,
        cycles=result.cycles,
        memory_written=result.memory_written,
        human_review_flag=result.human_review_flag,
        convergence_reason=result.convergence_reason,
        success=result.success,
        error_message=result.error_message,
    )


@router.get("/memory-status")
def memory_status(memory_store=Depends(get_memory_store)):
    """Debug endpoint — returns ChromaDB collection counts."""
    return memory_store.status()
