"""
Self-Improving Playbook Agent.

The one agent that changes its OWN behaviour. It reads this creator's real post
outcomes from episodic memory (wins vs misses, with their hook patterns and
signal metrics), reasons about what actually distinguishes the two for THIS
brand, and rewrites the procedural-memory playbook — the rules CopywritingAgent
reads (via build_copywriting_context) on every future generation. So next
week's captions are shaped by what genuinely worked last week: a closed
self-improvement loop, not a fixed prompt.

Run standalone (self-check — needs Ollama + a populated ChromaDB):
    python -m src.agents.playbook_agent
"""

from __future__ import annotations

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from src.agents.base import OLLAMA_MODEL

_TEMPLATE = """\
You are the self-improvement engine for {brand_name}, learning ONLY from this \
creator's own past post outcomes — not generic social-media advice.

POSTS THAT WORKED:
{winners_block}

POSTS THAT UNDERPERFORMED:
{losers_block}

Compare the two sets. Identify the specific, repeatable patterns that separate \
this brand's wins from its misses — reference the hook patterns and signals you \
actually see above (e.g. "sensory openers", "number-led hooks", "posts ending in \
a question"). Then write 3-5 PROCEDURAL RULES the copywriter should follow next \
time. Each rule must be concrete and specific to this brand's evidence, not \
generic ("post consistently" is useless).

Return ONLY valid JSON — no preamble, no markdown fences:
{{
  "learned": "<2-3 sentences: the key insight from this creator's own results>",
  "rules": [
    {{"rule_name": "<3-5 word slug>", "instruction": "<one concrete, brand-specific rule>"}}
  ]
}}
"""

_PROMPT = PromptTemplate(
    input_variables=["brand_name", "winners_block", "losers_block"],
    template=_TEMPLATE,
)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _episode_line(ep: dict) -> str:
    hook = ep.get("hook_pattern") or "?"
    save = ep.get("save_rate")
    sig = ep.get("primary_signal") or ""
    metrics = f"hook={hook}" + (f", save_rate={save}" if save is not None else "") + (f", {sig}" if sig else "")
    text = (ep.get("caption") or ep.get("text") or "")[:120]
    return f"- ({metrics}) {text}"


class PlaybookAgent:
    """Reflects over episodic outcomes and rewrites procedural-memory rules."""

    def __init__(self, memory, model: str = OLLAMA_MODEL, brand_name: str = "the brand"):
        self._memory = memory
        self._llm = OllamaLLM(model=model, temperature=0.3, num_predict=600)
        self._chain = _PROMPT | self._llm
        self._brand_name = brand_name

    def reflect(self, winners: list[dict], losers: list[dict]) -> dict:
        """
        Reflect over the creator's real tagged outcomes (winners vs losers, each a
        dict with at least a 'caption'; optional 'hook_pattern'/'save_rate'/
        'primary_signal'). Writes each learned rule to procedural memory
        (source='reflection') so future generation reads it. Degrades gracefully
        when there isn't enough tagged data yet.
        Returns {learned, rules, applied, winners, losers}.
        """
        if len(winners) + len(losers) < 2:
            return {
                "learned": "Not enough tagged outcomes yet — tag a few post results "
                           "(succeeded / underperformed) and I'll learn what works for you.",
                "rules": [], "applied": 0,
                "winners": len(winners), "losers": len(losers),
            }

        winners_block = "\n".join(_episode_line(e) for e in winners) or "(none recorded yet)"
        losers_block = "\n".join(_episode_line(e) for e in losers) or "(none recorded yet)"

        try:
            raw = self._chain.invoke({
                "brand_name": self._brand_name,
                "winners_block": winners_block,
                "losers_block": losers_block,
            })
            result = _parse_json(raw)
            rules = [r for r in (result.get("rules") or []) if isinstance(r, dict) and r.get("instruction")][:5]
        except (json.JSONDecodeError, ValueError):
            return {
                "learned": "Could not parse the reflection this time — try again.",
                "rules": [], "applied": 0,
                "winners": len(winners), "losers": len(losers),
            }

        applied = 0
        for r in rules:
            try:
                self._memory.upsert_procedural_rule(
                    rule_name=str(r.get("rule_name", "learned_rule"))[:60],
                    instruction=str(r["instruction"]),
                    source="reflection",
                )
                applied += 1
            except Exception:
                pass

        return {
            "learned": str(result.get("learned", "")),
            "rules": rules,
            "applied": applied,
            "winners": len(winners),
            "losers": len(losers),
        }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.memory.store import AgentMemoryStore

    # Stub memory with fake episodes so the reflection logic is testable without
    # depending on ChromaDB contents (still exercises the real Granite call).
    class _StubMemory:
        applied: list = []
        def search_episodic(self, q, n_results=5, outcome=None, **k):
            if outcome == "succeeded":
                return [
                    {"caption": "3 reasons our bomboloni sell out by noon. Which would you grab first?",
                     "hook_pattern": "number_led", "save_rate": 0.18, "primary_signal": "saves"},
                    {"caption": "Soft, gooey, freshly fried — the smell alone stops people mid-scroll.",
                     "hook_pattern": "sensory_opener", "save_rate": 0.15, "primary_signal": "shares"},
                ]
            if outcome in ("underperformed", "failed"):
                return [
                    {"caption": "We are excited to announce our new product line for our valued customers.",
                     "hook_pattern": "dead_opener", "save_rate": 0.01, "primary_signal": "none"},
                ]
            return []
        def upsert_procedural_rule(self, rule_name, instruction, **k):
            self.applied.append((rule_name, instruction))
            return rule_name

    stub = _StubMemory()
    agent = PlaybookAgent(stub, brand_name="HotCakes Bakes")
    result = agent.reflect(
        winners=stub.search_episodic("", outcome="succeeded"),
        losers=stub.search_episodic("", outcome="failed"),
    )
    print(json.dumps({k: v for k, v in result.items() if k != "rules"}, indent=2))
    for r in result["rules"]:
        print(f"  • {r['rule_name']}: {r['instruction']}")

    assert result["applied"] == len(result["rules"]) >= 1, "expected at least one learned rule written"
    assert len(stub.applied) == result["applied"], "rules should be written to procedural memory"
    print("\nOK — reflected over wins/misses and wrote", result["applied"], "rules to the playbook.")
