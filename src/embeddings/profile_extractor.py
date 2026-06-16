"""
Granite Brand Profile Extractor — local inference via Ollama.

Uses IBM Granite 3.1 running locally on Apple Silicon (Metal/MPS).
No API keys, no cloud costs — pull the model once with:

    ollama pull granite3.1-dense:8b

For each content cluster, Granite extracts:
  - content_pillar      what type of content this cluster represents
  - tone_descriptors    3-5 adjectives that describe the brand voice here
  - vocabulary_patterns recurring words, signature phrases, emoji style
  - avoided_terms       what HotCakes Bakes conspicuously does NOT say
  - structural_signature how posts in this cluster are built

Compiles all cluster profiles into data/brand_profile.json.

Input:  data/clusters.json     (from cluster.py)
Output: data/brand_profile.json

Run:
    python src/embeddings/profile_extractor.py
"""

import json
import re
from pathlib import Path

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

# ── Config ───────────────────────────────────────────────────────────────────
_PROJECT_ROOT      = Path(__file__).resolve().parent.parent.parent
CLUSTERS_PATH      = _PROJECT_ROOT / "data" / "clusters.json"
BRAND_PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"

BRAND_NAME   = "HotCakes Bakes"
IG_HANDLE    = "@hot_cakesbakes"
BRAND_BIO    = "Homemade cakes & desserts. Based in Taloja, Navi Mumbai. Baked with love, served with joy."

# IBM Granite 3.1 via Ollama — free, local, M4-accelerated
# Pull with: ollama pull granite3.1-dense:8b
OLLAMA_MODEL       = "granite3.1-dense:8b"
MAX_POSTS_PER_CALL = 12   # cap per Granite context window


# ── Prompt ────────────────────────────────────────────────────────────────────
# Structured JSON extraction prompt tuned for Granite 3.1's instruction format.
# Double-braces {{ }} are PromptTemplate escape sequences, not Granite tokens.
_TEMPLATE = """\
You are a brand voice analyst specialising in artisanal food businesses on Instagram.

Brand context:
  Name:    {brand_name}
  Handle:  {ig_handle}
  Bio:     {brand_bio}

You are given {n_posts} real Instagram posts from this brand (marketing copy only; \
ordering info and location details have been removed). Analyse them as a group.

Return ONLY a valid JSON object — no preamble, no explanation, no markdown fences:

{{
  "content_pillar": "<one of: product_showcase | behind_scenes | seasonal_special | customer_connection | brand_story>",
  "tone_descriptors": ["<adj>", "<adj>", "<adj>"],
  "vocabulary_patterns": {{
    "recurring_words"  : ["<word>", "<word>", "<word>"],
    "signature_phrases": ["<short phrase>", "<short phrase>"],
    "emoji_style"      : "<one sentence: how are emojis used in this cluster?>"
  }},
  "avoided_terms": ["<term or style conspicuously absent from this brand>"],
  "structural_signature": "<one sentence: how are these posts typically structured?>",
  "representative_post" : "<verbatim copy of the single most on-brand post in the set>"
}}

Posts:
---
{posts_text}
---

JSON:
"""

_PROMPT = PromptTemplate(
    input_variables=["brand_name", "ig_handle", "brand_bio", "n_posts", "posts_text"],
    template=_TEMPLATE,
)


# ── JSON extraction ───────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """
    Extract JSON from Granite's response, handling optional markdown fences
    and any leading/trailing prose.
    """
    text = raw.strip()

    # Strip ```json ... ``` wrappers
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    # Find the outermost { ... } block
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    return json.loads(text)


# ── Extractor ─────────────────────────────────────────────────────────────────

class BrandProfileExtractor:
    """
    Builds a structured brand profile by running each content cluster through
    IBM Granite 3.1 (local Ollama inference). Accepts optional brand identity
    params so any account's data can be analyzed, not just @hot_cakesbakes.
    """

    def __init__(
        self,
        model      : str = OLLAMA_MODEL,
        brand_name : str = BRAND_NAME,
        ig_handle  : str = IG_HANDLE,
        brand_bio  : str = BRAND_BIO,
    ):
        self.model       = model
        self._brand_name = brand_name
        self._ig_handle  = ig_handle
        self._brand_bio  = brand_bio
        self._llm  = OllamaLLM(
            model       = model,
            temperature = 0.0,       # deterministic — brand analysis needs consistency
            num_predict = 900,       # max tokens in response
        )
        self._chain = _PROMPT | self._llm

    # ── Single cluster ────────────────────────────────────────────────────────

    def _format_posts(self, posts: list[dict]) -> str:
        sample = posts[:MAX_POSTS_PER_CALL]
        return "\n\n".join(
            f"[{i + 1}] {p['marketing_hook'].strip()}"
            for i, p in enumerate(sample)
        )

    def extract_cluster_profile(self, cluster_id: int, posts: list[dict]) -> dict:
        posts_text = self._format_posts(posts)
        n_posts    = min(len(posts), MAX_POSTS_PER_CALL)

        print(f"  → Cluster {cluster_id}  ({len(posts)} posts)  calling Granite…")

        raw = self._chain.invoke({
            "brand_name": self._brand_name,
            "ig_handle" : self._ig_handle,
            "brand_bio" : self._brand_bio,
            "n_posts"   : str(n_posts),
            "posts_text": posts_text,
        })

        try:
            profile = _parse_json(raw)
            print(f"     pillar → {profile.get('content_pillar', '?')}")
        except (json.JSONDecodeError, ValueError):
            print(f"     ⚠ JSON parse failed for cluster {cluster_id} — storing raw.")
            profile = {"raw_response": raw, "parse_error": True}

        return {
            "cluster_id": cluster_id,
            "post_count": len(posts),
            "profile"   : profile,
        }

    # ── Full profile build ────────────────────────────────────────────────────

    def build_brand_profile(
        self,
        clusters_path      : Path = CLUSTERS_PATH,
        output_path        : Path = BRAND_PROFILE_PATH,
    ) -> dict:
        """
        Iterate every cluster → extract Granite profile → compile brand_profile.json.
        """
        data     = json.loads(clusters_path.read_text(encoding="utf-8"))
        clusters : dict[str, list[dict]] = data["clusters"]

        print(
            f"\nBuilding brand profile — {len(clusters)} clusters "
            f"via {self.model} (local Ollama)\n"
            + "─" * 60
        )

        cluster_profiles = []
        for cid_str, posts in sorted(clusters.items(), key=lambda x: int(x[0])):
            if not posts:
                continue
            result = self.extract_cluster_profile(int(cid_str), posts)
            cluster_profiles.append(result)

        brand_profile = {
            "brand_name"      : self._brand_name,
            "ig_handle"       : self._ig_handle,
            "brand_bio"       : self._brand_bio,
            "model_used"      : self.model,
            "inference_backend": "ollama-local",
            "n_clusters"      : len(cluster_profiles),
            "cluster_profiles": cluster_profiles,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(brand_profile, indent=2, ensure_ascii=False), encoding="utf-8")

        print("\n" + "─" * 60)
        print(f"Brand profile saved → {output_path}")
        return brand_profile


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    extractor = BrandProfileExtractor()
    profile   = extractor.build_brand_profile()
    print(f"\nDone — {profile['n_clusters']} content pillars extracted.")
