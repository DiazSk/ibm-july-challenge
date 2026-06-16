"""
Script Generator — Granite invocation #9.

Takes a high-performing reference post (caption + engagement metrics) and
generates a structured content script in the brand's voice, adapted to the
chosen format (Reel / Carousel / Static Post).

The premise: if we know what worked (the reference post), Granite can distill
the hook style, emotional angle, and pacing from its caption+metrics, then
apply the brand's cluster voice to generate a new script in the same mold.

Output formats:
  Reel     — {hook, opening_line, voiceover_script, shot_suggestions, caption, hashtags}
  Carousel — {hook, slides: [{slide, headline, body}], cta_slide, caption, hashtags}
  Static   — {headline, caption, hashtags, visual_direction}

Run standalone:
    python src/generation/script_generator.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_CLUSTER_ID_LABELS = {
    0: "Homemade Classics",
    1: "Fusion Specials",
    2: "Behind the Scenes",
    3: "Nutella Series",
    4: "Bomboloni",
}

_TEMPLATE = """\
You are a content strategist for {brand_name}, a homemade artisanal bakery on Instagram.

A reference post performed exceptionally well:
  Caption  : {reference_caption}
  Metrics  : {metrics_summary}

Brand voice for this script (cluster: {cluster_label}):
  Tone              : {tone_descriptors}
  Recurring words   : {recurring_words}
  Signature phrases : {signature_phrases}
  Avoided terms     : {avoided_terms}

Task: Create a brand-new {content_format} script inspired by what made the reference \
post successful. Apply the brand voice above. Use a maximum of 5 hashtags.

{format_instructions}

Return ONLY valid JSON — no preamble, no markdown fences:
{json_schema}
"""

_FORMAT_INSTRUCTIONS = {
    "Reel": (
        "Structure the Reel script with:\n"
        "  • hook: the first on-screen text or spoken line (max 8 words, punchy)\n"
        "  • opening_line: the first full spoken sentence to deliver energy\n"
        "  • voiceover_script: 4-6 sentences of voiceover or on-screen text, conversational\n"
        "  • shot_suggestions: 3-4 quick shot ideas (e.g. 'close-up of dough being filled')\n"
        "  • caption: Instagram caption for the Reel (under 150 words)\n"
        "  • hashtags: list of exactly 5 hashtag strings (with #)"
    ),
    "Carousel": (
        "Structure the Carousel with 5-6 slides:\n"
        "  • hook: the cover slide headline (max 8 words)\n"
        "  • slides: array of {slide (number), headline (short), body (1-2 sentences)}\n"
        "  • cta_slide: the final slide's call-to-action text\n"
        "  • caption: Instagram caption for the Carousel (under 150 words)\n"
        "  • hashtags: list of exactly 5 hashtag strings (with #)"
    ),
    "Static": (
        "Structure the Static Post with:\n"
        "  • headline: overlay text for the image (max 8 words)\n"
        "  • caption: Instagram caption (under 150 words)\n"
        "  • hashtags: list of exactly 5 hashtag strings (with #)\n"
        "  • visual_direction: one sentence describing the image composition and mood"
    ),
}

_JSON_SCHEMAS = {
    "Reel": (
        '{{\n'
        '  "hook": "<max 8 words>",\n'
        '  "opening_line": "<first spoken line>",\n'
        '  "voiceover_script": "<4-6 sentences>",\n'
        '  "shot_suggestions": ["<shot 1>", "<shot 2>", "<shot 3>"],\n'
        '  "caption": "<Instagram caption>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}}'
    ),
    "Carousel": (
        '{{\n'
        '  "hook": "<cover slide headline>",\n'
        '  "slides": [\n'
        '    {{"slide": 1, "headline": "<short>", "body": "<1-2 sentences>"}},\n'
        '    {{"slide": 2, "headline": "<short>", "body": "<1-2 sentences>"}}\n'
        '  ],\n'
        '  "cta_slide": "<final call to action>",\n'
        '  "caption": "<Instagram caption>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}}'
    ),
    "Static": (
        '{{\n'
        '  "headline": "<overlay text, max 8 words>",\n'
        '  "caption": "<Instagram caption>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '  "visual_direction": "<one sentence on image composition and mood>",\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}}'
    ),
}

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "reference_caption", "metrics_summary", "cluster_label",
        "tone_descriptors", "recurring_words", "signature_phrases", "avoided_terms",
        "content_format", "format_instructions", "json_schema",
    ],
    template=_TEMPLATE,
)


def _parse_script(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


class ScriptGenerator:
    """
    Generates structured content scripts (Reel/Carousel/Static) inspired by a
    high-performing reference post, applying the brand's cluster voice.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.5, num_predict=700)
        self._chain = _PROMPT | self._llm
        self._profile: dict = json.loads(
            BRAND_PROFILE_PATH.read_text(encoding="utf-8")
        )

    def generate(
        self,
        reference_caption: str,
        metrics: dict,
        content_format: str = "Reel",
        cluster_id: int = 0,
    ) -> dict:
        """
        Returns a structured script dict plus a `format` and `reasoning` field.
        """
        cluster = next(
            (c for c in self._profile["cluster_profiles"] if c["cluster_id"] == cluster_id),
            self._profile["cluster_profiles"][0],
        )
        p   = cluster["profile"]
        voc = p.get("vocabulary_patterns", {})

        engagement = metrics.get("likes", 0) + metrics.get("saves", 0) + metrics.get("comments", 0)
        metrics_summary = (
            f"Views: {metrics.get('views', 0):,} | "
            f"Reach: {metrics.get('reach', 0):,} | "
            f"Likes: {metrics.get('likes', 0):,} | "
            f"Comments: {metrics.get('comments', 0):,} | "
            f"Shares: {metrics.get('shares', 0):,} | "
            f"Saves: {metrics.get('saves', 0):,} | "
            f"Total engagement: {engagement:,}"
        )

        fmt = content_format if content_format in _FORMAT_INSTRUCTIONS else "Reel"

        raw = self._chain.invoke({
            "brand_name"         : self._profile["brand_name"],
            "reference_caption"  : reference_caption,
            "metrics_summary"    : metrics_summary,
            "cluster_label"      : _CLUSTER_ID_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
            "tone_descriptors"   : ", ".join(p.get("tone_descriptors", [])),
            "recurring_words"    : ", ".join(voc.get("recurring_words", [])),
            "signature_phrases"  : ", ".join(voc.get("signature_phrases", [])),
            "avoided_terms"      : ", ".join(p.get("avoided_terms", [])),
            "content_format"     : fmt,
            "format_instructions": _FORMAT_INSTRUCTIONS[fmt],
            "json_schema"        : _JSON_SCHEMAS[fmt],
        })

        try:
            result = _parse_script(raw)
            result["format"] = fmt
            return result
        except (json.JSONDecodeError, ValueError):
            return {
                "format"   : fmt,
                "caption"  : raw.strip(),
                "reasoning": "Raw response (JSON parse failed)",
            }


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    gen = ScriptGenerator()
    result = gen.generate(
        reference_caption=(
            "Freshly fried Nutella Bomboloni 🍩 Warm, golden, and filled to the brim. "
            "These sell out every single Friday — DM us to pre-order! "
            "#NutellaBomboloni #HotCakesBakes #MumbaiFood"
        ),
        metrics={"views": 45000, "reach": 32000, "likes": 2100, "comments": 87, "shares": 340, "saves": 520},
        content_format="Reel",
        cluster_id=3,
    )
    print(json.dumps(result, indent=2))
