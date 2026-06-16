"""
Blank Page Solver — Granite invocations #6 and #7.

A two-step engine that starts from "what happened today?" and produces 3
distinct creative directions, pre-wired into CaptionGenerator.

Step 1 — MomentAnalyzer (Granite #6):
  Takes a free-text description of a real moment.
  Extracts emotional_core, business_signal, and maps to the best cluster.

Step 2 — DirectionGenerator (Granite #7):
  Takes the moment analysis from Step 1.
  Proposes 3 genuinely distinct creative angles for telling the story.

The output of DirectionGenerator pre-populates:
  CaptionGenerator.generate(desired_feel=angle+" "+tone_note, cluster_id=best_cluster_id)
No changes to CaptionGenerator — this is a pre-fill mechanism, not a replacement.

Run standalone:
    python src/generation/blank_page_solver.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_PILLAR_LABELS = {
    "product_showcase"   : "Product Showcase",
    "behind_scenes"      : "Behind the Scenes",
    "seasonal_special"   : "Seasonal Special",
    "customer_connection": "Customer Connection",
    "brand_story"        : "Brand Story",
}

# ── Moment Analyzer (Granite #6) ─────────────────────────────────────────────

_ANALYZER_TEMPLATE = """\
You are a creative director for {brand_name}, a homemade artisan bakery.

A baker just described something that happened in their work or life today:
"{moment_text}"

Available content clusters (each is a creative territory the brand has established):
{cluster_menu}

Your job: find the creative opportunity hidden in this moment.

Extract:
  1. emotional_core — what the creator is actually feeling right now (1 short phrase)
  2. business_signal — what this moment means for the business (1 short phrase)
  3. best_cluster_id — which cluster (0-4) best matches this moment's energy
  4. cluster_reason — why that cluster fits this moment (1 sentence)

Return ONLY valid JSON — no preamble, no markdown fences:
{{
  "emotional_core": "<1 short phrase>",
  "business_signal": "<1 short phrase>",
  "best_cluster_id": <integer 0-4>,
  "cluster_reason": "<1 sentence>"
}}
"""

_ANALYZER_PROMPT = PromptTemplate(
    input_variables=["brand_name", "moment_text", "cluster_menu"],
    template=_ANALYZER_TEMPLATE,
)

# ── Direction Generator (Granite #7) ─────────────────────────────────────────

_DIRECTION_TEMPLATE = """\
You are a creative director for {brand_name}, a homemade artisan bakery.

A baker described this moment: "{moment_text}"

What this moment is really about:
  Emotional core  : {emotional_core}
  Business signal : {business_signal}
  Best cluster    : {cluster_label}
  Why             : {cluster_reason}

Propose 3 distinct creative directions for an Instagram post about this moment. \
Each direction is a different angle for telling the same story — think like a \
creative director pitching 3 concepts to a client. Make the angles genuinely \
different (e.g. vulnerable + honest, playful + surprising, sensory + product-led). \
Do not repeat the same approach.

Return ONLY valid JSON — no preamble, no markdown fences:
[
  {{
    "direction_title": "<5-7 word title>",
    "angle": "<1-2 sentences: the creative angle and approach>",
    "tone_note": "<1 sentence: which brand voice element to lead with>"
  }},
  {{
    "direction_title": "<5-7 word title>",
    "angle": "<1-2 sentences: the creative angle and approach>",
    "tone_note": "<1 sentence: which brand voice element to lead with>"
  }},
  {{
    "direction_title": "<5-7 word title>",
    "angle": "<1-2 sentences: the creative angle and approach>",
    "tone_note": "<1 sentence: which brand voice element to lead with>"
  }}
]
"""

_DIRECTION_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "moment_text",
        "emotional_core", "business_signal",
        "cluster_label", "cluster_reason",
    ],
    template=_DIRECTION_TEMPLATE,
)


def _parse_json_obj(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _parse_json_arr(raw: str) -> list:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    end   = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _build_cluster_menu(brand_profile: dict) -> str:
    lines = []
    for cp in brand_profile["cluster_profiles"]:
        p = cp.get("profile", {})
        if p.get("parse_error"):
            continue
        raw_pillar = p.get("content_pillar", "product_showcase")
        pillar     = _PILLAR_LABELS.get(raw_pillar, raw_pillar.replace("_", " ").title())
        tones      = p.get("tone_descriptors", [])
        tone_str   = tones[0] if tones else ""
        phrases    = p.get("vocabulary_patterns", {}).get("signature_phrases", [])
        example    = phrases[0] if phrases else ""
        line = f"  C{cp['cluster_id']}: {pillar} — tone: {tone_str}"
        if example:
            line += f', example: "{example}"'
        lines.append(line)
    return "\n".join(lines)


class MomentAnalyzer:
    """
    Granite Call #6 — extracts emotional core + business signal from a moment
    description and maps it to the brand's best-fit content cluster.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm     = OllamaLLM(model=model, temperature=0.0, num_predict=300)
        self._chain   = _ANALYZER_PROMPT | self._llm
        self._profile = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    def analyze(self, moment_text: str) -> dict:
        """
        Returns {emotional_core, business_signal, best_cluster_id, cluster_reason}.
        best_cluster_id is always an int.
        """
        raw = self._chain.invoke({
            "brand_name"  : self._profile["brand_name"],
            "moment_text" : moment_text.strip(),
            "cluster_menu": _build_cluster_menu(self._profile),
        })
        try:
            result = _parse_json_obj(raw)
            result["best_cluster_id"] = int(result.get("best_cluster_id", 0))
            return result
        except (json.JSONDecodeError, ValueError, KeyError):
            return {
                "emotional_core"  : "—",
                "business_signal" : "—",
                "best_cluster_id" : 0,
                "cluster_reason"  : raw.strip(),
            }


class DirectionGenerator:
    """
    Granite Call #7 — proposes 3 distinct creative directions for a post
    based on the analysis from MomentAnalyzer.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm     = OllamaLLM(model=model, temperature=0.6, num_predict=600)
        self._chain   = _DIRECTION_PROMPT | self._llm
        self._profile = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    def _cluster_label(self, cluster_id: int) -> str:
        for cp in self._profile["cluster_profiles"]:
            if cp["cluster_id"] == cluster_id:
                p          = cp.get("profile", {})
                raw_pillar = p.get("content_pillar", "product_showcase")
                pillar     = _PILLAR_LABELS.get(raw_pillar, raw_pillar.replace("_", " ").title())
                tones      = p.get("tone_descriptors", [])
                tone_str   = ", ".join(tones[:2]) if tones else ""
                return f"C{cluster_id} {pillar} ({tone_str})"
        return f"C{cluster_id}"

    def generate(self, moment_analysis: dict, moment_text: str) -> list[dict]:
        """
        Returns list of up to 3 dicts: [{direction_title, angle, tone_note}].
        """
        cluster_id = moment_analysis.get("best_cluster_id", 0)
        raw = self._chain.invoke({
            "brand_name"    : self._profile["brand_name"],
            "moment_text"   : moment_text.strip(),
            "emotional_core": moment_analysis.get("emotional_core", ""),
            "business_signal": moment_analysis.get("business_signal", ""),
            "cluster_label" : self._cluster_label(cluster_id),
            "cluster_reason": moment_analysis.get("cluster_reason", ""),
        })
        try:
            directions = _parse_json_arr(raw)
            return directions[:3]
        except (json.JSONDecodeError, ValueError):
            return [{
                "direction_title": "Direct approach",
                "angle"          : raw.strip(),
                "tone_note"      : "",
            }]


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    analyzer  = MomentAnalyzer()
    generator = DirectionGenerator()

    moment = (
        "I just got a DM from a cafe owner asking for a bulk weekly order — "
        "my first B2B client. I don't even know how to feel about it."
    )

    print("Analyzing moment…")
    analysis = analyzer.analyze(moment)
    print(f"  Emotional core  : {analysis['emotional_core']}")
    print(f"  Business signal : {analysis['business_signal']}")
    print(f"  Best cluster    : C{analysis['best_cluster_id']}")
    print(f"  Reason          : {analysis['cluster_reason']}")

    print("\nGenerating creative directions…")
    directions = generator.generate(analysis, moment)
    for i, d in enumerate(directions, 1):
        print(f"\nDirection {i}: {d['direction_title']}")
        print(f"  Angle     : {d['angle']}")
        print(f"  Tone note : {d['tone_note']}")
