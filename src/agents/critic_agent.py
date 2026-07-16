"""
Critic / Editorial Agent — Granite invocations #18 (critique pass) + new #21 (classifier).

Architecture (ACL 2025 RAG-Critic pattern, coarse-to-fine):
  Step 1 — BrandGuardian.critique() identifies WHAT is wrong (issues list).
  Step 2 — ErrorClassifier (new Granite call) maps the issues to ONE typed error category.
  Step 3 — Return CriticResult with error_type and routing_target.

The Critic NEVER rewrites. The Orchestrator reads error_type and dispatches to
the appropriate correction agent (CopywritingAgent or BrandVoiceAgent).

Error taxonomy:
  ai_slop          → CopywritingAgent.rewrite_caption
  off_brand_vocab  → BrandVoiceAgent.enforce_vocabulary
  wrong_platform   → CopywritingAgent.reformat_caption
  factual_gap      → human_review_flag (no auto-route)
  approved         → no action
"""

import json
import re

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from src.agents.base import AgentResult, AgentTask, BaseAgent, OLLAMA_MODEL, ROUTING_TARGETS

_CLASSIFIER_TEMPLATE = """\
You are an editorial quality gate. You receive a caption and a list of brand-voice \
issues identified by a reviewer. Your ONLY job is to classify the PRIMARY failure mode.

Caption:
"{caption}"

Issues identified:
{issues_block}

Classify the primary failure mode as ONE of:
  ai_slop         — generic, template-like, or "obviously AI" language \
(e.g. "In today's fast-paced world", "delicious treats", "amazing quality")
  off_brand_vocab — specific terms or tone that violate brand guidelines \
(avoided terms present, wrong tone descriptor)
  wrong_platform  — formatting wrong for the target platform \
(too long, wrong hashtag count, wrong register)
  factual_gap     — specific factual claims that cannot be verified
  approved        — no significant issues found

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "error_type": "<one of the five labels above>",
  "flagged_phrase": "<shortest phrase in the caption that best illustrates the issue, or empty string>",
  "fix_direction": "<one sentence describing exactly what to fix, or 'none' if approved>"
}}
"""

_CLASSIFIER_PROMPT = PromptTemplate(
    input_variables=["caption", "issues_block"],
    template=_CLASSIFIER_TEMPLATE,
)

_VALID_ERROR_TYPES = {"ai_slop", "off_brand_vocab", "wrong_platform", "factual_gap", "approved"}


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _parse_json(raw: str) -> dict:
    text  = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_repair_missing_commas(text))


class CriticAgent(BaseAgent):
    """
    Classifies the error type of a draft and returns a routing signal.
    Does NOT rewrite — classification only.
    """

    name = "CriticAgent"

    def __init__(self, memory=None, model: str = OLLAMA_MODEL):
        super().__init__(memory, model)
        from src.generation.brand_guardian import BrandGuardian
        self._guardian   = BrandGuardian(model=model)
        self._classifier = OllamaLLM(model=model, temperature=0.1, num_predict=150)
        self._chain      = _CLASSIFIER_PROMPT | self._classifier

    def run(self, task: AgentTask) -> AgentResult:
        if task.task_type != "critique":
            return AgentResult(
                agent_name=self.name,
                success=False,
                error_message=f"CriticAgent only handles 'critique', got '{task.task_type}'",
            )
        return self._critique(task.payload)

    def _critique(self, payload: dict) -> AgentResult:
        caption    = payload.get("caption", "")
        cluster_id = payload.get("cluster_id", 0)

        # Step 1 — BrandGuardian identifies issues (Granite #18)
        critique = self._guardian.critique(caption, cluster_id)

        verdict = critique.get("verdict", "needs_revision")
        issues  = critique.get("issues", [])

        # Fast-path: guardian already approved, skip classifier
        if verdict == "approve" and not issues:
            return AgentResult(
                agent_name=self.name,
                output={
                    "guardian_critique": critique,
                    "error_type":        "approved",
                    "flagged_phrase":    "",
                    "fix_direction":     "none",
                },
                error_type="approved",
                routing_target=None,
            )

        # Step 2 — ErrorClassifier maps issues to a typed error (Granite #21)
        issues_block = "\n".join(f"- {i}" for i in (issues or ["Generic language detected."]))
        error_type, flagged_phrase, fix_direction = self._classify(caption, issues_block)

        return AgentResult(
            agent_name=self.name,
            output={
                "guardian_critique": critique,
                "error_type":        error_type,
                "flagged_phrase":    flagged_phrase,
                "fix_direction":     fix_direction,
                "severity":          critique.get("severity", "minor"),
            },
            error_type=error_type,
            routing_target=ROUTING_TARGETS.get(error_type),
        )

    def _classify(self, caption: str, issues_block: str) -> tuple[str, str, str]:
        """Run the error type classifier. Falls back to ai_slop on parse failure."""
        try:
            raw    = self._chain.invoke({"caption": caption, "issues_block": issues_block})
            result = _parse_json(raw)
            etype  = result.get("error_type", "ai_slop")
            if etype not in _VALID_ERROR_TYPES:
                etype = "ai_slop"
            return (
                etype,
                str(result.get("flagged_phrase", "")),
                str(result.get("fix_direction", "")),
            )
        except Exception:
            return ("ai_slop", "", "Rewrite to sound more human and authentic.")
