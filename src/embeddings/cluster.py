"""
Content clustering engine for @hot_cakesbakes brand data.

Embeds marketing hooks with all-MiniLM-L6-v2 (local),
then segments posts into content pillars via K-Means.

Input:  data/cleaned/ig_text_*.json   (from pipeline.py)
Output: data/clusters.json

Run:
    python src/embeddings/cluster.py
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

# ── Config ──────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLEANED_DIR   = _PROJECT_ROOT / "data" / "cleaned"
OUTPUT_PATH   = _PROJECT_ROOT / "data" / "clusters.json"

EMBED_MODEL  = "all-MiniLM-L6-v2"
DEVICE       = "auto"         # auto | mps | cuda | cpu
N_CLUSTERS   = 5
RANDOM_STATE = 42


def resolve_device(device: str = DEVICE) -> str:
    """Pick the best available backend; avoids MPS warnings on non-Mac hosts."""
    if device != "auto":
        if device == "mps":
            import torch
            return "mps" if torch.backends.mps.is_available() else "cpu"
        return device

    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_cleaned_posts(cleaned_dir: Path = CLEANED_DIR) -> list[dict]:
    records = [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(cleaned_dir.glob("ig_text_*.json"))
    ]
    records = [r for r in records if r.get("marketing_hook", "").strip()]
    if not records:
        raise FileNotFoundError(
            f"No cleaned posts found in {cleaned_dir}. Run pipeline.py first."
        )
    return records


# ── Embedding ────────────────────────────────────────────────────────────────

def embed(texts: list[str], device: str = DEVICE) -> np.ndarray:
    """
    Encode texts with all-MiniLM-L6-v2 and L2-normalise for cosine similarity.
    """
    resolved = resolve_device(device)
    model = SentenceTransformer(EMBED_MODEL, device=resolved)

    print(f"  Encoding {len(texts)} posts on {model.device}…")
    vecs = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return normalize(vecs)   # L2-norm → dot product == cosine similarity


# ── Clustering ───────────────────────────────────────────────────────────────

def cluster(embeddings: np.ndarray, n_clusters: int = N_CLUSTERS) -> np.ndarray:
    print(f"  Running K-Means (k={n_clusters})…")
    km = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init="auto")
    km.fit(embeddings)
    return km.labels_


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_clustering(
    cleaned_dir : Path = CLEANED_DIR,
    output_path : Path = OUTPUT_PATH,
    n_clusters  : int  = N_CLUSTERS,
    device      : str  = DEVICE,
) -> dict:
    """
    Full clustering pipeline.

    Returns the cluster output dict (also persisted to output_path):
    {
      "n_clusters": 5,
      "cluster_map": { "<shortcode>": <cluster_id>, ... },
      "clusters": { "0": [{shortcode, timestamp_utc, marketing_hook}, ...], ... }
    }
    """
    print("── Step 1: Loading cleaned posts")
    records    = load_cleaned_posts(cleaned_dir)
    hooks      = [r["marketing_hook"] for r in records]

    print("── Step 2: Generating embeddings")
    embeddings = embed(hooks, device)

    print("── Step 3: Clustering")
    labels     = cluster(embeddings, n_clusters)

    # ── Build output structure ─────────────────────────────────────────────
    cluster_map : dict[str, int]        = {}
    clusters    : dict[str, list[dict]] = {str(i): [] for i in range(n_clusters)}

    for record, label in zip(records, labels):
        cid = int(label)
        key = record.get("shortcode") or record.get("timestamp_utc", "unknown")
        cluster_map[key] = cid
        clusters[str(cid)].append({
            "shortcode"     : record["shortcode"],
            "timestamp_utc" : record["timestamp_utc"],
            "marketing_hook": record["marketing_hook"],
        })

    # ── Console summary ────────────────────────────────────────────────────
    print("\n── Cluster Summaries ──────────────────────────────────────────────")
    for cid in range(n_clusters):
        posts = clusters[str(cid)]
        print(f"\nCluster {cid}  ({len(posts)} posts)")
        for p in posts[:3]:
            preview = p["marketing_hook"][:100].replace("\n", " ")
            print(f"  · {preview}…")

    # ── Persist ────────────────────────────────────────────────────────────
    output = {
        "n_clusters" : n_clusters,
        "cluster_map": cluster_map,
        "clusters"   : clusters,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {output_path}")

    return output


# ── CLI entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_clustering()
    sizes  = {cid: len(posts) for cid, posts in result["clusters"].items()}
    print(f"\nCluster sizes: {sizes}")
