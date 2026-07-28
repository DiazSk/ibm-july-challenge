"""
Confidence Scorer — Granite invocation #15 (preserved) + deterministic signal gate (new).

WHAT CHANGED AND WHY:
The old scorer asked Granite to rate its own output 0-100 with a single rationale
sentence. That made the convergence loop exit on "sounds good to an LLM" rather than
on real behavioral criteria. The new scorer runs a deterministic signal rubric FIRST
(hook strength, DM-share potential, save potential, comment bait, niche keyword density)
and only calls Granite to produce a human-readable rationale sentence AFTER the gate
runs. The orchestrator's _quick_score now gets a number grounded in Instagram signal
logic, not LLM self-approval.

Output contract (unchanged — orchestrator reads .get("score", 50)):
{
    "score": int 0-100,
    "rationale": str,
    "gate_passed": bool,
    "breakdown": {
        "hook_strength":      int 0-25,
        "dm_share_potential": int 0-25,
        "save_potential":     int 0-20,
        "comment_bait":       int 0-15,
        "keyword_clarity":    int 0-15,
    },
    "failures": list[str],   # specific rejection reasons, empty if approved
    "hook_pattern": str,     # detected hook type, used to tag episodic memory
}

Run standalone:
    python src/generation/confidence_scorer.py
"""

from __future__ import annotations

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "granite3.1-dense:8b"

# ---------------------------------------------------------------------------
# Signal pattern libraries
# These are the behavioral patterns that correlate with Instagram distribution
# signals (watch-through, DM shares, saves, comments) based on how the
# platform's cascade ranking model actually works.
# ---------------------------------------------------------------------------

# Hook patterns that create pattern interrupts — each triggers a recognition
# response in the viewer that delays swipe. Named so they can be stored in
# episodic memory and correlated with performance later.
_HOOK_PATTERNS: list[tuple[str, str]] = [
    ("number_led",        r"^\d+\s+\w"),
    ("negative_hook",     r"\b(stop|never|worst|mistake|wrong|don't|avoid)\b"),
    ("result_first",      r"\b(how i|this got|watch me|i turned|i made)\b"),
    ("pov_format",        r"\bpov\b"),
    ("unpopular_opinion", r"\bunpopular opinion\b"),
    ("question_hook",     r"\?"),
    ("exclusivity",       r"\b(nobody talks about|secret|they don't want|hidden)\b"),
    ("controversy",       r"\b(hot take|controversial|will get hate)\b"),
    ("curiosity_gap",     r"\b(why your|reason your|this is why)\b"),
]

# Weak openers — hard penalty because these guarantee the algorithm never
# gets a meaningful watch signal (viewer swipes before 1.5s)
_WEAK_OPENERS: list[str] = [
    "hello", "hi guys", "hi everyone", "hey guys", "welcome back",
    "today i'm going to", "today i am going to", "in this video",
    "in this post", "so today", "i wanted to share", "just wanted to",
    "i'm so excited", "i am so excited", "greetings",
]

# DM share triggers — the single most powerful reach signal for Reels.
# When a viewer DMs a reel, it reaches a brand-new account. Weighted highest.
_DM_SHARE_TRIGGERS: list[str] = [
    "send this to", "tag someone", "show this to", "your friend who",
    "every baker", "anyone who bakes", "send to a friend", "share with",
    "who needs to see this", "forward this", "tag a baker",
]

# Save triggers — signals lasting utility; heavily weighted for educational
# and tutorial content. High save rate → algorithm marks as evergreen.
_SAVE_TRIGGERS: list[str] = [
    "save this", "screenshot this", "bookmark", "step by step",
    "how to", "tutorial", "recipe", "technique", "formula",
    "checklist", "next time you", "remember this", "guide",
    "full recipe", "exact method", "save for later", "keep this",
]

# Comment triggers — early comment velocity in the first 30 minutes
# strongly influences distribution. Specific triggers outperform generic CTAs.
_COMMENT_TRIGGERS: list[str] = [
    "comment", "let me know", "tell me", "which one", "have you tried",
    "drop a", "reply with", "what's your", "do you agree",
    "would you", "vote below", "yes or no", "hot take below",
]

# Niche keyword set for bakery content — Instagram's topic classifier needs
# these to route content to the right interest graph. More hits = clearer signal.
_BAKERY_KEYWORDS: list[str] = [
    "flour", "dough", "bake", "baked", "baking", "oven", "proof", "proofing",
    "knead", "kneading", "laminate", "lamination", "crumb", "crumb structure",
    "ganache", "glaze", "frosting", "buttercream", "yeast", "sourdough",
    "starter", "croissant", "cake", "cookie", "bread", "pastry", "bomboloni",
    "muffin", "brownie", "tart", "custard", "cream", "whip", "meringue",
    "crust", "filling", "chocolate", "vanilla", "cinnamon", "nutella",
    "rasmalai", "kunafa", "pudding", "artisan", "homemade", "from scratch",
    "bakery", "baker", "bakers",
]

# ---------------------------------------------------------------------------
# Deterministic signal scorer
# ---------------------------------------------------------------------------

def _detect_hook_pattern(hook: str) -> str:
    """Return the name of the first matching hook pattern, or 'no_pattern'."""
    h = hook.lower()
    for name, regex in _HOOK_PATTERNS:
        if re.search(regex, h, re.IGNORECASE):
            return name
    return "no_pattern"


# Soft signals — a tasteful artisan brand earns credit for good writing, not
# growth-hack CTA spam. Calibrated so a strong on-brand caption lands ~68-85, a
# decent one ~55-65, and a flat/generic one ~25-45 — realistic, not inflated.
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|yours)\b", re.IGNORECASE)
_SOFT_SHARE_RE = re.compile(r"\b(share|send|tag|dm|forward|tell a friend|show (this|someone))\b", re.IGNORECASE)
_SOFT_SAVE_RE = re.compile(r"\b(how to|why|tip|tips|recipe|step|steps|guide|method|\d+\s+(reasons|ways|things|tips))\b", re.IGNORECASE)
_QUESTION_RE = re.compile(r"\?")
_EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿]")
# Sensory / vivid opener words — for a warm artisan brand these ARE a strong hook,
# not just gimmicky "pattern interrupts".
_SENSORY = [
    "soft", "fluffy", "gooey", "rich", "warm", "crispy", "crunchy", "golden",
    "melty", "melt", "fresh", "buttery", "creamy", "decadent", "velvety", "tender",
    "moist", "flaky", "silky", "luscious", "oozing", "dreamy", "indulgent",
]


def _score_hook(hook: str) -> tuple[int, str, list[str]]:
    """
    Score hook strength 0-30. Base credit for any real opener, plus bonuses for a
    pattern interrupt (number-led, POV, question…) OR a vivid sensory opener —
    both are strong hooks for this brand. Returns (score, pattern_name, failures).
    """
    h = hook.lower().strip()

    for weak in _WEAK_OPENERS:
        if h.startswith(weak):
            return (
                8,
                "dead_opener",
                [
                    f"DEAD_HOOK: starts with '{weak}' — viewer swipes before the algorithm "
                    f"gets a watch signal. Open with a vivid detail, a number, or a question instead."
                ],
            )

    score = 16
    pattern_name = "no_pattern"
    for name, regex in _HOOK_PATTERNS:
        if re.search(regex, h, re.IGNORECASE):
            score = min(30, score + 7)
            if pattern_name == "no_pattern":
                pattern_name = name
    if any(w in h for w in _SENSORY):
        score = min(30, score + 7)
        if pattern_name == "no_pattern":
            pattern_name = "sensory_opener"

    return score, pattern_name, []


def score_content(
    hook: str,
    caption: str,
    content_format: str = "reel",
) -> dict:
    """
    Deterministic signal scorer. Rewards what a genuinely good, on-brand caption
    has — a strong hook (pattern interrupt OR vivid sensory opener), engagement
    cues (a question, second-person, a gentle share/save nudge), niche vocabulary,
    and clean craft — instead of hard-failing tasteful captions that skip
    growth-hack CTAs. Realistic: strong ~68-85, decent ~55-65, flat ~25-45.

    `hook` is the first sentence; `content_format` is reel|carousel|story|static.
    """
    text = (hook + " " + caption).lower()
    failures: list[str] = []

    # --- Hook (0-30) ---
    hook_score, hook_pattern, hook_failures = _score_hook(hook)
    failures.extend(hook_failures)

    # --- Engagement (0-30): a question, second-person, and soft/explicit nudges ---
    engagement = 0
    if _QUESTION_RE.search(caption):
        engagement += 10
    if _SECOND_PERSON_RE.search(text):
        engagement += 6
    if _SOFT_SHARE_RE.search(text) or _SOFT_SAVE_RE.search(text):
        engagement += 6
    engagement += sum(8 for t in (_DM_SHARE_TRIGGERS + _SAVE_TRIGGERS + _COMMENT_TRIGGERS) if t in text)
    engagement = min(30, engagement)
    if engagement < 6:
        failures.append(
            "LOW_ENGAGEMENT: nothing invites a reply, save, or share. A light question or "
            "a gentle 'save this for your next craving' would lift reach — keep it on-brand."
        )

    # --- Niche clarity (0-20) ---
    keyword_hits = [t for t in _BAKERY_KEYWORDS if t in text]
    niche_score = min(20, len(keyword_hits) * 4)
    if niche_score < 8:
        failures.append(
            f"LOW_NICHE_SIGNAL: only {len(keyword_hits)} bakery keyword(s). Weave in 2-3 "
            f"specific terms (dough, crumb, proof, ganache) so the topic classifier routes it right."
        )

    # --- Craft (0-20): coherent length, emoji warmth, clean close ---
    words = len(caption.split())
    craft = 10 if 12 <= words <= 160 else (5 if words else 0)
    if _EMOJI_RE.search(caption):
        craft += 5
    if caption.strip().endswith((".", "!", "?", "🙂")) or _QUESTION_RE.search(caption):
        craft += 5
    craft = min(20, craft)

    total = hook_score + engagement + niche_score + craft
    gate_passed = total >= 55 and hook_pattern != "dead_opener"

    return {
        "score": total,
        "gate_passed": gate_passed,
        "hook_pattern": hook_pattern,
        "breakdown": {
            "hook_strength": hook_score,
            "engagement":    engagement,
            "niche_clarity": niche_score,
            "craft":         craft,
        },
        "failures": failures,
        "rationale": (
            "; ".join(failures)
            if failures
            else f"Distribution-ready — hook: {hook_pattern}, score: {total}/100."
        ),
    }


# ---------------------------------------------------------------------------
# ConfidenceScorer class — drop-in replacement
# Preserves the .score(context_summary, output_summary) interface so
# analytics_agent.py and any other callers continue to work unchanged.
# The Granite call is now used ONLY to generate a one-sentence narrative
# rationale for the UI — NOT to set the numeric score.
# ---------------------------------------------------------------------------

_RATIONALE_TEMPLATE = """\
You are a one-sentence copywriter. A caption was scored against Instagram \
signal criteria. Here is what the scorer found:

Score: {score}/100
Gate passed: {gate_passed}
Hook pattern: {hook_pattern}
Issues detected:
{failures_block}

Write ONE sentence (max 25 words) that tells the creator the most important \
thing to fix, or confirms the caption is distribution-ready. Be direct. \
No preamble. Return plain text only, no JSON.
"""

_RATIONALE_PROMPT = PromptTemplate(
    input_variables=["score", "gate_passed", "hook_pattern", "failures_block"],
    template=_RATIONALE_TEMPLATE,
)


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"(\s*):', r'",\1"\2"\3:', text)


def _parse_json(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_repair_missing_commas(text))
    except json.JSONDecodeError:
        return {}


class ConfidenceScorer:
    """
    Drop-in replacement. Public interface identical to the original.
    score() now returns deterministic signal data + a Granite rationale sentence.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.2, num_predict=60)
        self._chain = _RATIONALE_PROMPT | self._llm

    def score(self, context_summary: str, output_summary: str) -> dict:
        """
        context_summary: e.g. "Caption for cluster 1"
        output_summary:  the caption text to evaluate

        Extracts the hook (first sentence) from output_summary automatically.
        Returns the full signal breakdown dict with "score" key for orchestrator.
        """
        caption = output_summary.strip()
        # Extract hook: first sentence ending in . ! or ? or first 12 words
        hook_match = re.match(r"^([^.!?]{10,120}[.!?])", caption)
        hook = hook_match.group(1).strip() if hook_match else " ".join(caption.split()[:12])

        # Detect format hint from context_summary
        fmt = "reel"
        ctx_lower = context_summary.lower()
        if "carousel" in ctx_lower:
            fmt = "carousel"
        elif "story" in ctx_lower:
            fmt = "story"
        elif "static" in ctx_lower:
            fmt = "static"

        # Run deterministic scoring
        result = score_content(hook=hook, caption=caption, content_format=fmt)

        # Granite generates the rationale sentence — does NOT set the score
        failures_block = (
            "\n".join(f"- {f}" for f in result["failures"])
            if result["failures"]
            else "- None. All gates passed."
        )
        try:
            granite_rationale = self._chain.invoke({
                "score":          result["score"],
                "gate_passed":    result["gate_passed"],
                "hook_pattern":   result["hook_pattern"],
                "failures_block": failures_block,
            }).strip()
        except Exception:
            granite_rationale = result["rationale"]

        result["rationale"] = granite_rationale
        return result


# ---------------------------------------------------------------------------
# Standalone runner — python src/generation/confidence_scorer.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scorer = ConfidenceScorer()

    tests = [
        {
            "caption": "Stop cold-proofing your croissants before reading this. "
                       "Your layers are dying in the fridge and nobody talks about why. "
                       "Save this — I'll show you the exact temp and timing that "
                       "changed my lamination. Tag a baker who needs to see this.",
            "label": "SHOULD PASS",
        },
        {
            "caption": "Hi guys! Welcome back to my page. Today I'm going to share "
                       "a really amazing recipe that I think you're all going to love. "
                       "It's so delicious and I'm so excited to show you. Don't forget "
                       "to follow for more amazing content!",
            "label": "SHOULD FAIL",
        },
    ]

    for t in tests:
        cap = t["caption"]
        hook_match = __import__("re").match(r"^([^.!?]{10,120}[.!?])", cap)
        hook = hook_match.group(1) if hook_match else " ".join(cap.split()[:12])
        res = score_content(hook=hook, caption=cap, content_format="reel")
        print(f"\n[{t['label']}]")
        print(f"  Score      : {res['score']}/100")
        print(f"  Gate passed: {res['gate_passed']}")
        print(f"  Hook pattern: {res['hook_pattern']}")
        print(f"  Breakdown  : {res['breakdown']}")
        if res["failures"]:
            for f in res["failures"]:
                print(f"  FAIL: {f}")
