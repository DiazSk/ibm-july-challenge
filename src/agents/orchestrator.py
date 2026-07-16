"""
StyleSync Orchestrator — adaptive topology multi-agent coordinator.

Implements the AdaptOrch pattern (Feb 2026, medium confidence): task type determines
coordination topology at runtime rather than using one fixed pattern.

Topology map:
  single_caption   → parallel:     BrandVoice + Copywriting run concurrently
  full_campaign    → hierarchical: Copy → Critic loop (max 2 cycles) → Visual + Analytics
  post_mortem      → sequential:   Analytics → Community (if triage payload present)
  trend_briefing   → parallel:     Trend + Analytics run concurrently
  community_triage → flat:         Community alone

Critic routing loop (inside full_campaign):
  approved         → stop
  ai_slop          → CopywritingAgent.rewrite_caption
  off_brand_vocab  → BrandVoiceAgent.enforce_vocabulary
  wrong_platform   → CopywritingAgent.reformat_caption
  factual_gap      → return with human_review_flag=True (no auto-route)
  max 2 cycles to mirror existing BrandGuardian cap
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from src.agents.base import AgentTask, AgentResult, OLLAMA_MODEL
from src.agents.brand_voice_agent import BrandVoiceAgent
from src.agents.copywriting_agent import CopywritingAgent
from src.agents.critic_agent import CriticAgent
from src.agents.analytics_agent import AnalyticsAgent
from src.agents.community_agent import CommunityAgent
from src.agents.visual_agent import VisualAgent
from src.agents.trend_agent import TrendAgent


@dataclass
class OrchestratorResult:
    task_type:          str
    topology:           str
    results:            dict            = field(default_factory=dict)
    agents_used:        list[str]       = field(default_factory=list)
    cycles:             int             = 0
    memory_written:     bool            = False
    human_review_flag:  bool            = False
    convergence_reason: str             = "max_cycles"  # goal_met | plateau | factual_gap | max_cycles
    success:            bool            = True
    error_message:      str | None      = None


TOPOLOGY_MAP: dict[str, str] = {
    "single_caption":   "parallel",
    "full_campaign":    "hierarchical",
    "post_mortem":      "sequential",
    "trend_briefing":   "parallel",
    "community_triage": "flat",
}

_MAX_SAFE_CYCLES = 8   # safety ceiling; convergence usually exits earlier
_PLATEAU_WINDOW  = 3   # consecutive cycles with Δscore ≤ 2 = stuck


class StyleSyncOrchestrator:
    """
    Coordinates all StyleSync agents using adaptive topology selection.
    Thread-safe — each run() call is independent.
    """

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        self._memory      = memory
        self._brand_voice = BrandVoiceAgent(memory=memory, model=model)
        self._copywriting = CopywritingAgent(memory=memory, model=model)
        self._critic      = CriticAgent(memory=memory, model=model)
        self._analytics   = AnalyticsAgent(memory=memory, model=model)
        self._community   = CommunityAgent(memory=memory, model=model)
        self._visual      = VisualAgent(memory=memory, model=model)
        self._trend       = TrendAgent(memory=memory, model=model)

    # ── Helper methods ────────────────────────────────────────────────────────

    def _quick_score(self, draft: str, cluster_id: int) -> int:
        """Inline confidence score; returns 50 on failure so the loop can still exit safely."""
        r = self._analytics.safe_run(
            AgentTask("pre_score", {"caption": draft, "cluster_id": cluster_id})
        )
        return r.output.get("score", 50) if r.success else 50

    def _rewrite_new_angle(self, draft: str, cluster_id: int, agents_used: list) -> str:
        """Called when critic approves but confidence is below threshold — tries a fresh hook."""
        fix = self._copywriting.safe_run(AgentTask("rewrite_caption", {
            "caption":       draft,
            "fix_direction": (
                "Open with a vivid sensory detail specific to this product — something a real "
                "person who baked it today would notice. Avoid generic invitation phrases like "
                "'Indulge in' or 'Experience the'. Sound authentic, not polished."
            ),
            "cluster_id": cluster_id,
        }))
        agents_used.append("CopywritingAgent")
        return fix.output.get("caption", draft)

    def run(self, task_type: str, payload: dict) -> OrchestratorResult:
        topology = TOPOLOGY_MAP.get(task_type, "flat")
        handler  = {
            "single_caption":   self._run_single_caption,
            "full_campaign":    self._run_full_campaign,
            "post_mortem":      self._run_post_mortem,
            "trend_briefing":   self._run_trend_briefing,
            "community_triage": self._run_community_triage,
        }
        fn = handler.get(task_type)
        if fn is None:
            return OrchestratorResult(
                task_type=task_type,
                topology=topology,
                success=False,
                error_message=f"Unknown task_type '{task_type}'",
            )
        try:
            return fn(payload, topology)
        except Exception as exc:
            return OrchestratorResult(
                task_type=task_type,
                topology=topology,
                success=False,
                error_message=str(exc),
            )

    # ── Topology implementations ──────────────────────────────────────────────

    def _run_single_caption(self, payload: dict, topology: str) -> OrchestratorResult:
        """
        Parallel: BrandVoice drift check + Copywriting generation run concurrently,
        then results are merged.
        """
        agents_used: list[str] = []
        bv_result: AgentResult | None  = None
        copy_result: AgentResult | None = None
        errors: list[str] = []

        def run_brand_voice():
            nonlocal bv_result
            pasted = [payload.get("product", "")]
            bv_result = self._brand_voice.safe_run(
                AgentTask("detect_drift", {"pasted_posts": pasted, "cluster_id": payload.get("cluster_id", 0)})
            )

        def run_copywriting():
            nonlocal copy_result
            copy_result = self._copywriting.safe_run(
                AgentTask("generate_caption", payload)
            )

        t1 = threading.Thread(target=run_brand_voice)
        t2 = threading.Thread(target=run_copywriting)
        t1.start(); t2.start()
        t1.join();  t2.join()

        if bv_result and bv_result.success:
            agents_used.append("BrandVoiceAgent")
        if copy_result and copy_result.success:
            agents_used.append("CopywritingAgent")

        return OrchestratorResult(
            task_type="single_caption",
            topology=topology,
            agents_used=agents_used,
            results={
                "captions":       copy_result.output if copy_result else {},
                "drift_check":    bv_result.output   if bv_result   else {},
            },
        )

    def _run_full_campaign(self, payload: dict, topology: str) -> OrchestratorResult:
        """
        Hierarchical: Copy → convergence loop (Critic + typed routing) → Visual + Analytics.

        Exits when:
          goal_met   — critic approves AND confidence ≥ threshold
          plateau    — score stalls (Δ ≤ 2 over PLATEAU_WINDOW cycles)
          factual_gap — human review required
          max_cycles — _MAX_SAFE_CYCLES reached without convergence
        """
        agents_used: list[str] = []
        cluster_id           = payload.get("cluster_id", 0)
        platform             = payload.get("platform", "instagram")
        confidence_threshold = int(payload.get("confidence_threshold", 75))

        # Inject trend hooks into desired_feel if the frontend passed them
        trend_context = payload.get("trend_context", [])
        enriched = dict(payload)
        if trend_context:
            hooks = " | ".join(str(h) for h in trend_context[:2])
            base  = enriched.get("desired_feel", "")
            enriched["desired_feel"] = f"{base}. Trending now: {hooks}".strip(". ")

        # Step 1 — Initial draft
        copy_result = self._copywriting.safe_run(AgentTask("generate_caption", enriched))
        agents_used.append("CopywritingAgent")
        captions = copy_result.output.get("captions", [{}])
        draft    = captions[0].get("caption", "") if captions else ""

        cycles:             int        = 0
        human_review_flag:  bool       = False
        critic_history:     list[dict] = []
        confidence_scores:  list[int]  = []
        convergence_reason: str        = "max_cycles"

        # Step 2 — Convergence loop
        while cycles < _MAX_SAFE_CYCLES and draft:
            critic_result = self._critic.safe_run(
                AgentTask("critique", {"caption": draft, "cluster_id": cluster_id})
            )
            agents_used.append("CriticAgent")
            error_type = critic_result.error_type or "approved"
            critic_history.append({
                "cycle":      cycles + 1,
                "error_type": error_type,
                "flagged":    critic_result.output.get("flagged_phrase", ""),
                "fix":        critic_result.output.get("fix_direction", ""),
            })

            if error_type == "approved":
                score = self._quick_score(draft, cluster_id)
                confidence_scores.append(score)
                if score >= confidence_threshold:
                    convergence_reason = "goal_met"
                    break
                # Approved but below quality gate — try a different angle
                draft = self._rewrite_new_angle(draft, cluster_id, agents_used)

            elif error_type == "factual_gap":
                convergence_reason = "factual_gap"
                human_review_flag  = True
                break

            elif error_type == "ai_slop":
                fix = self._copywriting.safe_run(AgentTask("rewrite_caption", {
                    "caption":       draft,
                    "fix_direction": critic_result.output.get("fix_direction", ""),
                    "cluster_id":    cluster_id,
                }))
                agents_used.append("CopywritingAgent")
                draft = fix.output.get("caption", draft)
                confidence_scores.append(self._quick_score(draft, cluster_id))

            elif error_type == "off_brand_vocab":
                fix = self._brand_voice.safe_run(AgentTask("enforce_vocabulary", {
                    "caption":    draft,
                    "cluster_id": cluster_id,
                    "issues":     critic_result.output.get("guardian_critique", {}).get("issues", []),
                }))
                agents_used.append("BrandVoiceAgent")
                draft = fix.output.get("refined_caption", draft)
                confidence_scores.append(self._quick_score(draft, cluster_id))

            elif error_type == "wrong_platform":
                fix = self._copywriting.safe_run(AgentTask("reformat_caption", {
                    "caption":    draft,
                    "platform":   platform,
                    "cluster_id": cluster_id,
                }))
                agents_used.append("CopywritingAgent")
                draft = fix.output.get("caption", draft)
                confidence_scores.append(self._quick_score(draft, cluster_id))

            # Plateau detection — Δscore ≤ 2 for PLATEAU_WINDOW consecutive cycles
            if len(confidence_scores) >= _PLATEAU_WINDOW:
                recent = confidence_scores[-_PLATEAU_WINDOW:]
                if max(recent) - min(recent) <= 2:
                    convergence_reason = "plateau"
                    human_review_flag  = True
                    break

            cycles += 1

        # Step 3 — Final score + Visual in parallel
        final_score_result: AgentResult | None = None
        visual_result:      AgentResult | None = None

        def run_score():
            nonlocal final_score_result
            final_score_result = self._analytics.safe_run(
                AgentTask("pre_score", {"caption": draft, "cluster_id": cluster_id})
            )

        def run_visual():
            nonlocal visual_result
            visual_result = self._visual.safe_run(
                AgentTask("generate_image_prompt", {"caption": draft, "cluster_id": cluster_id})
            )

        t1 = threading.Thread(target=run_score)
        t2 = threading.Thread(target=run_visual)
        t1.start(); t2.start()
        t1.join();  t2.join()

        if final_score_result and final_score_result.success:
            agents_used.append("AnalyticsAgent")
        if visual_result and visual_result.success:
            agents_used.append("VisualAgent")

        memory_written = False
        if self._memory and draft:
            self._memory.upsert_episode(draft, cluster_id, "pending")
            memory_written = True

        return OrchestratorResult(
            task_type="full_campaign",
            topology=topology,
            agents_used=agents_used,
            cycles=cycles,
            memory_written=memory_written,
            human_review_flag=human_review_flag,
            convergence_reason=convergence_reason,
            results={
                "draft":                 draft,
                "all_captions":          captions,
                "critic_history":        critic_history,
                "confidence":            final_score_result.output  if final_score_result else {},
                "image_prompt":          visual_result.output       if visual_result       else {},
                "confidence_trajectory": confidence_scores,
                "convergence_reason":    convergence_reason,
            },
        )

    def _run_post_mortem(self, payload: dict, topology: str) -> OrchestratorResult:
        """Sequential: Analytics why-engine → Community triage (if messages present)."""
        agents_used: list[str] = []

        analytics_result = self._analytics.safe_run(AgentTask("why_engine", payload))
        agents_used.append("AnalyticsAgent")

        community_result: AgentResult | None = None
        if payload.get("messages"):
            community_result = self._community.safe_run(
                AgentTask("triage_comments", {
                    "messages":   payload["messages"],
                    "cluster_id": payload.get("cluster_id", 0),
                })
            )
            agents_used.append("CommunityAgent")

        return OrchestratorResult(
            task_type="post_mortem",
            topology=topology,
            agents_used=agents_used,
            memory_written=analytics_result.memory_written,
            results={
                "diagnosis":  analytics_result.output,
                "triage":     community_result.output if community_result else None,
            },
        )

    def _run_trend_briefing(self, payload: dict, topology: str) -> OrchestratorResult:
        """Parallel: Trend + Analytics (strategic insights) run concurrently."""
        agents_used: list[str] = []
        trend_result:     AgentResult | None = None
        analytics_result: AgentResult | None = None

        def run_trend():
            nonlocal trend_result
            trend_result = self._trend.safe_run(AgentTask("trend_briefing", payload))

        def run_analytics():
            nonlocal analytics_result
            analytics_result = self._analytics.safe_run(
                AgentTask("strategic_insights", payload)
            )

        t1 = threading.Thread(target=run_trend)
        t2 = threading.Thread(target=run_analytics)
        t1.start(); t2.start()
        t1.join();  t2.join()

        if trend_result and trend_result.success:
            agents_used.append("TrendAgent")
        if analytics_result and analytics_result.success:
            agents_used.append("AnalyticsAgent")

        return OrchestratorResult(
            task_type="trend_briefing",
            topology=topology,
            agents_used=agents_used,
            results={
                "trend_briefing":    trend_result.output     if trend_result     else {},
                "strategic_context": analytics_result.output if analytics_result else {},
            },
        )

    def _run_community_triage(self, payload: dict, topology: str) -> OrchestratorResult:
        """Flat: Community agent alone."""
        result = self._community.safe_run(AgentTask("triage_comments", payload))
        return OrchestratorResult(
            task_type="community_triage",
            topology=topology,
            agents_used=["CommunityAgent"] if result.success else [],
            results=result.output,
        )
