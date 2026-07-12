"""
Resonance Simulator — Granite invocation #16.

Simulates how three distinct audience personas would react to a set of draft
captions before publishing — a pre-mortem for content, not just a post-mortem.
Personas are grounded in the creator's own real cluster_engagement data (not
generic archetypes): the router computes which of the creator's actual content
pillars behaves like a "superfan" audience (highest engagement rate), a
"scroll-happy" audience (highest reach, comparatively lower engagement), and a
"skeptical" audience (lowest engagement rate) — this module just role-plays
each persona given that grounding as a plain string.

Input:  captions: list[str], persona_label: str, persona_grounding: str
Output: {persona, predicted_resonance, emotional_polarity, critique_per_caption}

A second class, ResonanceSynthesizer, reads all three persona reactions and
picks a winning caption plus one concrete, actionable fix.

Note: predicted_resonance is a relative/directional signal, not a calibrated
prediction — small local models are not well-calibrated numeric self-assessors.
Frame it in the UI as "stronger/weaker than typical," not a precise percentage.

Run standalone:
    python src/generation/resonance_simulator.py
"""

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "granite3.1-dense:8b"

_REACT_TEMPLATE = """\
You are role-playing as a specific Instagram audience persona reacting to draft \
captions, before they are ever posted. Stay fully in character — be honest and \
critical, not agreeable. Do not simply praise the captions.

Persona: {persona_label}
{persona_grounding}

Here are the draft captions being considered:
{captions_block}

React as this persona would. For each caption, give a short, specific, \
in-character critique (what would make you stop scrolling, save it, or scroll past).

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "predicted_resonance": <integer 0-100, how strongly this persona would engage overall>,
  "emotional_polarity": "<one short phrase: e.g. delighted / indifferent / annoyed / intrigued>",
  "critique_per_caption": ["<critique of caption 1>", "<critique of caption 2>", "<critique of caption 3>"]
}}
"""

_SYNTHESIS_TEMPLATE = """\
You are aggregating three independent audience-persona reactions to the same \
set of draft Instagram captions, to recommend which one to post.

Draft captions:
{captions_block}

Persona reactions:
{reactions_block}

Pick the single strongest caption across all three personas combined, and give \
one concrete, actionable fix that would make it even stronger (e.g. "move the \
hook to the first sentence" or "add a sensory detail in the opening line").

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "winner_index": <integer 0-2, index of the strongest caption>,
  "predicted_resonance_score": <integer 0-100, aggregate across all three personas>,
  "reasoning": "<2-3 sentences on why this caption won>",
  "top_actionable_fix": "<one concrete, specific suggestion to improve it further>"
}}
"""

_REACT_PROMPT = PromptTemplate(
    input_variables=["persona_label", "persona_grounding", "captions_block"],
    template=_REACT_TEMPLATE,
)
_SYNTHESIS_PROMPT = PromptTemplate(
    input_variables=["captions_block", "reactions_block"],
    template=_SYNTHESIS_TEMPLATE,
)


def _format_captions(captions: list[str]) -> str:
    return "\n".join(f"{i + 1}. {c}" for i, c in enumerate(captions))


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


class PersonaSimulator:
    """
    Role-plays a single, data-grounded audience persona reacting to a batch of
    draft captions. Never raises — falls back to a neutral, clearly-labeled
    placeholder reaction if Granite's output can't be parsed, so one bad
    persona call never breaks the whole panel.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.4, num_predict=350)
        self._chain = _REACT_PROMPT | self._llm

    def react(self, captions: list[str], persona_label: str, persona_grounding: str) -> dict:
        """
        Granite Call #16.
        Returns {persona, predicted_resonance, emotional_polarity, critique_per_caption}.
        """
        raw = self._chain.invoke({
            "persona_label": persona_label,
            "persona_grounding": persona_grounding,
            "captions_block": _format_captions(captions),
        })

        try:
            result = _parse_json(raw)
            result["persona"] = persona_label
            result["predicted_resonance"] = max(0, min(100, int(result.get("predicted_resonance", 50))))
            critiques = result.get("critique_per_caption") or []
            while len(critiques) < len(captions):
                critiques.append("")
            result["critique_per_caption"] = critiques[: len(captions)]
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            return {
                "persona": persona_label,
                "predicted_resonance": 50,
                "emotional_polarity": "uncertain",
                "critique_per_caption": ["Could not parse this persona's reaction."] * len(captions),
            }


class ResonanceSynthesizer:
    """
    Aggregates three persona reactions into a single recommendation: which
    caption wins, and one concrete fix to make it stronger.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.3, num_predict=300)
        self._chain = _SYNTHESIS_PROMPT | self._llm

    def synthesize(self, persona_reactions: list[dict], captions: list[str]) -> dict:
        """
        Granite Call #16 (final call).
        Returns {winner_index, predicted_resonance_score, reasoning, top_actionable_fix}.
        """
        reactions_block = "\n\n".join(
            f"{r.get('persona', 'Unknown persona')} "
            f"(resonance {r.get('predicted_resonance', '?')}, mood: {r.get('emotional_polarity', '?')}):\n"
            + "\n".join(f"  - Caption {i + 1}: {c}" for i, c in enumerate(r.get("critique_per_caption", [])))
            for r in persona_reactions
        )

        raw = self._chain.invoke({
            "captions_block": _format_captions(captions),
            "reactions_block": reactions_block,
        })

        try:
            result = _parse_json(raw)
            winner = int(result.get("winner_index", 0))
            result["winner_index"] = winner if 0 <= winner < len(captions) else 0
            result["predicted_resonance_score"] = max(0, min(100, int(result.get("predicted_resonance_score", 50))))
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            return {
                "winner_index": 0,
                "predicted_resonance_score": 50,
                "reasoning": "Could not parse the synthesis — defaulting to the first caption.",
                "top_actionable_fix": "",
            }


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    captions = [
        "Fresh Bomboloni just dropped, made with love!",
        "There's something about freshly fried Bomboloni, hot coffee & old songs… it just feels like comfort in every bite",
        "New croissant flavor today, come try it!",
    ]

    simulator = PersonaSimulator()
    reactions = [
        simulator.react(
            captions,
            "The Devotee",
            "This persona behaves like your highest-engagement content pillar — they save posts, "
            "comment often, and expect signature vocabulary and sensory detail.",
        ),
        simulator.react(
            captions,
            "The Skeptic",
            "This persona behaves like your lowest-engagement content pillar — they scroll past "
            "generic announcements and need a strong, specific hook to stop.",
        ),
    ]
    for r in reactions:
        print(json.dumps(r, indent=2))

    synthesizer = ResonanceSynthesizer()
    synthesis = synthesizer.synthesize(reactions, captions)
    print(json.dumps(synthesis, indent=2))
