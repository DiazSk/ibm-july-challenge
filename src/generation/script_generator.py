"""
Script Generator — Granite invocation #9.

Takes a high-performing reference post (caption + engagement metrics) and
generates a structured content script in the brand's voice, adapted to the
chosen format (Reel / Carousel / Static Post).

The premise: if we know what worked (the reference post), Granite can distill
the hook style, emotional angle, and pacing from its caption+metrics, then
apply the brand's cluster voice to generate a new script in the same mold.

Output formats:
  Reel     — {hook, clips: [{clip_number, duration_secs, action, voiceover_line,
              camera_angle, lighting, setting, audio_cue}], music_recommendation,
              caption, hashtags}
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
from src.data.pillars import pillar_label

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"


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
{visual_world_block}
Task: Create a brand-new {content_format} script inspired by what made the reference \
post successful. Apply the brand voice above.

Hashtag rules live in the per-format instructions below — a global rule here would
contradict Story, which has no hashtags and no caption at all.

{format_instructions}

Return ONLY valid JSON — no preamble, no markdown fences:
{json_schema}
"""

# The only stickers Instagram actually offers. Granite will invent plausible-sounding
# ones ("swipe-up", "emoji slider bar") if left unconstrained, and a sticker the
# creator can't place is worse than no sticker — so the set is both stated in the
# prompt and enforced on the way out.
_STORY_STICKERS = {"poll", "question", "quiz", "slider", "countdown", "link", "none"}

_FORMAT_INSTRUCTIONS = {
    "Reel": (
        "Structure the Reel script as a clip-by-clip shot list, ready for someone to film without any further planning:\n"
        "  • hook_options: an array of EXACTLY 3 different opening lines (each max 8 words, punchy). "
        "Make them genuinely different approaches — e.g. one problem-first, one result-first, one "
        "curiosity-first — not three rewordings of the same line. Do NOT start any of them with "
        "'Stop scrolling'.\n"
        "  • cover_text: the 2-5 word text for the Reel's cover image (what shows on the profile grid)\n"
        "  • clips: an array of 5-6 clips, each with:\n"
        "      - clip_number: sequential integer starting at 1\n"
        "      - duration_secs: approximate on-screen duration for this clip (e.g. '0-3', '3-6')\n"
        "      - action: what's happening on screen, described concretely (e.g. 'Nutella scooped into dough, then sealed by hand')\n"
        "      - voiceover_line: the exact spoken line or on-screen text for this clip (conversational, one short sentence)\n"
        "      - camera_angle: the specific shot type (e.g. 'macro top-down close-up', 'low-angle on the frying pan')\n"
        "      - lighting: the lighting mood and source (e.g. 'warm golden-hour light through the kitchen window')\n"
        "      - setting: the background/location detail — ground this in a real home-kitchen bakery, not a generic studio\n"
        "      - audio_cue: an SFX or sound-design note for this clip (e.g. 'sizzle of frying', 'sugar being dusted')\n"
        "  • music_recommendation: one sentence naming an overall track mood/genre/BPM for the whole Reel (e.g. 'warm lo-fi acoustic, 90-100 BPM')\n"
        "  • caption: Instagram caption for the Reel (under 150 words)\n"
        "  • hashtags: list of exactly 5 hashtag strings (with #)\n"
        "Ground every camera/lighting/setting choice in the brand's visual world described below."
    ),
    "Carousel": (
        "Structure the Carousel with 5-6 slides:\n"
        "  • hook: the cover slide headline (max 8 words)\n"
        "  • slides: array of {slide (number), headline (short), body (1-2 sentences), "
        "visual (what to actually photograph or lay out on THIS slide — be concrete, "
        "e.g. 'overhead shot of cold butter cubes beside a warm bowl', not 'a nice image')}\n"
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
    "Story": (
        "Structure a Story sequence of 4 frames. Stories are the daily surface between "
        "polished feed posts — they should feel spontaneous and be filmable on a phone in "
        "one pass, not staged:\n"
        "  • hook: the first frame's on-screen text (max 8 words)\n"
        # An exact count, not a "3-5" range: Granite returned 2 frames on every run
        # when given the range, and models hold to a single number far better.
        "  • frames: an array of EXACTLY 4 frames, each with:\n"
        "      - frame: sequential integer starting at 1\n"
        "      - visual: what's on screen, shootable in a single take\n"
        "      - on_screen_text: the exact text overlay (max 12 words — it competes with the visual)\n"
        f"      - sticker: EXACTLY one of {' | '.join(sorted(_STORY_STICKERS))}\n"
        "      - sticker_prompt: the sticker's wording, or \"\" when sticker is \"none\"\n"
        "      - duration_secs: an integer from 3 to 15\n"
        "  • closing_cta: the last frame's ask, tied to what she wants them to do next\n"
        "At most 2 frames may carry a sticker — a sticker on every frame reads as a survey, "
        "not a story.\n"
        "Instagram Stories have NO caption and NO hashtags. Do NOT write a caption, do NOT "
        "write hashtags, and do NOT return prose — return only the JSON object below."
    ),
}

_JSON_SCHEMAS = {
    "Reel": (
        '{\n'
        '  "hook_options": ["<max 8 words>", "<a different angle>", "<a third angle>"],\n'
        '  "cover_text": "<2-5 words for the cover image>",\n'
        '  "clips": [\n'
        '    {"clip_number": 1, "duration_secs": "<e.g. 0-3>", "action": "<what happens on screen>", "voiceover_line": "<one short spoken line>", "camera_angle": "<shot type>", "lighting": "<lighting mood/source>", "setting": "<background/location detail>", "audio_cue": "<SFX or sound-design note>"},\n'
        '    {"clip_number": 2, "duration_secs": "<e.g. 3-6>", "action": "...", "voiceover_line": "...", "camera_angle": "...", "lighting": "...", "setting": "...", "audio_cue": "..."}\n'
        '  ],\n'
        '  "music_recommendation": "<overall track mood/genre/BPM in one sentence>",\n'
        '  "caption": "<Instagram caption>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}'
    ),
    "Carousel": (
        '{\n'
        '  "hook": "<cover slide headline>",\n'
        '  "slides": [\n'
        '    {"slide": 1, "headline": "<short>", "body": "<1-2 sentences>", "visual": "<what to shoot or lay out>"},\n'
        '    {"slide": 2, "headline": "<short>", "body": "<1-2 sentences>", "visual": "<what to shoot or lay out>"}\n'
        '  ],\n'
        '  "cta_slide": "<final call to action>",\n'
        '  "caption": "<Instagram caption>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}'
    ),
    "Static": (
        '{\n'
        '  "headline": "<overlay text, max 8 words>",\n'
        '  "caption": "<Instagram caption>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],\n'
        '  "visual_direction": "<one sentence on image composition and mood>",\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}'
    ),
    "Story": (
        '{\n'
        '  "hook": "<max 8 words>",\n'
        '  "frames": [\n'
        '    {"frame": 1, "visual": "<what is on screen>", "on_screen_text": "<max 12 words>", "sticker": "none", "sticker_prompt": "", "duration_secs": 5},\n'
        '    {"frame": 2, "visual": "...", "on_screen_text": "...", "sticker": "poll", "sticker_prompt": "<the poll wording>", "duration_secs": 5}\n'
        '  ],\n'
        '  "closing_cta": "<the last frame\'s ask>",\n'
        '  "reasoning": "<1-2 sentences on what you borrowed from the reference post>"\n'
        '}'
    ),
}

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "reference_caption", "metrics_summary", "cluster_label",
        "tone_descriptors", "recurring_words", "signature_phrases", "avoided_terms",
        "visual_world_block", "content_format", "format_instructions", "json_schema",
    ],
    template=_TEMPLATE,
)


def _parse_script(raw: str) -> dict:
    """
    Parse Granite's script JSON, repairing the two defects an 8B model actually
    produces here.

    This used to be a bare `json.loads`, so any imperfection dropped the whole
    script and the caller fell back to dumping raw prose into `caption` — the
    creator asked for a Reel and got a paragraph. Both repairs below are reused
    from modules that already needed them; neither is new logic.
    """
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

    # 1. Doubled braces. The schema examples were once double-braced (a stale
    #    PromptTemplate escape) and Granite still mirrors that shape sometimes.
    collapsed = text.replace("{{", "{").replace("}}", "}")
    try:
        return json.loads(collapsed)
    except json.JSONDecodeError:
        pass

    # 2. Truncation at the num_predict ceiling — long Reel shot lists hit it.
    from src.embeddings.profile_extractor import _repair_truncated_json
    return json.loads(_repair_truncated_json(collapsed))


def build_filming_checklist(clips: list, music: str = "") -> list[str]:
    """
    A before-you-start checklist, derived from the shot list rather than generated.

    Every clip already names its camera angle, lighting, setting and audio cue, so
    the checklist is a fold over data we have. Asking Granite for it again would add
    tokens to the slowest call in the app (the Reel script), risk truncation, and
    invite it to list gear the shot list never mentions.

    Deduplicated while preserving first-appearance order, so it reads in shooting
    order rather than alphabetically.
    """
    def collect(field: str) -> list[str]:
        seen: dict[str, None] = {}
        for c in clips or []:
            if isinstance(c, dict):
                v = str(c.get(field) or "").strip()
                if v:
                    seen.setdefault(v, None)
        return list(seen)

    # Caps, because dedup is exact-match and Granite rephrases the same physical
    # setup per clip ("Warm, diffused kitchen lighting" vs "Soft, diffused kitchen
    # lighting"). Uncapped this ran to 17 lines, which is longer than the shot list
    # it summarises and so gets skipped. Shots are uncapped — those genuinely differ
    # per clip and are the part worth checking off.
    items: list[str] = []
    for setting in collect("setting")[:3]:
        items.append(f"Set up: {setting}")
    for light in collect("lighting")[:2]:
        items.append(f"Lighting: {light}")
    for angle in collect("camera_angle"):
        items.append(f"Shot: {angle}")
    audio = collect("audio_cue")
    if audio:
        items.append("Record sound for: " + ", ".join(audio[:4]))
    if music:
        items.append(f"Music: {music}")
    return items


def _normalize_reel(result: dict) -> None:
    """
    Back-compat and derived fields for Reels. Mutates in place.

    `hook` is kept as the first of `hook_options` because saved Workbench assets,
    the repurpose fan-out and api/routers/create.py's caption regeneration all read
    `script["hook"]`. Dropping it would break each of them silently.
    """
    options = result.get("hook_options")
    if isinstance(options, list):
        options = [str(o).strip() for o in options if str(o or "").strip()]
    else:
        options = []
    # Granite occasionally returns `hook` instead of `hook_options`.
    if not options and result.get("hook"):
        options = [str(result["hook"]).strip()]
    result["hook_options"] = options
    if options:
        result["hook"] = options[0]

    result["filming_checklist"] = build_filming_checklist(
        result.get("clips") or [],
        str(result.get("music_recommendation") or ""),
    )


def _normalize_story(result: dict) -> None:
    """
    Enforce the Story contract Granite is asked for but can't be trusted to keep.
    Mutates in place.

    An 8B model reliably invents sticker types that don't exist on Instagram, and
    occasionally attaches a `sticker_prompt` to a frame whose sticker is "none".
    Both would send the creator looking for a control that isn't there.

    It also keeps emitting `caption`/`hashtags` for Stories however firmly the prompt
    says not to — Stories have neither, and a caption field on a Story card would just
    be wrong. Drop them here instead of trusting the instruction to hold.
    """
    result.pop("caption", None)
    result.pop("hashtags", None)

    frames = result.get("frames")
    if not isinstance(frames, list):
        result["frames"] = []
        return

    clean: list[dict] = []
    for i, f in enumerate(frames, start=1):
        if not isinstance(f, dict):
            continue
        sticker = str(f.get("sticker", "none")).strip().lower()
        if sticker not in _STORY_STICKERS:
            sticker = "none"
        f["sticker"] = sticker
        f["sticker_prompt"] = "" if sticker == "none" else str(f.get("sticker_prompt", "") or "")
        f["frame"] = i                      # renumber; Granite skips and repeats indices
        clean.append(f)
    result["frames"] = clean


class ScriptGenerator:
    """
    Generates structured content scripts (Reel/Carousel/Static) inspired by a
    high-performing reference post, applying the brand's cluster voice.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        # 1800, up from 1400: the Reel schema now also asks for 3 hook options and
        # cover text. The filming checklist is computed in Python precisely so this
        # ceiling didn't have to rise further — it's the slowest call in the app.
        self._llm   = OllamaLLM(model=model, temperature=0.5, num_predict=1800)
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

        if fmt == "Reel":
            visual_world_block = (
                f"\nVisual world for this Reel (ground every camera/lighting/setting choice here — "
                f"this is a {p.get('content_pillar', 'product_showcase')} post from a home-kitchen bakery, not a professional studio):\n"
                f"  Structural pattern : {p.get('structural_signature', '')}\n"
                f"  Example post       : {p.get('representative_post', '')}\n"
                f"  Brand in one line  : {self._profile.get('brand_bio', '')}\n"
            )
        else:
            visual_world_block = ""

        raw = self._chain.invoke({
            "brand_name"         : self._profile["brand_name"],
            "reference_caption"  : reference_caption,
            "metrics_summary"    : metrics_summary,
            "cluster_label"      : pillar_label(cluster_id),
            "tone_descriptors"   : ", ".join(p.get("tone_descriptors", [])),
            "recurring_words"    : ", ".join(voc.get("recurring_words", [])),
            "signature_phrases"  : ", ".join(voc.get("signature_phrases", [])),
            "avoided_terms"      : ", ".join(p.get("avoided_terms", [])),
            "visual_world_block" : visual_world_block,
            "content_format"     : fmt,
            "format_instructions": _FORMAT_INSTRUCTIONS[fmt],
            "json_schema"        : _JSON_SCHEMAS[fmt],
        })

        try:
            result = _parse_script(raw)
            result["format"] = fmt
            if fmt == "Story":
                _normalize_story(result)
            elif fmt == "Reel":
                _normalize_reel(result)
            return result
        except (json.JSONDecodeError, ValueError):
            # Flag the failure instead of passing raw prose off as a caption. The
            # old shape put `raw` in `caption`, so a failed Story render as a
            # plausible-looking paragraph — the creator couldn't tell it had failed.
            return {
                "format"      : fmt,
                "parse_failed": True,
                "raw_response": raw.strip(),
                "reasoning"   : f"Granite did not return valid {fmt} JSON. Try generating again.",
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
