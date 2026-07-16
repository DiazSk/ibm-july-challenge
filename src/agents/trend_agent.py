"""
Trend & Research Agent — Granite invocation #22.

The only fully new agent (all others wrap existing chains).

Flow:
  1. Run 3 DuckDuckGo queries about the creator's niche + current trends
  2. Feed snippets to Granite TrendSynthesizer (new prompt, new Granite call)
  3. Return micro-trends, content hooks, suggested angles, briefing summary

Also checks episodic memory to avoid repeating angles already used this week.
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

OLLAMA_MODEL = "granite3.1-dense:8b"

_TREND_TEMPLATE = """\
You are a content strategist for {brand_name}, a homemade artisanal bakery on Instagram \
({niche} niche). Your job is to identify actionable content opportunities from recent web \
trends.

Recent web search results:
{snippets_block}

Previously used angles to AVOID repeating:
{used_angles_block}

Brand voice clusters available:
  0 - Homemade Classics (warm, nostalgic)
  1 - Fusion Specials (bold, experimental)
  2 - Behind the Scenes (intimate, process-focused)
  3 - Nutella Series (indulgent, passionate)
  4 - Bomboloni (celebratory, artisanal pride)

Based on the search results, identify high-velocity trends relevant to this bakery.
For each suggested angle, recommend the most fitting cluster.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "micro_trends": [
    {{"trend": "<trend name>", "relevance": "<why this matters for the bakery>", "urgency": "high"}}
  ],
  "content_hooks": ["<hook 1>", "<hook 2>", "<hook 3>"],
  "suggested_angles": [
    {{
      "angle": "<content angle>",
      "cluster": "<cluster name>",
      "format": "Reel" or "Carousel" or "Static",
      "why_now": "<why this is timely>"
    }}
  ],
  "briefing_summary": "<2-3 sentence summary of the opportunity landscape this week>"
}}
"""

_TREND_PROMPT = PromptTemplate(
    input_variables=["brand_name", "niche", "snippets_block", "used_angles_block"],
    template=_TREND_TEMPLATE,
)


def _web_search(topic: str, niche: str = "bakery", max_results: int = 5) -> list[str]:
    """DuckDuckGo search — reuses the pattern from jarvis_agent.py. Never raises."""
    try:
        from duckduckgo_search import DDGS
        queries = [
            f"{niche} instagram content trends {topic}",
            f"trending {niche} food social media {topic}",
            f"viral {niche} content ideas {topic}",
        ]
        results: list[str] = []
        seen: set[str]     = set()
        with DDGS() as ddgs:
            for query in queries:
                try:
                    hits = ddgs.text(query, max_results=max_results, timelimit="m")
                    for h in (hits or []):
                        url = h.get("href", "")
                        if url not in seen:
                            seen.add(url)
                            title = h.get("title", "")
                            body  = h.get("body", "")[:250]
                            results.append(f"{title}: {body}")
                except Exception:
                    pass
        return results[: max_results * 2]
    except Exception:
        return []


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _parse_json(raw: str) -> dict:
    text  = raw.strip()
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


class TrendAgent(BaseAgent):
    """
    Researches and synthesizes content opportunities from live web trends.
    New Granite invocation #22 — TrendSynthesizer.
    """

    name = "TrendAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        self._llm   = OllamaLLM(model=model, temperature=0.6, num_predict=800)
        self._chain = _TREND_PROMPT | self._llm

        profile_path = _PROJECT_ROOT / "data" / "brand_profile.json"
        if profile_path.exists():
            profile          = json.loads(profile_path.read_text(encoding="utf-8"))
            self._brand_name = profile.get("brand_name", "the brand")
        else:
            self._brand_name = "the brand"

    def run(self, task: AgentTask) -> AgentResult:
        if task.task_type != "trend_briefing":
            return AgentResult(
                agent_name=self.name,
                success=False,
                error_message=f"TrendAgent only handles 'trend_briefing', got '{task.task_type}'",
            )
        return self._trend_briefing(task.payload)

    def _trend_briefing(self, payload: dict) -> AgentResult:
        niche  = payload.get("niche", "bakery homemade desserts")
        topic  = payload.get("topic", "")

        # Step 1 — Web search
        snippets = _web_search(topic or "content ideas", niche=niche)
        if not snippets:
            snippets = [
                "Food content trends: behind-the-scenes process videos perform well.",
                "Nostalgia-themed content drives high saves on Instagram.",
                "Short-form recipe reels with text overlay see 2x engagement.",
            ]

        snippets_block = "\n".join(f"- {s}" for s in snippets[:12])

        # Step 2 — Pull recently used angles from episodic memory to avoid repetition
        used_angles_block = "None recorded yet."
        if self._memory:
            past = self._memory.search_episodic("content angle trend", n=5)
            if past:
                used_angles_block = "\n".join(
                    f"- {r['text'][:120]}" for r in past
                )

        # Step 3 — Granite TrendSynthesizer (#22)
        try:
            raw    = self._chain.invoke({
                "brand_name":        self._brand_name,
                "niche":             niche,
                "snippets_block":    snippets_block,
                "used_angles_block": used_angles_block,
            })
            result = _parse_json(raw)

            # Validate expected keys
            result.setdefault("micro_trends",      [])
            result.setdefault("content_hooks",     [])
            result.setdefault("suggested_angles",  [])
            result.setdefault("briefing_summary",  "Trend briefing generated.")

        except Exception as exc:
            result = {
                "micro_trends":      [],
                "content_hooks":     [],
                "suggested_angles":  [],
                "briefing_summary":  f"Trend synthesis failed: {exc}",
                "raw_snippets":      snippets[:5],
            }

        result["sources_searched"] = len(snippets)
        return AgentResult(agent_name=self.name, output=result)
