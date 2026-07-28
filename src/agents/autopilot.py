"""
Weekly Autopilot — the autonomous content agent (guided autonomy: plan-then-act).

Unlike the old orchestrator (a fixed topology chosen by a lookup table), this
agent decides WHAT to post on its own:

  THINK  — gathers evidence with its tools (brand gaps, live trends, past
           performance), then Granite REASONS over that evidence to produce its
           own weekly plan (which pillars, which angles, and why). If it hits a
           genuine strategic fork it can't resolve from the evidence, it asks the
           user ONE question and waits.
  ACT    — autonomously produces each planned post via the orchestrator's
           produce_post pipeline (draft → critic → refine → score-gate → image).
  REVIEW — returns the batch with per-post rationale + confidence.

It streams every step through a `trace` callback and pauses for input through an
`ask_user` callback, so a caller (api/routers/agent_run.py) can show the agent
thinking live and resume it after a human answers.

Run standalone (self-check — needs Ollama + data files, ~1-2 min):
    python src/agents/autopilot.py
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from src.agents.base import OLLAMA_MODEL

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

_PILLARS = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}

_PLANNER_TEMPLATE = """\
You are the autonomous content strategist for {brand_name}, a homemade artisanal \
bakery on Instagram. Plan this week's Instagram posts — decide WHAT to post and WHY.

Content pillars (cluster_id — name):
  0 — Homemade Classics (warm, nostalgic)
  1 — Fusion Specials (bold, experimental)
  2 — Behind the Scenes (intimate, process-focused)
  3 — Nutella Series (indulgent, passionate)
  4 — Bomboloni (celebratory, artisanal pride)

Evidence you gathered with your tools:

BRAND GAPS (pillar balance — what's over/under-used):
{gaps_block}

LIVE TRENDS (this week):
{trends_block}

PAST PERFORMANCE (real outcomes of recent posts):
{perf_block}
{steer_block}{answer_block}
Decide the {target_count} best posts to make this week. For each, pick the most \
strategic pillar (by cluster_id) and a specific angle, and justify it by naming the \
exact gap, trend, or past outcome you are responding to.

Ask the user a question ONLY IF you face a genuine strategic fork you cannot resolve \
from the evidence above (e.g. two under-used pillars equally worth reviving, or a \
trend you are unsure fits the brand). If so, set "needs_user_input" true and ask ONE \
specific question with 2-3 concrete options. Otherwise set it false. Never ask about \
trivia or things the evidence already answers.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "reasoning": "<2-3 sentences on your overall strategy this week>",
  "needs_user_input": true or false,
  "question": "<your question if unsure, else empty string>",
  "options": ["<option 1>", "<option 2>"],
  "posts": [
    {{"cluster_id": 0, "pillar": "Homemade Classics", "angle": "<specific angle>", "rationale": "<the gap/trend/outcome this responds to>"}}
  ]
}}
"""

_PLANNER_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "gaps_block", "trends_block", "perf_block",
        "steer_block", "answer_block", "target_count",
    ],
    template=_PLANNER_TEMPLATE,
)


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_repair_missing_commas(text))


class WeeklyAutopilot:
    """Autonomous weekly content planner. Composes a StyleSyncOrchestrator as its toolbelt."""

    def __init__(self, orchestrator, model: str = OLLAMA_MODEL):
        self._orch = orchestrator
        self._llm = OllamaLLM(model=model, temperature=0.4, num_predict=800)
        self._chain = _PLANNER_PROMPT | self._llm
        try:
            self._brand_name = json.loads(_PROFILE_PATH.read_text(encoding="utf-8")).get(
                "brand_name", "the brand"
            )
        except Exception:
            self._brand_name = "the brand"

    # ── Evidence formatting ─────────────────────────────────────────────────────

    @staticmethod
    def _fmt_gaps(gaps: dict) -> str:
        if not gaps:
            return "No gap analysis available."
        parts = []
        under = gaps.get("underutilized_cluster")
        over = gaps.get("overused_cluster")
        if under is not None:
            parts.append(f"Under-used pillar: cluster {under} ({_PILLARS.get(under, '?')}).")
        if over is not None:
            parts.append(f"Over-used pillar: cluster {over} ({_PILLARS.get(over, '?')}).")
        if gaps.get("strategic_brief"):
            parts.append(str(gaps["strategic_brief"])[:300])
        for t in (gaps.get("tensions") or [])[:2]:
            parts.append(f"Tension: {t}")
        return "\n".join(f"- {p}" for p in parts) or "No notable gaps."

    @staticmethod
    def _fmt_trends(trends: dict) -> str:
        if not trends:
            return "No trend data available."
        parts = []
        if trends.get("briefing_summary"):
            parts.append(str(trends["briefing_summary"])[:300])
        for h in (trends.get("content_hooks") or [])[:3]:
            parts.append(f"Hook: {h}")
        for a in (trends.get("suggested_angles") or [])[:3]:
            if isinstance(a, dict):
                parts.append(f"Angle: {a.get('angle', '')} ({a.get('cluster', '')})")
        return "\n".join(f"- {p}" for p in parts) or "No strong trends this week."

    @staticmethod
    def _fmt_perf(perf: list[str]) -> str:
        if not perf:
            return "No past-performance data recorded yet."
        return "\n".join(f"- {p}" for p in perf[:5])

    # ── Phases ──────────────────────────────────────────────────────────────────

    def think(
        self,
        steer: str,
        target_count: int,
        trace: Callable[[dict], None],
        ask_user: Callable[[str, list[str]], str] | None,
    ) -> dict:
        trace({"phase": "think", "label": "Assessing brand gaps", "detail": ""})
        gaps = self._orch.assess_gaps()
        trace({"phase": "think", "label": "Checking live trends", "detail": ""})
        trends = self._orch.get_trends()
        trace({"phase": "think", "label": "Recalling past performance", "detail": ""})
        perf = self._orch.recall_performance()

        steer_block = f"\nThe creator asked you to focus on: {steer}\n" if steer.strip() else ""

        def plan_once(answer_block: str) -> dict:
            raw = self._chain.invoke({
                "brand_name": self._brand_name,
                "gaps_block": self._fmt_gaps(gaps),
                "trends_block": self._fmt_trends(trends),
                "perf_block": self._fmt_perf(perf),
                "steer_block": steer_block,
                "answer_block": answer_block,
                "target_count": target_count,
            })
            try:
                return _parse_json(raw)
            except (json.JSONDecodeError, ValueError):
                return {"reasoning": "", "needs_user_input": False, "posts": []}

        trace({"phase": "think", "label": "Planning the week", "detail": ""})
        plan = plan_once("")

        # Human-in-the-loop: only if the agent is genuinely unsure AND we can ask.
        if plan.get("needs_user_input") and plan.get("question") and ask_user:
            answer = ask_user(plan["question"], plan.get("options") or [])
            trace({"phase": "think", "label": "Got your answer", "detail": answer})
            plan = plan_once(
                f"\nYou asked: \"{plan['question']}\" — the creator answered: "
                f"\"{answer}\". Use this to finalize the plan; do not ask again.\n"
            )
            plan["needs_user_input"] = False

        posts = [p for p in (plan.get("posts") or []) if isinstance(p, dict)][:target_count]
        plan["posts"] = posts
        trace({
            "phase": "think",
            "label": f"Planned {len(posts)} post{'s' if len(posts) != 1 else ''}",
            "detail": plan.get("reasoning", ""),
        })
        return plan

    def act(
        self,
        plan: dict,
        steer: str,
        platform: str,
        confidence_threshold: int,
        trace: Callable[[dict], None],
    ) -> list[dict]:
        produced: list[dict] = []
        for i, post in enumerate(plan.get("posts", []), 1):
            cluster_id = int(post.get("cluster_id", 0))
            angle = post.get("angle", "")
            pillar = post.get("pillar", _PILLARS.get(cluster_id, ""))
            trace({"phase": "act", "post": i, "label": f"Producing post {i}: {pillar}", "detail": angle})

            result = self._orch.produce_post(
                {
                    "product": angle or steer or "this week's bake",
                    "occasion": steer or "This week's post",
                    "desired_feel": "on-brand and engaging",
                    "cluster_id": cluster_id,
                    "platform": platform,
                    "confidence_threshold": confidence_threshold,
                },
                trace=lambda e, _i=i: trace({**e, "phase": "act", "post": _i}),
            )
            confidence = result.get("confidence", {}) or {}
            produced.append({
                "index": i,
                "cluster_id": cluster_id,
                "pillar": pillar,
                "angle": angle,
                "rationale": post.get("rationale", ""),
                "caption": result.get("draft", ""),
                "confidence": confidence.get("score"),
                "convergence_reason": result.get("convergence_reason", ""),
                "image_prompt": (result.get("image_prompt", {}) or {}).get("prompt", ""),
                "needs_review": result.get("human_review_flag", False),
            })
            trace({
                "phase": "act", "post": i,
                "label": f"Post {i} ready",
                "detail": f"{confidence.get('score', '?')}/100 · {result.get('convergence_reason', '')}",
            })
        return produced

    def run(
        self,
        steer: str = "",
        target_count: int = 3,
        platform: str = "instagram",
        confidence_threshold: int = 75,
        trace: Callable[[dict], None] | None = None,
        ask_user: Callable[[str, list[str]], str] | None = None,
    ) -> dict:
        emit = trace or (lambda _e: None)
        target_count = max(1, min(5, int(target_count)))

        emit({"phase": "start", "label": "Autopilot starting", "detail": f"{target_count} posts"})
        plan = self.think(steer, target_count, emit, ask_user)
        posts = self.act(plan, steer, platform, confidence_threshold, emit)

        summary = (
            f"Planned and produced {len(posts)} post"
            f"{'s' if len(posts) != 1 else ''} across "
            f"{len({p['cluster_id'] for p in posts})} pillar(s)."
        )
        emit({"phase": "done", "label": "Done", "detail": summary})
        return {
            "reasoning": plan.get("reasoning", ""),
            "posts": posts,
            "summary": summary,
        }


# ── Standalone self-check ───────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(_PROJECT_ROOT))
    from src.agents.orchestrator import StyleSyncOrchestrator
    from src.memory.store import AgentMemoryStore

    orch = StyleSyncOrchestrator(memory=AgentMemoryStore())
    pilot = WeeklyAutopilot(orch)

    def _trace(e):
        print(f"  [{e.get('phase','')}] {e.get('label','')} — {str(e.get('detail',''))[:80]}")

    print("-- THINK only (planner validity) --")
    plan = pilot.think(steer="", target_count=3, trace=_trace, ask_user=None)
    assert isinstance(plan.get("posts"), list) and len(plan["posts"]) >= 1, "planner produced no posts"
    for p in plan["posts"]:
        assert "cluster_id" in p and "angle" in p, f"post missing keys: {p}"
    print(f"\nOK — planner produced {len(plan['posts'])} valid post(s).")
