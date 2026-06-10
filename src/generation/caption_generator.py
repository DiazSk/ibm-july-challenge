"""
Caption Generator — Granite invocation #2.

Given a content brief and a brand profile cluster, generates 3 on-brand
Instagram caption variants with per-attribute reasoning.

Input:  data/brand_profile.json
        content brief (product, occasion, desired_feel, cluster_id)
Output: list of {caption, reasoning} dicts

Run standalone:
    python src/generation/caption_generator.py
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
You are a brand copywriter for {brand_name}, a homemade artisanal bakery on Instagram.

Brand voice profile for this content type:
  Content pillar    : {content_pillar}
  Tone              : {tone_descriptors}
  Recurring words   : {recurring_words}
  Signature phrases : {signature_phrases}
  Emoji style       : {emoji_style}
  Post structure    : {structural_signature}
  Avoided terms     : {avoided_terms}

Content brief:
  Product  : {product}
  Occasion : {occasion}
  Feel     : {desired_feel}

Write 3 distinct Instagram caption variants. Each must:
- Match the brand voice profile above
- Stay under 150 words
- Not use any of the avoided terms
- Sound like a real person, not a marketing template
- Each variant should take a different angle (e.g. emotional, sensory, humorous)

Return ONLY valid JSON — no preamble, no explanation, no markdown fences:

[
  {{
    "caption": "<caption text here>",
    "reasoning": "<1-2 sentences: which brand attributes you applied>"
  }},
  {{
    "caption": "<caption text here>",
    "reasoning": "<1-2 sentences: which brand attributes you applied>"
  }},
  {{
    "caption": "<caption text here>",
    "reasoning": "<1-2 sentences: which brand attributes you applied>"
  }}
]
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "content_pillar", "tone_descriptors", "recurring_words",
        "signature_phrases", "emoji_style", "structural_signature", "avoided_terms",
        "product", "occasion", "desired_feel",
    ],
    template=_TEMPLATE,
)


def _parse_captions(raw: str) -> list[dict]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    end   = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


class CaptionGenerator:
    """
    Generates 3 on-brand caption variants for a given content brief
    by injecting the matching cluster profile from brand_profile.json.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.7, num_predict=900)
        self._chain = _PROMPT | self._llm
        self._profile: dict = json.loads(
            BRAND_PROFILE_PATH.read_text(encoding="utf-8")
        )

    # ── Public ────────────────────────────────────────────────────────────────

    def cluster_profiles(self) -> list[dict]:
        return self._profile["cluster_profiles"]

    def generate(
        self,
        product: str,
        occasion: str,
        desired_feel: str,
        cluster_id: int = 0,
    ) -> list[dict]:
        """
        Returns a list of 3 dicts: [{caption, reasoning}, ...].
        Falls back to cluster 0 if the requested cluster_id is not found.
        """
        cluster = next(
            (c for c in self._profile["cluster_profiles"] if c["cluster_id"] == cluster_id),
            self._profile["cluster_profiles"][0],
        )
        p   = cluster["profile"]
        voc = p.get("vocabulary_patterns", {})

        raw = self._chain.invoke({
            "brand_name"          : self._profile["brand_name"],
            "content_pillar"      : p.get("content_pillar", "product_showcase"),
            "tone_descriptors"    : ", ".join(p.get("tone_descriptors", [])),
            "recurring_words"     : ", ".join(voc.get("recurring_words", [])),
            "signature_phrases"   : ", ".join(voc.get("signature_phrases", [])),
            "emoji_style"         : voc.get("emoji_style", ""),
            "structural_signature": p.get("structural_signature", ""),
            "avoided_terms"       : ", ".join(p.get("avoided_terms", [])),
            "product"             : product,
            "occasion"            : occasion,
            "desired_feel"        : desired_feel or "on-brand and engaging",
        })

        try:
            return _parse_captions(raw)
        except (json.JSONDecodeError, ValueError):
            return [{"caption": raw.strip(), "reasoning": "Raw response (JSON parse failed)"}]


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    gen = CaptionGenerator()
    results = gen.generate(
        product="Nutella Bomboloni",
        occasion="Weekend craving post",
        desired_feel="Indulgent and enticing — emphasise the Nutella filling",
        cluster_id=3,
    )
    for i, r in enumerate(results, 1):
        print(f"\n{'─'*60}")
        print(f"Variant {i}")
        print(f"{'─'*60}")
        print(r.get("caption", ""))
        print(f"\nReasoning: {r.get('reasoning', '')}")
