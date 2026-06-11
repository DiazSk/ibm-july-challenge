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
# Plain-English thresholds that Granite uses to calibrate its diagnosis.
_BENCHMARKS = """
Instagram performance benchmarks for a micro-creator account (<5k followers):
  - Hook rate (% watching past 3s): <20% = weak hook, 20-35% = average, >35% = strong
  - Watch time %: <30% = skipped, 30-50% = moderate, >50% = algorithm-promoted
  - Shares: the single most important distribution signal — even 2-3 shares on a small account matters
  - Saves: indicates aspirational or educational value — important for Reels that teach or inspire
  - Like-to-view ratio: <2% = low engagement, 2-5% = good, >5% = viral signal
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
  Caption     : "{caption}"
  Post type   : {post_type}
  Posted      : {posted_day}, {posted_hour}

Performance metrics:
  Views       : {views}
  Watch time  : {watch_time_pct}% watched
  Hook rate   : {hook_rate}% watched past 3 seconds
  Shares      : {shares}
  Saves       : {saves}
  Likes       : {likes}
  Comments    : {comments}

Using these metrics AND the brand's established voice patterns above, diagnose this post.
Be specific. Do not give generic advice. Reference the actual caption and actual numbers.

Return ONLY valid JSON — no preamble, no explanation, no markdown fences:

{{
  "verdict": "<one of: succeeded | underperformed | failed>",
  "diagnosis": "<2-3 sentences: what the numbers tell you overall — be specific>",
  "what_worked": "<1-2 sentences: what drove any positive signal — use 'N/A' if nothing>",
  "what_failed": "<1-2 sentences: the specific metric or content element causing the issue>",
  "brand_voice_gap": "<1-2 sentences: how this caption differs from the brand's established pattern — reference specific signature phrases or structural elements>",
  "change_next_time": "<2-3 concrete, specific changes to make on the next similar post>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "benchmarks",
        "content_pillar", "tone_descriptors", "signature_phrases",
        "structural_signature", "emoji_style",
        "caption", "post_type", "posted_day", "posted_hour",
        "views", "watch_time_pct", "hook_rate",
        "shares", "saves", "likes", "comments",
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
        caption      : str,
        post_type    : str,
        posted_day   : str,
        posted_hour  : str,
        views        : int,
        watch_time_pct: float,
        hook_rate    : float,
        shares       : int,
        saves        : int,
        likes        : int,
        comments     : int,
        cluster_id   : int = 0,
    ) -> dict:
        """
        Returns a diagnosis dict:
        {verdict, diagnosis, what_worked, what_failed,
         brand_voice_gap, change_next_time}
        """
        cluster = next(
            (c for c in self._profile["cluster_profiles"] if c["cluster_id"] == cluster_id),
            self._profile["cluster_profiles"][0],
        )
        p   = cluster["profile"]
        voc = p.get("vocabulary_patterns", {})

        raw = self._chain.invoke({
            "brand_name"         : self._profile["brand_name"],
            "benchmarks"         : _BENCHMARKS,
            "content_pillar"     : p.get("content_pillar", "product_showcase"),
            "tone_descriptors"   : ", ".join(p.get("tone_descriptors", [])),
            "signature_phrases"  : ", ".join(voc.get("signature_phrases", [])),
            "structural_signature": p.get("structural_signature", ""),
            "emoji_style"        : voc.get("emoji_style", ""),
            "caption"            : caption,
            "post_type"          : post_type,
            "posted_day"         : posted_day,
            "posted_hour"        : posted_hour,
            "views"              : str(views),
            "watch_time_pct"     : str(watch_time_pct),
            "hook_rate"          : str(hook_rate),
            "shares"             : str(shares),
            "saves"              : str(saves),
            "likes"              : str(likes),
            "comments"           : str(comments),
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
        caption       = "Chocolate Cake 🤎\n\nTo order / enquire DM @hot_cakesbakes",
        post_type     = "Reel",
        posted_day    = "Tuesday",
        posted_hour   = "7:00 PM",
        views         = 420,
        watch_time_pct= 28.0,
        hook_rate     = 18.0,
        shares        = 1,
        saves         = 3,
        likes         = 22,
        comments      = 2,
        cluster_id    = 0,
    )

    print(f"\nVerdict: {result['verdict_label']}")
    print(f"\nDiagnosis:\n{result['diagnosis']}")
    print(f"\nWhat worked:\n{result['what_worked']}")
    print(f"\nWhat failed:\n{result['what_failed']}")
    print(f"\nBrand voice gap:\n{result['brand_voice_gap']}")
    print(f"\nChange next time:\n{result['change_next_time']}")
