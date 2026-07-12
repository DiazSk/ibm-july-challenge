"""
Brand Guardian — Granite invocation #18.

An adversarial critique-then-refine loop for ONE already-generated caption
(not a from-scratch drafter). A harsh in-character reviewer flags generic,
"obviously-AI" language, avoided-term slips, and tone/signature-phrase
mismatches; a separate refine call rewrites the caption to address exactly
those issues.

Hard-capped at 2 rounds by the caller (api/routers/create.py) — small local
models don't reliably converge in iterative critique loops, so this module
only exposes the two single-purpose calls (critique, refine) and leaves the
round-cap / best-so-far selection logic to the router, matching this
codebase's convention of keeping multi-call orchestration out of generator
classes.

Input:  caption: str, cluster_id: int
Output: critique() -> {verdict, issues, severity, reasoning}
        refine()   -> {refined_caption, what_changed}

Run standalone:
    python src/generation/brand_guardian.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"

_CRITIQUE_TEMPLATE = """\
You are an adversarial brand-voice reviewer for {brand_name}, a homemade \
artisanal bakery on Instagram. Your job is to be harsh and specific, not \
agreeable — most captions you see should need work.

Brand voice profile for this content pillar:
  Tone              : {tone_descriptors}
  Signature phrases : {signature_phrases}
  Structural pattern: {structural_signature}
  Avoided terms     : {avoided_terms}

Caption under review:
"{caption}"

Critique this caption harshly. Specifically check for:
- Generic, "obviously-AI," or marketing-template language a real person wouldn't write
- Any avoided terms appearing anywhere in the caption
- Missing or mismatched signature phrases / tone
- Weak or absent hook in the first sentence

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "verdict": "approve" or "needs_revision",
  "issues": ["<specific issue 1>", "<specific issue 2>"],
  "severity": "none" or "minor" or "major",
  "reasoning": "<1-2 sentences justifying the verdict>"
}}
"""

_REFINE_TEMPLATE = """\
You are a brand copywriter for {brand_name}, a homemade artisanal bakery on \
Instagram, revising a caption based on a reviewer's critique.

Brand voice profile for this content pillar:
  Tone              : {tone_descriptors}
  Signature phrases : {signature_phrases}
  Structural pattern: {structural_signature}
  Avoided terms     : {avoided_terms}

Original caption:
"{caption}"

Reviewer's issues to fix:
{issues_block}

Rewrite the caption to address every issue above, while keeping it on-brand, \
under 150 words, and sounding like a real person. Do not introduce any \
avoided terms.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "refined_caption": "<the rewritten caption>",
  "what_changed": "<1 sentence: what you changed and why>"
}}
"""

_CRITIQUE_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "tone_descriptors", "signature_phrases",
        "structural_signature", "avoided_terms", "caption",
    ],
    template=_CRITIQUE_TEMPLATE,
)
_REFINE_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "tone_descriptors", "signature_phrases",
        "structural_signature", "avoided_terms", "caption", "issues_block",
    ],
    template=_REFINE_TEMPLATE,
)

_VALID_VERDICTS = {"approve", "needs_revision"}
_VALID_SEVERITIES = {"none", "minor", "major"}


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return json.loads(_repair_missing_commas(text))


class BrandGuardian:
    """
    Critiques and refines a single caption against the brand voice profile.
    Never raises — both methods fall back to a safe, clearly-labeled result
    if Granite's output can't be parsed.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._critique_llm = OllamaLLM(model=model, temperature=0.2, num_predict=350)
        self._refine_llm = OllamaLLM(model=model, temperature=0.6, num_predict=350)
        self._critique_chain = _CRITIQUE_PROMPT | self._critique_llm
        self._refine_chain = _REFINE_PROMPT | self._refine_llm
        self._profile: dict = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    def _cluster_voice(self, cluster_id: int) -> dict:
        cluster = next(
            (c for c in self._profile["cluster_profiles"] if c["cluster_id"] == cluster_id),
            self._profile["cluster_profiles"][0],
        )
        p = cluster["profile"]
        voc = p.get("vocabulary_patterns", {})
        return {
            "brand_name": self._profile["brand_name"],
            "tone_descriptors": ", ".join(p.get("tone_descriptors", [])),
            "signature_phrases": ", ".join(voc.get("signature_phrases", [])),
            "structural_signature": p.get("structural_signature", ""),
            "avoided_terms": ", ".join(p.get("avoided_terms", [])),
        }

    def critique(self, caption: str, cluster_id: int = 0) -> dict:
        """
        Granite Call #18.
        Returns {verdict, issues, severity, reasoning}.
        """
        voice = self._cluster_voice(cluster_id)
        raw = self._critique_chain.invoke({**voice, "caption": caption})

        try:
            result = _parse_json(raw)
            verdict = result.get("verdict", "needs_revision")
            result["verdict"] = verdict if verdict in _VALID_VERDICTS else "needs_revision"
            severity = result.get("severity", "minor")
            result["severity"] = severity if severity in _VALID_SEVERITIES else "minor"
            issues = result.get("issues") or []
            result["issues"] = [str(i) for i in issues][:6]
            result["reasoning"] = str(result.get("reasoning", ""))
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            return {
                "verdict": "needs_revision",
                "issues": ["Could not parse the reviewer's critique."],
                "severity": "minor",
                "reasoning": "Granite's response could not be parsed.",
            }

    def refine(self, caption: str, critique: dict, cluster_id: int = 0) -> dict:
        """
        Granite Call #18 (refine pass).
        Returns {refined_caption, what_changed}.
        """
        voice = self._cluster_voice(cluster_id)
        issues = critique.get("issues") or ["Make it more on-brand and less generic."]
        issues_block = "\n".join(f"- {i}" for i in issues)
        raw = self._refine_chain.invoke({**voice, "caption": caption, "issues_block": issues_block})

        try:
            result = _parse_json(raw)
            refined = str(result.get("refined_caption", "")).strip()
            if not refined:
                raise ValueError("empty refined_caption")
            result["refined_caption"] = refined
            result["what_changed"] = str(result.get("what_changed", ""))
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            return {
                "refined_caption": caption,
                "what_changed": "Could not parse the refinement — kept original.",
            }


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    guardian = BrandGuardian()

    generic_caption = "Check out our amazing new product! Buy now and enjoy the best treats in town!"
    print("-- Critiquing a generic caption --")
    c1 = guardian.critique(generic_caption, cluster_id=3)
    print(json.dumps(c1, indent=2))

    if c1["verdict"] == "needs_revision":
        print("\n-- Refining it --")
        r1 = guardian.refine(generic_caption, c1, cluster_id=3)
        print(json.dumps(r1, indent=2))

        print("\n-- Re-critiquing the refined version --")
        c2 = guardian.critique(r1["refined_caption"], cluster_id=3)
        print(json.dumps(c2, indent=2))
