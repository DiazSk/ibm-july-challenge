"""
Image Prompt Generator — Granite invocation #3.

Given a chosen caption and product name, generates a Midjourney/DALL-E
compatible image prompt that matches the brand's warm, artisanal aesthetic.

Input:  chosen caption string, product name
Output: {prompt, style_notes} dict

Run standalone:
    python src/generation/image_prompt_generator.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_BRAND_AESTHETIC = (
    "warm, intimate home-kitchen atmosphere; "
    "soft natural window light or warm golden hour; "
    "muted warm tones — cream, caramel, chocolate brown, dusty rose; "
    "editorial food photography style; "
    "artisanal textures and imperfect handmade details; "
    "no harsh flash, no stark white studio background, no corporate polish"
)

_TEMPLATE = """\
You are a visual art director for {brand_name}, a homemade artisanal bakery.

Brand aesthetic: {brand_aesthetic}

Instagram caption to visualize:
"{caption}"

Product being shown: {product}

Generate one image generation prompt for Midjourney or DALL-E 3 that:
1. Visually represents the caption's mood and emotional energy
2. Stays true to the warm, homemade, artisanal aesthetic
3. Specifies subject, composition, lighting, color palette, photographic style, and mood

Return ONLY valid JSON — no preamble, no explanation, no markdown fences:

{{
  "prompt": "<complete image generation prompt, 50-90 words>",
  "style_notes": "<one sentence: the key visual mood this image should convey>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=["brand_name", "brand_aesthetic", "caption", "product"],
    template=_TEMPLATE,
)


def _repair_missing_commas(text: str) -> str:
    """
    Granite occasionally omits the comma between two key-value pairs, e.g.:
        "prompt": "...mood."
        "style_notes": "..."
    Insert a comma wherever a closing quote is followed only by whitespace and
    then another quoted key + colon (i.e. no comma already present).
    """
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _extract_fields_by_regex(raw: str) -> dict | None:
    """
    Last-resort fallback: pull "prompt" and "style_notes" string values directly
    out of the raw text via regex, ignoring overall JSON validity. Used only when
    both the direct and comma-repaired json.loads attempts fail, so the UI never
    has to display a raw, garbled LLM response.
    """
    prompt_match = re.search(r'"prompt"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
    style_match  = re.search(r'"style_notes"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
    if not prompt_match:
        return None
    return {
        "prompt"     : prompt_match.group(1).strip(),
        "style_notes": style_match.group(1).strip() if style_match else "",
    }


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    repaired = _repair_missing_commas(text)
    return json.loads(repaired)


class ImagePromptGenerator:
    """
    Generates a Midjourney/DALL-E image direction prompt from a chosen caption.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm        = OllamaLLM(model=model, temperature=0.5, num_predict=400)
        self._chain      = _PROMPT | self._llm
        self._brand_name = json.loads(
            BRAND_PROFILE_PATH.read_text(encoding="utf-8")
        )["brand_name"]

    def generate(self, caption: str, product: str) -> dict:
        """
        Returns {prompt, style_notes}.
        Falls back to a template-based response on JSON parse failure.
        """
        raw = self._chain.invoke({
            "brand_name"      : self._brand_name,
            "brand_aesthetic" : _BRAND_AESTHETIC,
            "caption"         : caption,
            "product"         : product,
        })

        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        extracted = _extract_fields_by_regex(raw)
        if extracted:
            return extracted

        return {
            "prompt"      : raw.strip(),
            "style_notes" : "Raw response (JSON parse failed)",
        }


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    gen = ImagePromptGenerator()
    result = gen.generate(
        caption=(
            "There's something about freshly fried Bomboloni, hot coffee & old songs… "
            "it just feels like comfort in every bite ☕🍩🎶 "
            "Soft, warm & made fresh — once you try, you'll crave it again 🤤"
        ),
        product="Nutella Bomboloni",
    )
    print("Prompt:")
    print(result["prompt"])
    print("\nStyle notes:", result["style_notes"])
