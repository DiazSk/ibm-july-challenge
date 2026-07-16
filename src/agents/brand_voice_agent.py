"""
Brand Voice Agent — wraps BrandDriftAnalyzer and VoiceRefiner.

Responsibilities:
  - detect_drift:        Check whether a batch of posts has drifted from brand guidelines
  - enforce_vocabulary:  Refine a single caption to fix vocabulary/tone issues (called by
                         the orchestrator when CriticAgent routes error_type=off_brand_vocab)
  - refine_voice:        Polish a raw transcript into an on-brand caption

Adds over the raw generators:
  - Reads semantic memory before each call to enrich the brand voice context
  - Writes a corrected episode to episodic memory after enforce_vocabulary
"""

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL


class BrandVoiceAgent(BaseAgent):
    name = "BrandVoiceAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        from src.generation.brand_drift import BrandDriftAnalyzer
        from src.generation.voice_refiner import VoiceRefiner
        from src.generation.brand_guardian import BrandGuardian

        self._drift    = BrandDriftAnalyzer(model=model)
        self._refiner  = VoiceRefiner(model=model)
        self._guardian = BrandGuardian(model=model)

    def run(self, task: AgentTask) -> AgentResult:
        t = task.task_type

        if t == "detect_drift":
            return self._detect_drift(task.payload)
        if t == "enforce_vocabulary":
            return self._enforce_vocabulary(task.payload)
        if t == "refine_voice":
            return self._refine_voice(task.payload)

        return AgentResult(
            agent_name=self.name,
            success=False,
            error_message=f"Unknown task_type '{t}' for BrandVoiceAgent",
        )

    # ── Task handlers ─────────────────────────────────────────────────────────

    def _detect_drift(self, payload: dict) -> AgentResult:
        pasted_posts = payload.get("pasted_posts", [])
        cluster_id   = payload.get("cluster_id", 0)

        # Enrich context from semantic memory
        context_hint = ""
        if self._memory:
            records = self._memory.search_semantic(
                "brand voice tone vocabulary signature phrases", n=3
            )
            if records:
                context_hint = " | ".join(r["text"][:120] for r in records)

        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer("all-MiniLM-L6-v2")

        import json
        clusters_path = (
            __import__("pathlib").Path(__file__).resolve().parent.parent.parent
            / "data" / "clusters.json"
        )
        clusters_data = json.loads(clusters_path.read_text(encoding="utf-8"))

        result = self._drift.analyze(
            pasted_posts=pasted_posts,
            clusters_data=clusters_data,
            embedder=embedder,
        )
        return AgentResult(agent_name=self.name, output=result)

    def _enforce_vocabulary(self, payload: dict) -> AgentResult:
        caption    = payload.get("caption", "")
        cluster_id = payload.get("cluster_id", 0)
        issues     = payload.get("issues", [])

        critique = {
            "verdict": "needs_revision",
            "issues":  issues or ["Fix off-brand vocabulary and tone."],
            "severity": "major",
            "reasoning": "CriticAgent flagged off_brand_vocab error type.",
        }
        result = self._guardian.refine(caption, critique, cluster_id)

        refined = result.get("refined_caption", caption)
        if self._memory and refined != caption:
            self._write_episode(refined, cluster_id, "pending")
            result["memory_written"] = True

        return AgentResult(
            agent_name=self.name,
            output=result,
            memory_written=result.get("memory_written", False),
        )

    def _refine_voice(self, payload: dict) -> AgentResult:
        transcript = payload.get("transcript", "")
        cluster_id = payload.get("cluster_id", 0)
        result     = self._refiner.refine(transcript, cluster_id)
        return AgentResult(agent_name=self.name, output=result)
