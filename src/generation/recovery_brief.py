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
  Recurring words   : {recurring_words}
  Signature phrases : {signature_phrases}
  Post structure    : {structural_signature}
  Avoided terms     : {avoided_terms}

Your task: generate a recovery brief that directly addresses the identified failure.
Build the new angle around one of {brand_name}'s own recurring words or signature phrases
above. Do not keep the failed post's subject matter, and do not suggest an angle, hook, or
script built around any avoided term above.

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
        "recurring_words",
        "signature_phrases",
        "structural_signature",
        "avoided_terms",
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

        # Avoided terms are a brand-wide rule, not just this cluster's own list —
        # matches how /api/brand/profile unions them for the Brand Voice page.
        avoided_terms: list[str] = []
        for cp in self._profile["cluster_profiles"]:
            for term in cp["profile"].get("avoided_terms", []):
                if term not in avoided_terms:
                    avoided_terms.append(term)

        raw = self._chain.invoke({
            "brand_name"          : self._profile["brand_name"],
            "diagnosis"           : diagnosis,
            "what_failed"         : what_failed,
            "brand_voice_gap"     : brand_voice_gap,
            "content_pillar"      : p.get("content_pillar", "product_showcase"),
            "tone_descriptors"    : ", ".join(p.get("tone_descriptors", [])),
            "recurring_words"     : ", ".join(voc.get("recurring_words", [])),
            "signature_phrases"   : ", ".join(voc.get("signature_phrases", [])),
            "structural_signature": p.get("structural_signature", ""),
            "avoided_terms"       : ", ".join(avoided_terms),
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


if __name__ == "__main__":
    # No Ollama call — just proves the brand-wide avoided_terms union is wired
    # correctly (this was the actual bug: it used to be per-cluster only, so a
    # term avoided by cluster 1 never reached a recovery brief for cluster 0).
    profile = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))
    merged: list[str] = []
    for cp in profile["cluster_profiles"]:
        for term in cp["profile"].get("avoided_terms", []):
            if term not in merged:
                merged.append(term)
    assert "Vegan" in merged and "Gluten-free" in merged, merged
    print(f"OK — {len(merged)} brand-wide avoided terms: {merged}")
