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


def _score_hook(hook: str) -> tuple[int, str, list[str]]:
    """
    Score hook strength 0-25. Returns (score, pattern_name, failures).
    A hook is the first sentence/line of the caption — the distribution gate.
    If the viewer swipes before 1.5s the algorithm never gets a watch signal.
    """
    h = hook.lower().strip()
    failures: list[str] = []

    # Check for dead openers first — hard override
    for weak in _WEAK_OPENERS:
        if h.startswith(weak):
            return (
                0,
                "dead_opener",
                [
                    f"DEAD_HOOK: starts with '{weak}' — viewer swipes before algorithm "
                    f"gets a watch signal. Rewrite as number-led, result-first, or POV."
                ],
            )

    # Score pattern matches (up to 25)
    score = 0
    pattern_name = "no_pattern"
    for name, regex in _HOOK_PATTERNS:
        if re.search(regex, h, re.IGNORECASE):
            score = min(25, score + 6)
            if pattern_name == "no_pattern":
                pattern_name = name  # capture first (strongest) match

    if score < 10:
        failures.append(
            f"WEAK_HOOK: {score}/25 — no recognisable pattern interrupt in the first line. "
            f"Use one of: number-led ('3 reasons...'), result-first ('How I got...'), "
            f"POV, question, or exclusivity ('Nobody talks about...')."
        )

    return score, pattern_name, failures


def score_content(
    hook: str,
    caption: str,
    content_format: str = "reel",
) -> dict:
    """
    Deterministic signal scorer. Returns the full breakdown dict.
    `hook` should be the first sentence of the caption.
    `content_format` is 'reel' | 'carousel' | 'story' | 'static'.
    """
    text = (hook + " " + caption).lower()
    failures: list[str] = []

    # --- Hook (0-25) ---
    hook_score, hook_pattern, hook_failures = _score_hook(hook)
    failures.extend(hook_failures)

    # --- DM share potential (0-25) ---
    share_score = min(25, sum(6 for t in _DM_SHARE_TRIGGERS if t in text))
    if share_score == 0 and content_format in ("reel", "carousel"):
        failures.append(
            "NO_SHARE_TRIGGER: nothing makes this DM-able. Shares are the #1 reach "
            "multiplier for Reels — a viewer DMing to a friend reaches a new account entirely. "
            "Add one: 'Send this to someone who...' or 'Tag a baker who...'."
        )

    # --- Save potential (0-20) ---
    save_score = min(20, sum(4 for t in _SAVE_TRIGGERS if t in text))
    if save_score == 0 and content_format in ("reel", "carousel"):
        failures.append(
            "NO_SAVE_TRIGGER: no reason to bookmark. Saves signal lasting utility — "
            "high save rate tells the algorithm the content is evergreen. "
            "Add 'Save this for next time' or embed a step-by-step structure."
        )

    # --- Comment bait (0-15) ---
    comment_score = min(15, sum(4 for t in _COMMENT_TRIGGERS if t in text))
    # No failure for zero comment triggers — it's nice-to-have, not critical

    # --- Keyword clarity (0-15) ---
    keyword_hits = [t for t in _BAKERY_KEYWORDS if t in text]
    keyword_score = min(15, len(keyword_hits) * 2)
    if keyword_score < 6:
        failures.append(
            f"LOW_NICHE_SIGNAL: only {len(keyword_hits)} bakery keyword(s) detected. "
            f"Instagram's topic classifier needs ≥3 niche terms to route content to the "
            f"right interest graph. Add specific bakery terms (e.g. dough, crumb, proof, ganache)."
        )

    total = hook_score + share_score + save_score + comment_score + keyword_score

    # Gate: must clear 60/100 AND have no critical failures (dead hook or no share trigger on reels)
    critical = [f for f in failures if f.startswith(("DEAD_HOOK", "NO_SHARE_TRIGGER"))]
    gate_passed = total >= 60 and len(critical) == 0

    return {
        "score": total,
        "gate_passed": gate_passed,
        "hook_pattern": hook_pattern,
        "breakdown": {
            "hook_strength":      hook_score,
            "dm_share_potential": share_score,
            "save_potential":     save_score,
            "comment_bait":       comment_score,
            "keyword_clarity":    keyword_score,
        },
        "failures": failures,
        "rationale": (
            "; ".join(failures)
            if failures
            else f"All signal gates passed — hook pattern: {hook_pattern}, score: {total}/100."
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
