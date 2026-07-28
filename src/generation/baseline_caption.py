"""
Baseline Caption Generator — the honest control for "The Drift Test".

Generates a single Instagram caption with a GENERIC prompt: no brand profile,
no memory, no cluster grounding. It simulates what a creator gets from a plain
LLM (e.g. ChatGPT). Uses the SAME model as StyleSync (granite3.1-dense:8b) so
any head-to-head difference is about brand *grounding*, not model quality.

This exists so the Create tab can show a side-by-side drift score: baseline
(this) vs StyleSync (caption_generator.py), both scored against the creator's
real brand profile via brand_drift.detect_nearest_cluster_and_signal().

Run standalone (self-check):
    python src/generation/baseline_caption.py
"""

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

OLLAMA_MODEL = "granite3.1-dense:8b"

_TEMPLATE = """\
Write a single Instagram caption for the following post.

Product / topic : {product}
Occasion        : {occasion}

Return ONLY the caption text — no preamble, no options, no explanation.
"""

_PROMPT = PromptTemplate(input_variables=["product", "occasion"], template=_TEMPLATE)


class BaselineCaptionGenerator:
    """Plain-LLM caption — no brand grounding. One Granite call, returns a str."""

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.7, num_predict=400)
        self._chain = _PROMPT | self._llm

    def generate(self, product: str, occasion: str = "") -> str:
        raw = self._chain.invoke({
            "product": product,
            "occasion": occasion or "a general post",
        })
        return raw.strip()


# ── Standalone self-check ───────────────────────────────────────────────────────
# The generator just needs to produce a caption; the head-to-head scoring contrast
# is validated in voice_fidelity.py's own self-check.
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")  # captions contain emoji; Windows console is cp1252
    baseline = BaselineCaptionGenerator().generate("Nutella Bomboloni", "Weekend craving post")
    print(f"Baseline caption:\n  {baseline}")
    assert baseline.strip(), "baseline generator returned empty text"
    print("\nOK — baseline generator produces a caption.")
