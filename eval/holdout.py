"""
Leak-free train/test split for the fidelity evaluation.

The shipped data/brand_profile.json was extracted over every clustered post, so
scoring generated captions against it tells you nothing: the profile has already
seen the answers. This script rebuilds the pipeline on a strict subset.

  1. Split the 208 voiced posts into train / test, stratified by current pillar.
  2. Re-fit K-Means on the TRAIN captions only, keeping the new centroids.
  3. Assign each TEST post to its nearest train centroid — the test posts never
     influence the partition.
  4. Re-run BrandProfileExtractor over the train-only clusters.
  5. Assert no vocabulary in the resulting profile is exclusive to the test set.

Step 5 is the whole point. If it fails, the evaluation downstream is measuring
memorisation and the result is worthless.

data/cleaned/ is empty in this checkout, so the pipeline input is reconstructed
from data/clusters.json, which carries the captions and engagement already.

Run (requires Ollama with granite3.1-dense:8b — 5 Granite calls, a few minutes):
    python eval/holdout.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.embeddings.cluster import UNCATEGORIZED_ID, cluster, embed  # noqa: E402
from src.embeddings.profile_extractor import BrandProfileExtractor  # noqa: E402

CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
ARTIFACTS = _PROJECT_ROOT / "eval" / "artifacts"
SPLIT_PATH = ARTIFACTS / "split.json"
TRAIN_CLUSTERS_PATH = ARTIFACTS / "clusters_train.json"
HOLDOUT_PROFILE_PATH = ARTIFACTS / "profile_holdout.json"

N_TEST = 40
N_CLUSTERS = 5
SEED = 20260801

# profile_extractor shows Granite at most this many posts per cluster. Every
# train cluster must retain at least this many, or the holdout profile is built
# on thinner evidence than the shipped one and the comparison is confounded.
MIN_TRAIN_PER_CLUSTER = 12


def voiced_posts(clusters_data: dict) -> list[dict]:
    """Every post carrying caption copy, tagged with its current pillar."""
    out = []
    for cid_str, posts in clusters_data["clusters"].items():
        if int(cid_str) == UNCATEGORIZED_ID:
            continue
        for p in posts:
            if p.get("marketing_hook", "").strip():
                out.append({**p, "orig_cluster": int(cid_str)})
    return out


def allocate_test_counts(sizes: dict[int, int], n_test: int) -> dict[int, int]:
    """
    Proportional allocation, floored so no cluster drops below
    MIN_TRAIN_PER_CLUSTER and no cluster is emptied.
    """
    total = sum(sizes.values())
    capacity = {
        cid: max(0, n - MIN_TRAIN_PER_CLUSTER) if n > MIN_TRAIN_PER_CLUSTER else 0
        for cid, n in sizes.items()
    }
    raw = {cid: n_test * n / total for cid, n in sizes.items()}
    alloc = {cid: min(int(raw[cid]), capacity[cid]) for cid in sizes}

    # Distribute the rounding remainder to whichever clusters still have room,
    # largest fractional part first.
    while sum(alloc.values()) < n_test:
        room = [cid for cid in sizes if alloc[cid] < capacity[cid]]
        if not room:
            break
        pick = max(room, key=lambda c: raw[c] - alloc[c])
        alloc[pick] += 1
    return alloc


def build_split(posts: list[dict], rng: np.random.Generator) -> tuple[list[dict], list[dict]]:
    sizes: dict[int, int] = {}
    for p in posts:
        sizes[p["orig_cluster"]] = sizes.get(p["orig_cluster"], 0) + 1

    alloc = allocate_test_counts(sizes, N_TEST)
    print("── Stratified allocation")
    for cid in sorted(sizes):
        print(f"   pillar {cid}: {sizes[cid]:>3} posts → {alloc[cid]:>2} test, "
              f"{sizes[cid] - alloc[cid]:>3} train")

    test_keys: set[str] = set()
    for cid, k in alloc.items():
        pool = [p for p in posts if p["orig_cluster"] == cid]
        if k:
            picked = rng.choice(len(pool), size=k, replace=False)
            test_keys |= {pool[i]["shortcode"] for i in picked}

    train = [p for p in posts if p["shortcode"] not in test_keys]
    test = [p for p in posts if p["shortcode"] in test_keys]
    return train, test


def refit_on_train(train: list[dict], test: list[dict]) -> tuple[dict, np.ndarray, np.ndarray]:
    """
    Re-fit K-Means on train captions only; assign test posts by nearest centroid.
    Returns (train_clusters_payload, centroids, test_labels).
    """
    train_hooks = [p["marketing_hook"] for p in train]
    test_hooks = [p["marketing_hook"] for p in test]

    print("\n── Re-embedding and re-fitting K-Means on TRAIN only")
    train_vecs = embed(train_hooks)
    labels, centroids = cluster(train_vecs, N_CLUSTERS)

    # embed() L2-normalises, and KMeans centroids of unit vectors are not unit
    # length, so normalise before treating the dot product as cosine.
    unit_centroids = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)
    test_vecs = embed(test_hooks)
    test_labels = (test_vecs @ unit_centroids.T).argmax(axis=1)

    clusters: dict[str, list[dict]] = {str(i): [] for i in range(N_CLUSTERS)}
    for post, label in zip(train, labels):
        clusters[str(int(label))].append({
            "shortcode": post["shortcode"],
            "timestamp_utc": post["timestamp_utc"],
            "marketing_hook": post["marketing_hook"],
            "engagement": post.get("engagement", {}),
        })

    payload = {
        "n_clusters": N_CLUSTERS,
        "cluster_map": {p["shortcode"]: int(l) for p, l in zip(train, labels)},
        "clusters": clusters,
        "centroids": centroids.tolist(),
        "embed_model": "all-MiniLM-L6-v2",
    }
    return payload, centroids, test_labels


def assert_no_leakage(profile: dict, train: list[dict], test: list[dict]) -> None:
    """
    Every term in the holdout profile must be traceable to a TRAIN caption.
    A term found only in test captions means the split leaked.
    """
    train_blob = " || ".join(p["marketing_hook"] for p in train).lower()
    test_blob = " || ".join(p["marketing_hook"] for p in test).lower()

    violations = []
    for entry in profile["cluster_profiles"]:
        vocab = entry["profile"].get("vocabulary_patterns", {})
        for phrase in vocab.get("signature_phrases", []):
            p = phrase.lower()
            if p not in train_blob and p in test_blob:
                violations.append(("signature_phrase", entry["cluster_id"], phrase))
        for word in vocab.get("recurring_words", []):
            pat = re.compile(rf"\b{re.escape(word.lower())}\b")
            if not pat.search(train_blob) and pat.search(test_blob):
                violations.append(("recurring_word", entry["cluster_id"], word))

    if violations:
        for kind, cid, term in violations:
            print(f"   LEAK  cluster {cid}  {kind}: {term!r}")
        raise AssertionError(
            f"{len(violations)} profile term(s) appear only in held-out captions. "
            "The holdout profile saw test data — downstream scores are invalid."
        )
    print(f"   no leakage: every profile term traces to a train caption")


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    clusters_data = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))
    posts = voiced_posts(clusters_data)
    print(f"── {len(posts)} voiced posts (of {sum(len(v) for v in clusters_data['clusters'].values())} total)\n")

    train, test = build_split(posts, rng)
    print(f"\n   train {len(train)} · test {len(test)}")

    payload, centroids, test_labels = refit_on_train(train, test)
    TRAIN_CLUSTERS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    sizes = {c: len(v) for c, v in payload["clusters"].items()}
    print(f"   train pillar sizes after re-fit: {sizes}")

    split = {
        "seed": SEED,
        "n_train": len(train),
        "n_test": len(test),
        "train_shortcodes": [p["shortcode"] for p in train],
        "test": [
            {
                "shortcode": p["shortcode"],
                "timestamp_utc": p["timestamp_utc"],
                "real_caption": p["marketing_hook"],
                "assigned_cluster": int(l),
                "engagement": p.get("engagement", {}),
            }
            for p, l in zip(test, test_labels)
        ],
    }
    SPLIT_PATH.write_text(json.dumps(split, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n── Extracting brand profile from TRAIN clusters only (Granite ×5)")
    extractor = BrandProfileExtractor()
    profile = extractor.build_brand_profile(
        clusters_path=TRAIN_CLUSTERS_PATH,
        output_path=HOLDOUT_PROFILE_PATH,
    )

    print("\n── Leakage check")
    assert_no_leakage(profile, train, test)

    print(f"\nSaved → {SPLIT_PATH.relative_to(_PROJECT_ROOT)}")
    print(f"        {TRAIN_CLUSTERS_PATH.relative_to(_PROJECT_ROOT)}")
    print(f"        {HOLDOUT_PROFILE_PATH.relative_to(_PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
