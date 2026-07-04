"""
Voice Refiner — Granite invocation #12.

Takes a raw spoken caption idea (transcribed via browser Web Speech API)
and the creator's brand voice cluster profile, then returns a polished,
on-brand caption that preserves the emotional core of the spoken idea.

This closes the voice loop: speak an idea → Granite refines it → TTS reads it back.

Input:  transcript (raw spoken text), cluster_id (int), brand_profile (dict)
Output: {refined_caption: str, reasoning: str}

Run standalone:
    python src/generation/voice_refiner.py
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
You are a caption writer for {brand_name}, an artisan bakery with a specific brand voice.

The creator just spoke this idea aloud (raw, unpolished):
"{transcript}"

Their brand voice for this content pillar ({cluster_name}) is:
- Tone: {tone}
- Signature phrases they use: {phrases}
- Recurring words: {words}

Transform the spoken idea into a polished Instagram caption in their exact brand voice. \
Preserve the emotional core of what they said. Keep it under 150 words. \
Do NOT add generic hashtags or emojis unless their brand naturally uses them.

Return ONLY valid JSON — no preamble, no markdown fences:
{{
  "refined_caption": "<the polished caption>",
  "reasoning": "<one sentence: what you preserved from their spoken idea and why this voice fits>"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=["brand_name", "transcript", "cluster_name", "tone", "phrases", "words"],
    template=_TEMPLATE,
)


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


def _extract_cluster_voice(brand_profile: dict, cluster_id: int) -> dict:
    for cp in brand_profile.get("cluster_profiles", []):
        if cp["cluster_id"] == cluster_id:
            p = cp.get("profile", {})
            voc = p.get("vocabulary_patterns", {})
            return {
                "tone"   : p.get("tone_descriptors", []),
                "phrases": voc.get("signature_phrases", []),
                "words"  : voc.get("recurring_words", []),
            }
    # fallback to first cluster
    if brand_profile.get("cluster_profiles"):
        p = brand_profile["cluster_profiles"][0].get("profile", {})
        voc = p.get("vocabulary_patterns", {})
        return {
            "tone"   : p.get("tone_descriptors", []),
            "phrases": voc.get("signature_phrases", []),
            "words"  : voc.get("recurring_words", []),
        }
    return {"tone": [], "phrases": [], "words": []}


class VoiceRefiner:
    """
    Granite #12 — transforms a raw spoken caption idea into a polished,
    on-brand Instagram caption using the creator's brand voice profile.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm   = OllamaLLM(model=model, temperature=0.4, num_predict=300)
        self._chain = _PROMPT | self._llm

    def refine(self, transcript: str, cluster_id: int, brand_profile: dict) -> dict:
        """
        Granite Call #12.
        Returns {refined_caption, reasoning}.
        """
        voice = _extract_cluster_voice(brand_profile, cluster_id)
        cluster_name = _CLUSTER_ID_LABELS.get(cluster_id, f"Cluster {cluster_id}")

        raw = self._chain.invoke({
            "brand_name"  : brand_profile.get("brand_name", "the brand"),
            "transcript"  : transcript.strip(),
            "cluster_name": cluster_name,
            "tone"        : ", ".join(voice["tone"][:3]) or "warm and authentic",
            "phrases"     : ", ".join(f'"{p}"' for p in voice["phrases"][:3]) or "none listed",
            "words"       : ", ".join(voice["words"][:5]) or "none listed",
        })

        try:
            return _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            return {
                "refined_caption": raw.strip(),
                "reasoning"      : "Preserved the emotional core of your spoken idea.",
            }


# ── Standalone demo ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    profile = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))
    refiner = VoiceRefiner()

    test_transcript = "I just pulled the last batch of pistachio rose bomboloni out of the fryer and the whole kitchen smells incredible right now"
    result = refiner.refine(test_transcript, cluster_id=4, brand_profile=profile)
    print("Refined caption:")
    print(result["refined_caption"])
    print("\nReasoning:", result["reasoning"])
