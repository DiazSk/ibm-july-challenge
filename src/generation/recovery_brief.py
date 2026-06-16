"""
Recovery Brief Generator — Granite invocation #10.

Chained from Why Engine output when a post underperforms or fails.
Generates a strategic recovery: a new hook, recommended format, and
a ~150-word script in the brand's established voice.

Input:  Why Engine diagnosis fields + cluster_id
        data/brand_profile.json  (for cluster voice context)
Output: {new_hook, recommended_format, recovery_script, reasoning}

Not called from its own endpoint — wired into analyze.py after WhyEngine.
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_TEMPLATE = """\
You are a content strategist for {brand_name}, a homemade artisanal bakery.

A recent Instagram post underperformed. Here is the Why Engine diagnosis:
  Diagnosis       : {diagnosis}
  What failed     : {what_failed}
  Brand voice gap : {brand_voice_gap}

Brand voice context for this content pillar:
  Content pillar    : {content_pillar}
  Tone              : {tone_descriptors}
  Signature phrases : {signature_phrases}
  Post structure    : {structural_signature}

Your task: generate a recovery brief that directly addresses the identified failure.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "new_hook": "<a single punchy opening line that fixes the failure — max 15 words>",
  "recommended_format": "<one of: Reel | Carousel | Static>",
  "recovery_script": "<~150-word script in brand voice for the recommended format — include hook, body, CTA>",
  "reasoning": "<1-2 sentences: why this approach directly addresses the original failure>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name",
        "diagnosis",
        "what_failed",
        "brand_voice_gap",
        "content_pillar",
        "tone_descriptors",
        "signature_phrases",
        "structural_signature",
    ],
    template=_TEMPLATE,
)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


class RecoveryBriefGenerator:
    """
    Granite invocation #10 — chained from Why Engine output.

    Generates a strategic recovery brief when a post underperforms or fails,
    grounded in the brand's established voice for the matched content cluster.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm     = OllamaLLM(model=model, temperature=0.3, num_predict=500)
        self._chain   = _PROMPT | self._llm
        self._profile = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    def generate(
        self,
        diagnosis      : str,
        what_failed    : str,
        brand_voice_gap: str,
        cluster_id     : int = 0,
    ) -> dict:
        """
        Returns {new_hook, recommended_format, recovery_script, reasoning}.
        Raises on Granite failure — caller catches and treats as non-fatal.
        """
        cluster = next(
            (c for c in self._profile["cluster_profiles"] if c["cluster_id"] == cluster_id),
            self._profile["cluster_profiles"][0],
        )
        p   = cluster["profile"]
        voc = p.get("vocabulary_patterns", {})

        raw = self._chain.invoke({
            "brand_name"          : self._profile["brand_name"],
            "diagnosis"           : diagnosis,
            "what_failed"         : what_failed,
            "brand_voice_gap"     : brand_voice_gap,
            "content_pillar"      : p.get("content_pillar", "product_showcase"),
            "tone_descriptors"    : ", ".join(p.get("tone_descriptors", [])),
            "signature_phrases"   : ", ".join(voc.get("signature_phrases", [])),
            "structural_signature": p.get("structural_signature", ""),
        })

        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            return {
                "new_hook"           : "Let's try a different angle.",
                "recommended_format" : "Reel",
                "recovery_script"    : raw.strip(),
                "reasoning"          : "Could not parse structured response from Granite.",
            }
