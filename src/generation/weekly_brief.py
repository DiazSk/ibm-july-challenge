"""
Weekly Brief Planner — Granite invocation #17.

Proposes a handful of realistic content "scenarios" — the kind of free-text
moment a founder would type into Blank Page Solver — biased toward a specific
underutilized-but-rich content cluster and grounded in real web trend research.

This class only proposes the scenarios. Per this project's composition
philosophy (see blank_page_solver.py), it does NOT touch the downstream
generators — each proposed scenario_text is fed completely unmodified into
the existing MomentAnalyzer -> DirectionGenerator -> CaptionGenerator ->
ImagePromptGenerator chain by the router/background job, exactly as if a
human had typed it into Blank Page Solver themselves.

Input:  cluster_label, cluster_context, trend_snippets, brand_name, n
Output: list[{scenario_text, rationale}]

Run standalone:
    python src/generation/weekly_brief.py
"""

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "granite3.1-dense:8b"

_TEMPLATE = """\
You are a content planner for {brand_name}, a homemade artisanal bakery on Instagram.

This week, the goal is to create more content for an underutilized-but-rich \
content pillar:

Pillar: {cluster_label}
{cluster_context}

Here are some real, current trend snippets that might be relevant inspiration:
{trend_snippets_block}

Propose {n} realistic, specific content scenarios for this pillar — the kind \
of real moment a founder would describe if asked "what's happening in your \
kitchen this week?" Each scenario should be a natural, first-person-style \
description (2-3 sentences), not a caption or a marketing pitch. Draw on the \
trend snippets where genuinely relevant, but keep every scenario grounded in \
this specific bakery and pillar.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "scenarios": [
    {{"scenario_text": "<2-3 sentence realistic moment>", "rationale": "<1 sentence: why this fits the pillar and this week>"}}
  ]
}}
"""

_PROMPT = PromptTemplate(
    input_variables=["brand_name", "cluster_label", "cluster_context", "trend_snippets_block", "n"],
    template=_TEMPLATE,
)


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return json.loads(_repair_missing_commas(text))


class WeeklyBriefPlanner:
    """
    Proposes n content scenarios for an underutilized cluster, grounded in
    real trend snippets. Never raises — falls back to a single generic
    scenario if Granite's output can't be parsed.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.7, num_predict=800)
        self._chain = _PROMPT | self._llm

    def generate(
        self,
        cluster_label: str,
        cluster_context: str,
        trend_snippets: list[str],
        brand_name: str,
        n: int = 2,
    ) -> list[dict]:
        """
        Granite Call #17.
        Returns n x {scenario_text, rationale}.
        """
        trend_snippets_block = (
            "\n".join(f"- {s}" for s in trend_snippets[:5])
            if trend_snippets
            else "(no external trend data available this week)"
        )

        raw = self._chain.invoke({
            "brand_name": brand_name,
            "cluster_label": cluster_label,
            "cluster_context": cluster_context,
            "trend_snippets_block": trend_snippets_block,
            "n": n,
        })

        try:
            result = _parse_json(raw)
            scenarios = result.get("scenarios") or []
            cleaned = [
                {"scenario_text": s.get("scenario_text", "").strip(), "rationale": s.get("rationale", "").strip()}
                for s in scenarios
                if s.get("scenario_text", "").strip()
            ]
            if cleaned:
                return cleaned[:n]
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
            pass

        return [{
            "scenario_text": f"A behind-the-scenes look at how we make {cluster_label} this week.",
            "rationale": "Fallback scenario — could not parse a specific plan.",
        }]


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    planner = WeeklyBriefPlanner()
    scenarios = planner.generate(
        cluster_label="Fusion Specials",
        cluster_context="Tone: playful, indulgent. This is your richest-voiced pillar but posted least often.",
        trend_snippets=["Rasmalai-inspired desserts trending this season", "Fusion desserts blending Indian and Western flavors are popular right now"],
        brand_name="HotCakes Bakes",
        n=2,
    )
    print(json.dumps(scenarios, indent=2))
