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
  "content_pillar": "<a short, distinctive 2-4 word Title Case name for THIS cluster's specific theme, named after the concrete subject or format that dominates these posts — e.g. 'Nutella Series', 'Bomboloni', 'Behind the Scenes', 'Fusion Cakes', 'Custom Orders'. NOT a generic category like 'Product Showcase'. Make it specific enough to distinguish this cluster from the brand's other content clusters.>",
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

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback (only reached when strict parsing already failed, so it can't
    # corrupt valid JSON). Repair the two quirks Granite 3.1 produces: a missing
    # comma between fields, and a response truncated at the token cap. Without
    # this, one malformed character discards the whole cluster profile.
    repaired = _repair_truncated_json(_insert_missing_commas(text))
    return json.loads(repaired)


def _insert_missing_commas(text: str) -> str:
    """Insert a comma where a value-close is directly followed by the next key."""
    # e.g.  "avoided_terms": [...]\n  "structural_signature": ...  (comma dropped)
    return re.sub(r'([}\]"])(\s*\n\s*)("[\w ]+"\s*:)', r"\1,\2\3", text)


def _repair_truncated_json(text: str) -> str:
    """Close strings/brackets left open by a truncated response."""
    stack: list[str] = []
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:            esc = False
            elif ch == "\\":   esc = True
            elif ch == '"':    in_str = False
        elif ch == '"':        in_str = True
        elif ch in "{[":       stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack: stack.pop()

    repaired = text + ('"' if in_str else "")
    repaired = repaired.rstrip()
    if repaired.endswith(","):
        repaired = repaired[:-1]
    elif repaired.endswith(":"):
        repaired += " null"
    return repaired + "".join(reversed(stack))


# ── Pillar-name de-duplication ────────────────────────────────────────────────
# Each cluster is named in its own Granite call, so the model cannot see what
# its siblings were called and the prompt's "make it distinct" instruction is
# unenforceable. Two custom-cake clusters reliably came back as "Custom Cakes &
# Bulk Orders" and "Custom Cakes & Desserts". One extra call, seeing all the
# names at once, fixes the set.

_RENAME_TEMPLATE = """\
You are naming the content pillars of one Instagram brand: {brand_name}.

Current pillar names, with sample posts from each:

{clusters_text}

Problem — these names are too similar to tell apart: {collisions}

Rename ONLY those clusters so every pillar name in the set is clearly distinct.
Each new name must be 2-4 words, Title Case, and capture what actually separates
that cluster from the others — the format, occasion, or specific product that
dominates it. Do not reuse a first word that another pillar already uses.

Return ONLY a JSON object mapping cluster id to its new name, nothing else:
{{"2": "Bulk Dessert Orders", "4": "Celebration Cakes"}}
"""

_RENAME_PROMPT = PromptTemplate.from_template(_RENAME_TEMPLATE)


def _existing_timezone(output_path: Path, default: str = "UTC") -> str:
    """
    Carry the brand's timezone across rebuilds so a re-sync doesn't reset it.
    Set once (at onboarding); every later pipeline run preserves it.
    """
    try:
        return json.loads(output_path.read_text(encoding="utf-8")).get("timezone") or default
    except (OSError, json.JSONDecodeError):
        return default


def _pillar_name(entry: dict) -> str:
    return (entry.get("profile") or {}).get("content_pillar", "") or ""


def colliding_cluster_ids(names: dict[int, str]) -> list[int]:
    """
    Cluster ids whose pillar name shares its first word with another pillar.

    First word is what the eye anchors on and what compact chart labels used to
    truncate to, so a shared one means the names don't read as distinct.
    """
    buckets: dict[str, list[int]] = {}
    for cid, name in names.items():
        head = name.strip().split(" ")[0].lower()
        if head:
            buckets.setdefault(head, []).append(cid)
    return sorted(cid for ids in buckets.values() if len(ids) > 1 for cid in ids)


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
        timezone   : str | None = None,   # IANA name; None keeps whatever is on disk
    ):
        self.model       = model
        self._brand_name = brand_name
        self._ig_handle  = ig_handle
        self._brand_bio  = brand_bio
        self._timezone   = timezone
        self._llm  = OllamaLLM(
            model       = model,
            temperature = 0.0,       # deterministic — brand analysis needs consistency
            num_predict = 1400,      # headroom so the full JSON (incl. representative_post) isn't truncated
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

    # ── Pillar-name de-duplication ────────────────────────────────────────────

    def dedupe_pillar_names(
        self,
        cluster_profiles: list[dict],
        clusters        : dict[str, list[dict]],
    ) -> None:
        """
        Rename pillars whose names aren't distinguishable from each other.
        Mutates cluster_profiles in place; a no-op when the names are already
        distinct, so the extra Granite call only happens when it's needed.
        """
        names = {e["cluster_id"]: _pillar_name(e) for e in cluster_profiles}
        collisions = colliding_cluster_ids(names)
        if not collisions:
            return

        print(f"\n  → Pillar names collide on {collisions} — asking Granite to rename…")

        clusters_text = "\n\n".join(
            f'Cluster {cid} — "{names[cid]}" ({len(clusters.get(str(cid), []))} posts)\n'
            + "\n".join(
                f"  · {p['marketing_hook'].strip()[:110]}"
                for p in clusters.get(str(cid), [])[:3]
            )
            for cid in sorted(names)
        )
        collisions_text = ", ".join(f'"{names[cid]}" (cluster {cid})' for cid in collisions)

        raw = (_RENAME_PROMPT | self._llm).invoke({
            "brand_name"   : self._brand_name,
            "clusters_text": clusters_text,
            "collisions"   : collisions_text,
        })

        try:
            renames = _parse_json(raw)
        except (json.JSONDecodeError, ValueError):
            print("     ⚠ rename pass returned unparseable JSON — keeping original names.")
            return

        for entry in cluster_profiles:
            new = renames.get(str(entry["cluster_id"]))
            if entry["cluster_id"] in collisions and isinstance(new, str) and new.strip():
                print(f"     cluster {entry['cluster_id']}: {_pillar_name(entry)!r} → {new.strip()!r}")
                entry["profile"]["content_pillar"] = new.strip()

        still = colliding_cluster_ids({e["cluster_id"]: _pillar_name(e) for e in cluster_profiles})
        if still:
            print(f"     ⚠ names still collide on {still} — left as-is.")

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

        self.dedupe_pillar_names(cluster_profiles, clusters)

        brand_profile = {
            "brand_name"      : self._brand_name,
            "ig_handle"       : self._ig_handle,
            "brand_bio"       : self._brand_bio,
            # The audience's timezone, not the viewer's — "best day to post" is a
            # different answer in Mumbai than in California for the same posts.
            "timezone"        : self._timezone or _existing_timezone(output_path),
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

def _check_parser() -> None:
    """Offline assert-check for the JSON repair fallbacks (no Ollama needed)."""
    # Missing comma between fields (Granite 3.1's common quirk).
    missing_comma = '{"a": ["x", "y"]\n  "b": "z"}'
    assert _parse_json(missing_comma) == {"a": ["x", "y"], "b": "z"}
    # Truncated mid-list (token cap).
    truncated = '{"a": "hi", "b": ["one", "two'
    assert _parse_json(truncated) == {"a": "hi", "b": ["one", "two"]}
    # Both at once + markdown fence + trailing prose.
    both = 'here:\n```json\n{"a": "1"\n  "b": ["k"\n```'
    assert _parse_json(both)["a"] == "1"
    # Well-formed still parses.
    assert _parse_json('{"a": 1, "b": [2, 3]}') == {"a": 1, "b": [2, 3]}
    print("profile_extractor parser self-check passed.")


if __name__ == "__main__":
    import sys
    if "--check-parser" in sys.argv:
        _check_parser()
    else:
        extractor = BrandProfileExtractor()
        profile   = extractor.build_brand_profile()
        print(f"\nDone — {profile['n_clusters']} content pillars extracted.")
