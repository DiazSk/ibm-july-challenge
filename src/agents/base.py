"""
Base types and abstract class for all StyleSync specialized agents.

Every agent:
  - Receives an AgentTask (task_type + payload + optional memory handle)
  - Returns an AgentResult (output dict + optional typed error for CriticAgent)
  - Can write episodes to shared memory via _write_episode()
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

OLLAMA_MODEL = "granite3.1-dense:8b"

# Error types produced by CriticAgent — each maps to a specific routing target.
ERROR_TYPES = frozenset({
    "ai_slop",         # → CopywritingAgent.rewrite
    "off_brand_vocab", # → BrandVoiceAgent.enforce
    "wrong_platform",  # → CopywritingAgent.reformat
    "factual_gap",     # → human review flag (no auto-route)
    "approved",        # → no action needed
})

ROUTING_TARGETS: dict[str, str | None] = {
    "ai_slop":         "CopywritingAgent",
    "off_brand_vocab": "BrandVoiceAgent",
    "wrong_platform":  "CopywritingAgent",
    "factual_gap":     None,
    "approved":        None,
}


@dataclass
class AgentTask:
    task_type: str
    payload: dict = field(default_factory=dict)
    session_id: str | None = None


@dataclass
class AgentResult:
    agent_name: str
    output: dict = field(default_factory=dict)
    # CriticAgent populates these; other agents leave them None
    error_type: str | None = None
    routing_target: str | None = None
    memory_written: bool = False
    success: bool = True
    error_message: str | None = None


class BaseAgent(ABC):
    """Abstract base for all StyleSync specialized agents."""

    name: str = "base"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        self._model  = model
        self._memory = memory  # AgentMemoryStore | None

    @abstractmethod
    def run(self, task: AgentTask) -> AgentResult:
        ...

    def safe_run(self, task: AgentTask) -> AgentResult:
        """Wraps run() so the orchestrator never crashes on a single agent failure."""
        try:
            return self.run(task)
        except Exception as exc:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error_message=str(exc),
            )

    def _write_episode(self, caption: str, cluster_id: int, outcome: str) -> str | None:
        """Write a campaign outcome to episodic memory if store is available."""
        if self._memory is None:
            return None
        return self._memory.upsert_episode(caption, cluster_id, outcome)
