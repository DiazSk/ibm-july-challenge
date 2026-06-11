"""
Why Engine — Granite invocation #4.

Post-mortem analysis: takes a post's Instagram Insights + the caption +
the matched content cluster, then uses Granite to explain in plain English
why the post succeeded or failed — cross-referenced against the brand's own
established voice patterns.

What makes this different from generic analytics tools:
  brand_voice_gap — Granite compares the actual caption against the
  cluster's signature phrases, structural pattern, and tone descriptors.
  The diagnosis is brand-specific, not one-size-fits-all.

Input:  post metrics dict + caption + cluster_id
        data/brand_profile.json  (for cluster context)
Output: {verdict, diagnosis, what_worked, what_failed,
         brand_voice_gap, change_next_time} dict

Run standalone:
    python src/generation/why_engine.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

# ── Benchmark context injected into every prompt ──────────────────────────────
_BENCHMARKS = """
Instagram performance benchmarks for a micro-creator account (<5k followers):
  - Shares: the single most powerful distribution signal — even 2-3 shares on a small account matters more than 50 likes
  - Saves: indicates aspirational or educational value — high saves mean people want to return to this content
  - Reach vs Views: if reach << views, the same people are replaying (good for Reels); if reach ≈ views, little replay
  - Like-to-view ratio: <2% = low resonance, 2-5% = solid, >5% = strong viral signal
  - Avg watch time (Reels): <3s = hook failed, 3-7s = moderate, >7s = strong retention for short-form content
"""

_TEMPLATE = """\
You are a social media performance analyst for {brand_name}, a homemade artisanal bakery.

{benchmarks}

Brand voice profile for this type of content:
  Content pillar    : {content_pillar}
  Tone              : {tone_descriptors}
  Signature phrases : {signature_phrases}
  Post structure    : {structural_signature}
  Emoji style       : {emoji_style}

Post being analyzed:
  Caption   : "{caption}"
  Post type : {post_type}

Performance metrics (from Instagram Insights):
  Views     : {views}
  Reach     : {reach}
  Likes     : {likes}
  Comments  : {comments}
  Shares    : {shares}
  Saves     : {saves}{avg_watch_line}

Using these metrics AND the brand's established voice patterns above, diagnose this post.
Be specific. Reference the actual caption text and actual numbers.

Return ONLY valid JSON — no preamble, no explanation, no markdown fences:

{{
  "verdict": "<one of: succeeded | underperformed | failed>",
  "diagnosis": "<2-3 sentences: what the numbers tell you overall — be specific>",
  "what_worked": "<1-2 sentences: which metric(s) were a positive signal — use 'N/A' if nothing>",
  "what_failed": "<1-2 sentences: the specific metric or content element causing underperformance>",
  "brand_voice_gap": "<1-2 sentences: how this caption differs from the brand's established patterns — reference the signature phrases or structure above>",
  "change_next_time": "<2-3 concrete, specific changes to try on the next similar post>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "benchmarks",
        "content_pillar", "tone_descriptors", "signature_phrases",
        "structural_signature", "emoji_style",
        "caption", "post_type",
        "views", "reach", "likes", "comments", "shares", "saves",
        "avg_watch_line",
    ],
    template=_TEMPLATE,
)

_VERDICT_LABELS = {
    "succeeded"     : "✓  Succeeded",
    "underperformed": "~  Underperformed",
    "failed"        : "✗  Failed",
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
    return json.loads(text)


class WhyEngine:
    """
    Diagnoses why an Instagram post succeeded or failed, cross-referencing
    the post's metrics against the brand's own established voice clusters.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm     = OllamaLLM(model=model, temperature=0.0, num_predict=600)
        self._chain   = _PROMPT | self._llm
        self._profile = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    def analyze(
        self,
        caption             : str,
        post_type           : str,
        views               : int,
        reach               : int,
        likes               : int,
        comments            : int,
        shares              : int,
        saves               : int,
        avg_watch_time_secs : float | None = None,
        cluster_id          : int = 0,
    ) -> dict:
        """
        Returns a diagnosis dict:
        {verdict, diagnosis, what_worked, what_failed,
         brand_voice_gap, change_next_time}

        avg_watch_time_secs — Reels only, from Instagram Insights
        ("Average watch time: Xs"). Pass None for carousels/static posts.
        """
        cluster = next(
            (c for c in self._profile["cluster_profiles"] if c["cluster_id"] == cluster_id),
            self._profile["cluster_profiles"][0],
        )
        p   = cluster["profile"]
        voc = p.get("vocabulary_patterns", {})

        avg_watch_line = (
            f"\n  Avg watch time : {avg_watch_time_secs}s"
            if avg_watch_time_secs is not None
            else ""
        )

        raw = self._chain.invoke({
            "brand_name"          : self._profile["brand_name"],
            "benchmarks"          : _BENCHMARKS,
            "content_pillar"      : p.get("content_pillar", "product_showcase"),
            "tone_descriptors"    : ", ".join(p.get("tone_descriptors", [])),
            "signature_phrases"   : ", ".join(voc.get("signature_phrases", [])),
            "structural_signature": p.get("structural_signature", ""),
            "emoji_style"         : voc.get("emoji_style", ""),
            "caption"             : caption,
            "post_type"           : post_type,
            "views"               : str(views),
            "reach"               : str(reach),
            "likes"               : str(likes),
            "comments"            : str(comments),
            "shares"              : str(shares),
            "saves"               : str(saves),
            "avg_watch_line"      : avg_watch_line,
        })

        try:
            result = _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            result = {
                "verdict"         : "underperformed",
                "diagnosis"       : raw.strip(),
                "what_worked"     : "N/A",
                "what_failed"     : "Could not parse structured response.",
                "brand_voice_gap" : "N/A",
                "change_next_time": "Re-run the analysis.",
            }

        result["verdict_label"] = _VERDICT_LABELS.get(
            result.get("verdict", "underperformed"),
            result.get("verdict", "—"),
        )
        return result


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = WhyEngine()

    # Real example: a simple product post that likely underperformed
    result = engine.analyze(
        caption             = "Chocolate Cake 🤎\n\nTo order / enquire DM @hot_cakesbakes",
        post_type           = "Reel",
        views               = 420,
        reach               = 390,
        likes               = 22,
        comments            = 2,
        shares              = 1,
        saves               = 3,
        avg_watch_time_secs = 4.2,
        cluster_id          = 0,
    )

    print(f"\nVerdict: {result['verdict_label']}")
    print(f"\nDiagnosis:\n{result['diagnosis']}")
    print(f"\nWhat worked:\n{result['what_worked']}")
    print(f"\nWhat failed:\n{result['what_failed']}")
    print(f"\nBrand voice gap:\n{result['brand_voice_gap']}")
    print(f"\nChange next time:\n{result['change_next_time']}")
