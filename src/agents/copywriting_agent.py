"""
Copywriting Agent — wraps CaptionGenerator, ScriptGenerator, BlankPageSolver.

Responsibilities:
  - generate_caption:  Produce 3 on-brand caption variants enriched with episodic memory
  - rewrite_caption:   Rewrite a specific caption with a fix direction (from CriticAgent)
  - reformat_caption:  Reformat a caption to comply with platform-specific rules
  - generate_script:   Generate a Reel/Carousel/Static script
  - solve_blank_page:  Moment analysis + creative directions

Adds over the raw generators:
  - Platform context injection: reads procedural memory before generation
  - Episodic enrichment: reads past winning captions from memory store
"""

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL


class CopywritingAgent(BaseAgent):
    name = "CopywritingAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        from src.generation.caption_generator import CaptionGenerator
        from src.generation.script_generator import ScriptGenerator
        from src.generation.blank_page_solver import MomentAnalyzer, DirectionGenerator
        from src.generation.brand_guardian import BrandGuardian

        self._captions   = CaptionGenerator(model=model)
        self._scripts    = ScriptGenerator(model=model)
        self._moment     = MomentAnalyzer(model=model)
        self._directions = DirectionGenerator(model=model)
        self._guardian   = BrandGuardian(model=model)

    def run(self, task: AgentTask) -> AgentResult:
        t = task.task_type

        if t == "generate_caption":
            return self._generate_caption(task.payload)
        if t == "rewrite_caption":
            return self._rewrite_caption(task.payload)
        if t == "reformat_caption":
            return self._reformat_caption(task.payload)
        if t == "generate_script":
            return self._generate_script(task.payload)
        if t == "solve_blank_page":
            return self._solve_blank_page(task.payload)

        return AgentResult(
            agent_name=self.name,
            success=False,
            error_message=f"Unknown task_type '{t}' for CopywritingAgent",
        )

    # ── Task handlers ─────────────────────────────────────────────────────────

    def _build_performance_context(self, cluster_id: int, product: str) -> str | None:
        """Pull past winning/failing captions from episodic memory."""
        if not self._memory:
            return None
        records = self._memory.search_episodic(
            query=product or "caption performance", cluster_id=cluster_id, n_results=5
        )
        if not records:
            return None
        lines = []
        for r in records:
            outcome = r["metadata"].get("outcome", "unknown")
            text    = r["text"][:150]
            lines.append(f"[{outcome.upper()}] {text}")
        return "\n".join(lines)

    def _platform_note(self, platform: str) -> str:
        """Get a short platform-specific formatting note."""
        if not self._memory:
            return ""
        rules = self._memory.get_platform_rules(platform)
        return (
            f"Platform: {platform}. "
            f"Hook: {rules.get('hook_position', '')}. "
            f"Hashtags: {rules.get('hashtag_count', '')}. "
            f"Register: {rules.get('tone_register', '')}."
        )

    def _generate_caption(self, payload: dict) -> AgentResult:
        product            = payload.get("product", "")
        occasion           = payload.get("occasion", "")
        desired_feel       = payload.get("desired_feel", "")
        cluster_id         = payload.get("cluster_id", 0)
        previous_captions  = payload.get("previous_captions")
        platform           = payload.get("platform", "instagram")

        # Enrich desired_feel with platform context
        platform_note = self._platform_note(platform)
        if platform_note:
            desired_feel = f"{desired_feel} | {platform_note}" if desired_feel else platform_note

        perf_ctx = self._build_performance_context(cluster_id, product)
        captions = self._captions.generate(
            product=product,
            occasion=occasion,
            desired_feel=desired_feel,
            cluster_id=cluster_id,
            previous_captions=previous_captions,
            performance_context=perf_ctx,
        )
        return AgentResult(
            agent_name=self.name,
            output={"captions": captions, "used_memory": perf_ctx is not None},
        )

    def _rewrite_caption(self, payload: dict) -> AgentResult:
        caption       = payload.get("caption", "")
        fix_direction = payload.get("fix_direction", "Rewrite to sound more human and authentic.")
        cluster_id    = payload.get("cluster_id", 0)

        critique = {
            "verdict":   "needs_revision",
            "issues":    [fix_direction],
            "severity":  "major",
            "reasoning": "CriticAgent detected ai_slop or requested targeted rewrite.",
        }
        result = self._guardian.refine(caption, critique, cluster_id)
        return AgentResult(
            agent_name=self.name,
            output={
                "caption":      result.get("refined_caption", caption),
                "what_changed": result.get("what_changed", ""),
            },
        )

    def _reformat_caption(self, payload: dict) -> AgentResult:
        caption    = payload.get("caption", "")
        platform   = payload.get("platform", "instagram")
        cluster_id = payload.get("cluster_id", 0)

        rules   = self._memory.get_platform_rules(platform) if self._memory else {}
        fix_dir = (
            f"Reformat for {platform}. "
            f"Hook position: {rules.get('hook_position', 'first line')}. "
            f"Hashtags: {rules.get('hashtag_count', '5-10')}. "
            f"Register: {rules.get('tone_register', 'warm')}."
        )
        critique = {
            "verdict":  "needs_revision",
            "issues":   [fix_dir],
            "severity": "major",
            "reasoning": f"CriticAgent detected wrong_platform register for {platform}.",
        }
        result = self._guardian.refine(caption, critique, cluster_id)
        return AgentResult(
            agent_name=self.name,
            output={
                "caption":      result.get("refined_caption", caption),
                "what_changed": result.get("what_changed", ""),
            },
        )

    def _generate_script(self, payload: dict) -> AgentResult:
        result = self._scripts.generate(
            reference_caption=payload.get("reference_caption", ""),
            views=payload.get("views", 0),
            reach=payload.get("reach", 0),
            likes=payload.get("likes", 0),
            comments=payload.get("comments", 0),
            shares=payload.get("shares", 0),
            saves=payload.get("saves", 0),
            content_format=payload.get("format", "Reel"),
            cluster_id=payload.get("cluster_id", 0),
        )
        return AgentResult(agent_name=self.name, output=result)

    def _solve_blank_page(self, payload: dict) -> AgentResult:
        moment_text = payload.get("moment_text", "")
        analysis    = self._moment.analyze(moment_text)
        directions  = self._directions.generate(moment_text, analysis)
        return AgentResult(
            agent_name=self.name,
            output={"analysis": analysis, "directions": directions},
        )
