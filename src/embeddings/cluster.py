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

UNCATEGORIZED_ID = -1   # posts with real metrics but no caption copy to cluster


def load_cleaned_posts(cleaned_dir: Path = CLEANED_DIR) -> tuple[list[dict], list[dict]]:
    """
    Return (voiced, thin).

    `voiced` posts carry marketing copy and drive clustering and the voice
    profile. `thin` posts have no usable copy but do have real engagement — they
    are excluded from K-Means yet must still reach every analytics surface, so
    they ride along in the output under UNCATEGORIZED_ID.
    """
    records = [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(cleaned_dir.glob("ig_text_*.json"))
    ]
    if not records:
        raise FileNotFoundError(
            f"No cleaned posts found in {cleaned_dir}. Run pipeline.py first."
        )
    voiced = [r for r in records if r.get("marketing_hook", "").strip()]
    thin   = [r for r in records if not r.get("marketing_hook", "").strip()]
    if not voiced:
        raise ValueError(f"No posts with marketing copy in {cleaned_dir}.")
    return voiced, thin


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

def cluster(
    embeddings: np.ndarray, n_clusters: int = N_CLUSTERS
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (labels, centroids). Centroids are kept because scoring a *new*
    caption against a pillar needs the pillar's centre — recovering it later
    would mean re-fitting K-Means and hoping for the same partition.
    """
    print(f"  Running K-Means (k={n_clusters})…")
    km = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init="auto")
    km.fit(embeddings)
    return km.labels_, km.cluster_centers_


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
      "clusters": { "0": [{shortcode, timestamp_utc, marketing_hook}, ...], ... },
      "centroids": [[float, ...], ...],   # row i = centre of cluster i
      "embed_model": "all-MiniLM-L6-v2"
    }
    """
    print("── Step 1: Loading cleaned posts")
    records, thin = load_cleaned_posts(cleaned_dir)
    hooks         = [r["marketing_hook"] for r in records]
    if thin:
        print(f"  {len(thin)} post(s) have metrics but no copy → cluster {UNCATEGORIZED_ID}")

    print("── Step 2: Generating embeddings")
    embeddings = embed(hooks, device)

    print("── Step 3: Clustering")
    labels, centroids = cluster(embeddings, n_clusters)

    # ── Build output structure ─────────────────────────────────────────────
    cluster_map : dict[str, int]        = {}
    clusters    : dict[str, list[dict]] = {str(i): [] for i in range(n_clusters)}

    def _emit(record: dict, cid: int) -> None:
        key = record.get("shortcode") or record.get("timestamp_utc", "unknown")
        cluster_map[key] = cid
        clusters.setdefault(str(cid), []).append({
            "shortcode"     : record["shortcode"],
            "timestamp_utc" : record["timestamp_utc"],
            "marketing_hook": record["marketing_hook"],
            "engagement"    : record.get("engagement", {}),
        })

    for record, label in zip(records, labels):
        _emit(record, int(label))

    # Metrics-only posts: never embedded, never profiled, but present so KPIs,
    # top posts and best-day are computed over the whole account.
    for record in thin:
        _emit(record, UNCATEGORIZED_ID)

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
        # Row i is the centre of cluster i, in the same L2-normalised space as
        # embed(), so cosine to a pillar is a plain dot product.
        "centroids"  : centroids.tolist(),
        "embed_model": EMBED_MODEL,
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
