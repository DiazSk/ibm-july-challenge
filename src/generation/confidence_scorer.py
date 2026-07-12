"""
Confidence Scorer — Granite invocation #15.

Given a short summary of the input context and the output an earlier Granite
call produced, scores how confident that output actually is and why — a
lightweight self-critique pass surfaced to the user as a visible badge rather
than a silent, uniformly-confident-sounding result.

Input:  context_summary string, output_summary string
Output: {score, rationale} dict — score is 0-100, framed as a directional
        signal (not a scientifically calibrated prediction — small local
        models are not well-calibrated numeric self-assessors).

Run standalone:
    python src/generation/confidence_scorer.py
"""

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "granite3.1-dense:8b"

_TEMPLATE = """\
You are a rigorous internal reviewer double-checking another AI system's output
before it reaches a human. You do not regenerate the output — you assess it.

Context the original output was based on:
{context_summary}

The output produced:
{output_summary}

Score how confident a careful reviewer should be that this output is accurate,
well-supported by the context, and safe to act on without further verification.
A lower score means the reasoning is thin, generic, or could easily be wrong.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "score": <integer 0-100>,
  "rationale": "<one sentence: the single biggest reason for this score>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=["context_summary", "output_summary"],
    template=_TEMPLATE,
)


def _repair_missing_commas(text: str) -> str:
    """Same repair used by image_prompt_generator.py — insert a comma wherever
    a closing quote is followed only by whitespace and then another quoted
    key + colon (i.e. Granite omitted the comma between two fields)."""
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _extract_fields_by_regex(raw: str) -> dict | None:
    """Last-resort fallback: pull "score" and "rationale" directly out of the
    raw text via regex, ignoring overall JSON validity."""
    score_match = re.search(r'"score"\s*:\s*"?(\d+)"?', raw)
    rationale_match = re.search(r'"rationale"\s*:\s*"((?:[^"\\]|\\.)*)"', raw, re.DOTALL)
    if not score_match:
        return None
    return {
        "score": int(score_match.group(1)),
        "rationale": rationale_match.group(1).strip() if rationale_match else "",
    }


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

    repaired = _repair_missing_commas(text)
    return json.loads(repaired)


class ConfidenceScorer:
    """
    Scores how confident an earlier Granite output is, given a short summary
    of its context and its content. Never raises — always returns a usable
    {score, rationale} dict, falling back to a neutral score on any failure.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.1, num_predict=150)
        self._chain = _PROMPT | self._llm

    def score(self, context_summary: str, output_summary: str) -> dict:
        """
        Granite Call #15.
        Returns {score: int 0-100, rationale: str}.
        """
        raw = self._chain.invoke({
            "context_summary": context_summary,
            "output_summary": output_summary,
        })

        result: dict | None = None
        try:
            result = _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            result = _extract_fields_by_regex(raw)

        if not result or "score" not in result:
            return {"score": 50, "rationale": "Could not parse confidence assessment."}

        try:
            result["score"] = max(0, min(100, int(result["score"])))
        except (TypeError, ValueError):
            result["score"] = 50
        result["rationale"] = str(result.get("rationale", "")).strip()
        return result


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    scorer = ConfidenceScorer()
    result = scorer.score(
        context_summary="Post type: Reel; views=15000 reach=13000 likes=1200 comments=85 shares=210 saves=430",
        output_summary="Verdict: succeeded. Strong like-to-view ratio and high saves indicate strong resonance.",
    )
    print(json.dumps(result, indent=2))
