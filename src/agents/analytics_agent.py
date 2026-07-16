"""
Analytics & Strategy Agent — wraps WhyEngine, StrategicInsights, BoostAdvisor,
ConfidenceScorer, ResonanceSimulator.

Responsibilities:
  - why_engine:         Post-mortem analysis of a published post
  - pre_score:          Confidence score for a draft before publishing
  - resonance_check:    Audience persona simulation for caption variants
  - strategic_insights: Cluster richness vs. volume analysis
  - boost_advice:       Which cluster to put paid promotion behind

Adds over raw generators:
  - After why_engine: writes the outcome to episodic memory to close the feedback loop
    (so CopywritingAgent reads real performance data on the next generation run)
"""

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL


class AnalyticsAgent(BaseAgent):
    name = "AnalyticsAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        from src.generation.why_engine import WhyEngine
        from src.generation.confidence_scorer import ConfidenceScorer
        from src.generation.resonance_simulator import PersonaSimulator, ResonanceSynthesizer
        from src.generation.strategic_insights import StrategicInsights
        from src.generation.boost_advisor import BoostAdvisor

        self._why        = WhyEngine(model=model)
        self._scorer     = ConfidenceScorer(model=model)
        self._personas   = PersonaSimulator(model=model)
        self._resonance  = ResonanceSynthesizer(model=model)
        self._strategic  = StrategicInsights(model=model)
        self._boost      = BoostAdvisor(model=model)

    def run(self, task: AgentTask) -> AgentResult:
        t = task.task_type
        dispatch = {
            "why_engine":         self._why_engine,
            "pre_score":          self._pre_score,
            "resonance_check":    self._resonance_check,
            "strategic_insights": self._strategic_insights,
            "boost_advice":       self._boost_advice,
        }
        if t not in dispatch:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error_message=f"Unknown task_type '{t}' for AnalyticsAgent",
            )
        return dispatch[t](task.payload)

    def _why_engine(self, payload: dict) -> AgentResult:
        result = self._why.analyze(
            caption             = payload.get("caption", ""),
            post_type           = payload.get("post_type", "Static"),
            views               = payload.get("views", 0),
            reach               = payload.get("reach", 0),
            likes               = payload.get("likes", 0),
            comments            = payload.get("comments", 0),
            shares              = payload.get("shares", 0),
            saves               = payload.get("saves", 0),
            avg_watch_time_secs = payload.get("avg_watch_time_secs"),
            cluster_id          = payload.get("cluster_id", 0),
        )

        # Close the feedback loop — write outcome to episodic memory
        verdict = result.get("verdict_label", result.get("verdict", "")).lower()
        outcome = (
            "succeeded"     if "succeed" in verdict
            else "failed"   if "fail"    in verdict
            else "underperformed"
        )
        written = False
        if self._memory and payload.get("caption"):
            self._write_episode(payload["caption"], payload.get("cluster_id", 0), outcome)
            written = True

        return AgentResult(agent_name=self.name, output=result, memory_written=written)

    def _pre_score(self, payload: dict) -> AgentResult:
        caption    = payload.get("caption", "")
        cluster_id = payload.get("cluster_id", 0)
        result     = self._scorer.score(
            context_summary=f"Caption for cluster {cluster_id}",
            output_summary=caption,
        )
        return AgentResult(agent_name=self.name, output=result)

    def _resonance_check(self, payload: dict) -> AgentResult:
        captions   = payload.get("captions", [])
        cluster_id = payload.get("cluster_id", 0)

        import json
        from pathlib import Path
        clusters_path = (
            Path(__file__).resolve().parent.parent.parent / "data" / "clusters.json"
        )
        clusters_data = json.loads(clusters_path.read_text(encoding="utf-8"))

        reactions = self._personas.simulate(captions, clusters_data, cluster_id)
        synthesis = self._resonance.synthesize(captions, reactions)
        return AgentResult(
            agent_name=self.name,
            output={"persona_reactions": reactions, "synthesis": synthesis},
        )

    def _strategic_insights(self, payload: dict) -> AgentResult:
        import json
        from pathlib import Path
        clusters_path = (
            Path(__file__).resolve().parent.parent.parent / "data" / "clusters.json"
        )
        clusters_data = json.loads(clusters_path.read_text(encoding="utf-8"))
        result = self._strategic.analyze(clusters_data)
        return AgentResult(agent_name=self.name, output=result)

    def _boost_advice(self, payload: dict) -> AgentResult:
        import json
        from pathlib import Path
        clusters_path = (
            Path(__file__).resolve().parent.parent.parent / "data" / "clusters.json"
        )
        clusters_data = json.loads(clusters_path.read_text(encoding="utf-8"))
        result = self._boost.advise(clusters_data)
        return AgentResult(agent_name=self.name, output=result)
