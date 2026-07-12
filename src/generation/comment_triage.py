"""
Comment/DM Triage + Draft Replies — Granite invocation #20.

Pastes a batch of Instagram comments/DMs, classifies each (order inquiry /
compliment / complaint / spam), and drafts a brand-voice reply for every
non-spam message — the real, lived pain point of a small business losing
sales because a founder can't reply fast enough.

Honest limitation: there is no live Instagram inbox API access without
platform approval, so this is a paste-and-review batch tool, not live
automation — the UI must say so explicitly, and this module never invents
order details, prices, or promises not present in the source message.

Processed in chunks of CHUNK_SIZE messages per Granite call (not all-at-once)
to avoid JSON truncation on a small local 8B model; a chunk-level parse
failure degrades only that chunk to "uncertain" placeholders, so the caller
always gets back exactly len(messages) results, in original order.

Input:  messages: list[str], cluster_id: int
Output: list[{message_index, original_message, category, drafted_reply, reasoning}]

Run standalone:
    python src/generation/comment_triage.py
"""

import json
import re
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"
CHUNK_SIZE = 5

_VALID_CATEGORIES = {"order_inquiry", "compliment", "complaint", "spam"}

_TEMPLATE = """\
You are a customer-service assistant for {brand_name}, a homemade artisanal \
bakery on Instagram, triaging a batch of comments/DMs.

Brand voice for replies:
  Tone              : {tone_descriptors}
  Signature phrases : {signature_phrases}
  Avoided terms     : {avoided_terms}

Messages to triage (respond to ALL {count}, in this exact order):
{messages_block}

For each message:
1. Classify it as exactly one of: order_inquiry, compliment, complaint, spam
2. If NOT spam, draft a short, warm, on-brand reply. NEVER invent order
   details, prices, availability, or promises not stated in the message —
   if specifics are needed, the reply should ask the customer to DM details
   or say "check availability with us," not fabricate an answer.
3. If spam, leave drafted_reply as an empty string.

Return ONLY a valid JSON array with exactly {count} objects, in the same \
order as the messages above — no preamble, no markdown fences:

[
  {{
    "category": "<order_inquiry|compliment|complaint|spam>",
    "drafted_reply": "<reply text, or empty string if spam>",
    "reasoning": "<1 short sentence: why this category>"
  }}
]
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "tone_descriptors", "signature_phrases", "avoided_terms",
        "count", "messages_block",
    ],
    template=_TEMPLATE,
)


def _repair_missing_commas(text: str) -> str:
    return re.sub(r'"(\s+)"([A-Za-z_][A-Za-z0-9_ ]*)"\s*:', r'",\1"\2":', text)


def _parse_array(raw: str, expected_len: int) -> list[dict]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list) and parsed:
                return parsed
        except json.JSONDecodeError:
            try:
                parsed = json.loads(_repair_missing_commas(candidate))
                if isinstance(parsed, list) and parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

    # Last resort: extract individual JSON objects from anywhere in the text
    objects = re.findall(r"\{[^{}]+\}", text, re.DOTALL)
    results = []
    for obj_str in objects:
        try:
            obj = json.loads(obj_str)
            if "category" in obj:
                results.append(obj)
        except (json.JSONDecodeError, ValueError):
            continue
    if results:
        return results

    raise ValueError("Could not extract triage JSON from Granite response")


class CommentTriager:
    """
    Classifies and drafts replies for a batch of comments/DMs, chunked to
    stay reliable on a small local model. Never raises — a failed chunk
    degrades to "uncertain" placeholders instead of dropping messages.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.3, num_predict=1200)
        self._chain = _PROMPT | self._llm
        self._profile: dict = json.loads(BRAND_PROFILE_PATH.read_text(encoding="utf-8"))

    def _brand_voice(self, cluster_id: int) -> dict:
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
            "avoided_terms": ", ".join(p.get("avoided_terms", [])),
        }

    def _triage_chunk(self, chunk: list[str], voice: dict) -> list[dict]:
        messages_block = "\n".join(f"{i + 1}. {m}" for i, m in enumerate(chunk))
        raw = self._chain.invoke({**voice, "count": len(chunk), "messages_block": messages_block})

        try:
            parsed = _parse_array(raw, len(chunk))
        except (json.JSONDecodeError, ValueError):
            parsed = []

        results = []
        for i in range(len(chunk)):
            item = parsed[i] if i < len(parsed) else {}
            category = item.get("category", "uncertain")
            if category not in _VALID_CATEGORIES:
                category = "uncertain"
            results.append({
                "category": category,
                "drafted_reply": str(item.get("drafted_reply", "")) if category != "spam" else "",
                "reasoning": str(item.get("reasoning", "")),
            })
        return results

    def triage_batch(self, messages: list[str], cluster_id: int = 0) -> list[dict]:
        """
        Granite Call #20 (one per chunk of up to CHUNK_SIZE messages).
        Returns len(messages) dicts, original order preserved:
        [{message_index, original_message, category, drafted_reply, reasoning}, ...]
        """
        voice = self._brand_voice(cluster_id)
        all_results: list[dict] = []

        for chunk_start in range(0, len(messages), CHUNK_SIZE):
            chunk = messages[chunk_start : chunk_start + CHUNK_SIZE]
            chunk_results = self._triage_chunk(chunk, voice)
            for offset, result in enumerate(chunk_results):
                idx = chunk_start + offset
                all_results.append({
                    "message_index": idx,
                    "original_message": messages[idx],
                    **result,
                })

        return all_results


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    triager = CommentTriager()

    messages = [
        "Hi! Do you have Nutella Bomboloni available this weekend? Want to order 6 for a party.",
        "OMG these look SO good, following you now!!",
        "I ordered last week and the box arrived squished, very disappointed for the price I paid.",
        "FREE FOLLOWERS CLICK MY BIO NOW!!! www.spam-link-example.com",
        "Can I get a dozen assorted donuts delivered to Vashi by Saturday morning?",
        "Your bakery is literally the best thing about my week, thank you for existing!",
        "This is way overpriced compared to other bakeries nearby, not ordering again.",
        "hey check out my page for crypto tips 🚀🚀🚀",
    ]

    results = triager.triage_batch(messages, cluster_id=0)
    for r in results:
        print(f"\n--- Message {r['message_index']} [{r['category']}] ---".encode("ascii", "replace").decode())
        print(r["original_message"].encode("ascii", "replace").decode())
        if r["drafted_reply"]:
            print(f"Reply: {r['drafted_reply']}".encode("ascii", "replace").decode())
