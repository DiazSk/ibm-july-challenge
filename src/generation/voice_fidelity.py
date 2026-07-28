"""
Brand-Voice Fidelity — deterministic, no LLM call.

Scores how well a caption uses THIS creator's own brand vocabulary: their
signature phrases, recurring words, and compliance with avoided terms (all from
brand_profile.json). Unlike an embedding cosine — which mostly measures whether
the caption is on the right *topic* — this measures whether it's in the right
*voice*. A plain LLM has never seen the brand profile, so it structurally cannot
reproduce the signature phrases; StyleSync is prompted with them. That gap is the
head-to-head hero shot in "The Drift Test".

The matched phrases/words and avoided-term violations returned here ARE the
human-readable explanation — no separate Granite call needed.

Run standalone (self-check):
    python src/generation/voice_fidelity.py
"""

import re


def _word_hits(text_lower: str, terms: list[str]) -> list[str]:
    """Whole-word matches only — so 'light' does NOT match 'delight'."""
    return [t for t in terms if re.search(rf"\b{re.escape(t.lower())}\b", text_lower)]


def score_voice_fidelity(
    text: str,
    vocabulary_patterns: dict,
    avoided_terms: list[str],
) -> dict:
    """
    Returns {score 0-100, match_label, matched_words, matched_phrases,
    avoided_violations}. Score = recurring-word coverage (up to 60) +
    signature-phrase reuse (up to 30) − 20 per avoided-term violation.
    """
    t = text.lower()
    rec = [w.lower() for w in vocabulary_patterns.get("recurring_words", [])]
    sig = [s.lower() for s in vocabulary_patterns.get("signature_phrases", [])]

    matched_words = _word_hits(t, rec)
    # Signature phrase counts if the full phrase or its leading clause (before
    # an '&') appears verbatim — creators rarely reproduce the whole line.
    matched_phrases = [
        s for s in sig
        if s in t or (s.split("&")[0].strip() and s.split("&")[0].strip() in t)
    ]
    avoided_violations = _word_hits(t, [a for a in avoided_terms])

    score = min(60, len(matched_words) * 10) + min(30, len(matched_phrases) * 15)
    score -= len(avoided_violations) * 20
    score = max(0, min(100, score))

    if score >= 60:
        label = "closely matches"
    elif score >= 25:
        label = "some drift"
    else:
        label = "significant drift"

    return {
        "score": score,
        "match_label": label,
        "matched_words": matched_words,
        "matched_phrases": matched_phrases,
        "avoided_violations": avoided_violations,
    }


if __name__ == "__main__":
    vocab = {
        "recurring_words": ["Nutella", "soft", "fluffy", "rich", "loaded", "bite", "love"],
        "signature_phrases": ["Freshly made & packed with love"],
    }
    avoided = ["healthy", "light", "dietary restrictions"]

    on_brand = (
        "Soft, fluffy Bomboloni loaded with rich Nutella in every bite. "
        "Freshly made & packed with love."
    )
    generic = "Indulging in a weekend of sweet delight with these heavenly treats!"

    r_brand = score_voice_fidelity(on_brand, vocab, avoided)
    r_generic = score_voice_fidelity(generic, vocab, avoided)
    print("on-brand:", r_brand)
    print("generic :", r_generic)

    assert r_brand["score"] >= 60, "on-brand caption should score 'closely matches'"
    assert r_generic["score"] < 25, "generic caption should score 'significant drift'"
    # 'delight' must NOT trigger the avoided term 'light'
    assert not r_generic["avoided_violations"], "word-boundary matching failed (delight≠light)"
    print("\nOK — fidelity separates on-brand from generic; no substring false positives.")
