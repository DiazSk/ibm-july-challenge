"""
Brand Drift Watchdog — Granite invocation #19.

Paste a batch of recent post captions; the module auto-detects which locked
content pillar they most resemble (via a mean-vector cosine similarity over
the same all-MiniLM-L6-v2 embeddings used at onboarding — no manual cluster
picker needed), then Granite explains SPECIFICALLY what's drifted from that
pillar's locked brand voice profile, not a generic diagnosis.

No centroids are persisted anywhere in this codebase, so the similarity
signal is computed fresh per request by re-embedding a sample of the
cluster's original posts — cheap (sub-second, local, zero Ollama calls) and
needs no new persistent-state design.

Input:  pasted_posts: list[str], clusters_data (data/clusters.json),
        embedder: SentenceTransformer (from api.dependencies.get_sentence_embedder)
Output: detect_nearest_cluster_and_signal() -> (cluster_id, signal dict)
        BrandDriftAnalyzer.analyze_drift() -> {drift_detected, drift_summary,
            specific_changes, still_on_brand, severity}

Note: mean_similarity is a coarse, sample-based approximation, not a precise
metric — frame it in the UI as "closely matches" / "some drift" / "significant
drift" labels, never as a raw percentage.

Run standalone:
    python src/generation/brand_drift.py
"""

import json
import re
from pathlib import Path

import numpy as np
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from sklearn.preprocessing import normalize

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

OLLAMA_MODEL = "granite3.1-dense:8b"
MAX_POSTS_PER_CALL = 12

_TEMPLATE = """\
You are a brand-voice auditor for {brand_name}, a homemade artisanal bakery \
on Instagram. You are comparing a batch of RECENT posts against the LOCKED \
brand voice profile for their closest-matching content pillar, established \
from this creator's historical posting patterns.

Locked brand voice profile ({content_pillar}):
  Tone              : {tone_descriptors}
  Signature phrases : {signature_phrases}
  Recurring words   : {recurring_words}
  Structural pattern: {structural_signature}
  Avoided terms     : {avoided_terms}

An embedding-similarity check found these recent posts are "{direction}" to \
this pillar's historical posts (mean similarity {mean_similarity}).

Recent posts to audit:
{pasted_posts_block}

Compare the recent posts against the locked profile. Be SPECIFIC — name \
exact vocabulary, tone shifts, or structural changes, quoting the recent \
posts where useful. Do not give a generic answer.

Return ONLY valid JSON — no preamble, no markdown fences:

{{
  "drift_detected": true or false,
  "drift_summary": "<2-3 sentences: the overall verdict on brand voice consistency>",
  "specific_changes": ["<specific drifted element 1, with evidence>", "<specific drifted element 2>"],
  "still_on_brand": ["<specific element still consistent with the locked profile>"],
  "severity": "none" or "mild" or "significant"
}}
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "brand_name", "content_pillar", "tone_descriptors", "signature_phrases",
        "recurring_words", "structural_signature", "avoided_terms",
        "direction", "mean_similarity", "pasted_posts_block",
    ],
    template=_TEMPLATE,
)

_VALID_SEVERITIES = {"none", "mild", "significant"}


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


def _stringify_item(item) -> str:
    """
    Granite sometimes returns list items as {"element": ..., "description": ...}
    objects instead of plain strings. Render those cleanly instead of falling
    back to Python's dict repr (which looks like broken JSON to a user).
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if "element" in item and "description" in item:
            return f"{item['element']}: {item['description']}"
        return " — ".join(str(v) for v in item.values() if v)
    return str(item)


def _encode(embedder, texts: list[str]) -> np.ndarray:
    """L2-normalized embeddings via a pre-loaded SentenceTransformer instance."""
    vecs = embedder.encode(texts, convert_to_numpy=True)
    return normalize(vecs)


def detect_nearest_cluster_and_signal(
    pasted_posts: list[str],
    clusters_data: dict,
    embedder,
    sample_size: int = 20,
) -> tuple[int, dict]:
    """
    Pure function, no Granite call. Mean-pools the pasted batch's embeddings
    and compares (cosine similarity) against a sample of each cluster's
    original posts, auto-detecting the nearest content pillar.

    Returns (nearest_cluster_id, {mean_similarity, sample_size_used, direction}).
    """
    pasted_vecs = _encode(embedder, pasted_posts)
    pasted_mean = pasted_vecs.mean(axis=0)
    pasted_mean = pasted_mean / np.linalg.norm(pasted_mean)

    best_cid = 0
    best_sim = -1.0
    best_sample_size = 0

    for cid_str, posts in clusters_data.get("clusters", {}).items():
        hooks = [p["marketing_hook"] for p in posts[:sample_size] if p.get("marketing_hook")]
        if not hooks:
            continue
        cluster_vecs = _encode(embedder, hooks)
        cluster_mean = cluster_vecs.mean(axis=0)
        cluster_mean = cluster_mean / np.linalg.norm(cluster_mean)
        sim = float(np.dot(pasted_mean, cluster_mean))
        if sim > best_sim:
            best_sim = sim
            best_cid = int(cid_str)
            best_sample_size = len(hooks)

    if best_sim > 0.65:
        direction = "similar"
    elif best_sim > 0.4:
        direction = "diverging"
    else:
        direction = "very_different"

    return best_cid, {
        "mean_similarity": round(best_sim, 3),
        "sample_size_used": best_sample_size,
        "direction": direction,
    }


class BrandDriftAnalyzer:
    """
    Explains specifically how a batch of recent posts has drifted from a
    content pillar's locked brand voice profile. Never raises — falls back
    to a neutral, clearly-labeled result if Granite's output can't be parsed.
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self._llm = OllamaLLM(model=model, temperature=0.3, num_predict=500)
        self._chain = _PROMPT | self._llm
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
            "content_pillar": p.get("content_pillar", "product_showcase"),
            "tone_descriptors": ", ".join(p.get("tone_descriptors", [])),
            "signature_phrases": ", ".join(voc.get("signature_phrases", [])),
            "recurring_words": ", ".join(voc.get("recurring_words", [])),
            "structural_signature": p.get("structural_signature", ""),
            "avoided_terms": ", ".join(p.get("avoided_terms", [])),
        }

    def analyze_drift(self, pasted_posts: list[str], cluster_id: int, similarity_signal: dict) -> dict:
        """
        Granite Call #19.
        Returns {drift_detected, drift_summary, specific_changes, still_on_brand, severity}.
        """
        voice = self._cluster_voice(cluster_id)
        capped = pasted_posts[:MAX_POSTS_PER_CALL]
        posts_block = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(capped))

        raw = self._chain.invoke({
            **voice,
            "direction": similarity_signal.get("direction", "diverging"),
            "mean_similarity": similarity_signal.get("mean_similarity", 0.5),
            "pasted_posts_block": posts_block,
        })

        try:
            result = _parse_json(raw)
            result["drift_detected"] = bool(result.get("drift_detected", False))
            result["specific_changes"] = [_stringify_item(c) for c in (result.get("specific_changes") or [])][:6]
            result["still_on_brand"] = [_stringify_item(c) for c in (result.get("still_on_brand") or [])][:6]
            severity = result.get("severity", "mild")
            result["severity"] = severity if severity in _VALID_SEVERITIES else "mild"
            result["drift_summary"] = str(result.get("drift_summary", ""))
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            return {
                "drift_detected": False,
                "drift_summary": "Could not parse the drift analysis.",
                "specific_changes": [],
                "still_on_brand": [],
                "severity": "mild",
            }


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(_PROJECT_ROOT))
    from sentence_transformers import SentenceTransformer

    clusters_data = json.loads((_PROJECT_ROOT / "data" / "clusters.json").read_text(encoding="utf-8"))
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    print("-- On-brand batch (styled like Nutella Series) --")
    on_brand_posts = [
        "Soft, fluffy Bomboloni filled with rich Nutella till every bite melts in your mouth. Made fresh at home with lots of love.",
        "Our Nutella Croissants are back! Flaky, buttery, and packed with gooey Nutella in every layer. Freshly made & packed with love.",
        "There's nothing like the smell of fresh Nutella pastries straight from our home kitchen. A little indulgence for your Sunday.",
    ]
    cid, signal = detect_nearest_cluster_and_signal(on_brand_posts, clusters_data, embedder)
    print(f"Nearest cluster: {cid}, signal: {json.dumps(signal)}")

    analyzer = BrandDriftAnalyzer()
    result = analyzer.analyze_drift(on_brand_posts, cid, signal)
    print(json.dumps(result, indent=2))

    print("\n-- Deliberately different batch (generic corporate marketing) --")
    drifted_posts = [
        "LIMITED TIME OFFER: 20% off all products this week only! Shop now before it's gone!",
        "We are excited to announce our new product line, engineered for maximum customer satisfaction.",
        "Follow us for exclusive deals and don't forget to like, share, and subscribe!",
    ]
    cid2, signal2 = detect_nearest_cluster_and_signal(drifted_posts, clusters_data, embedder)
    print(f"Nearest cluster: {cid2}, signal: {json.dumps(signal2)}")

    result2 = analyzer.analyze_drift(drifted_posts, cid2, signal2)
    print(json.dumps(result2, indent=2))
