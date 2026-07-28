"""Pipeline orchestrator — runs all three stages in sequence.

Usage:
    python run_pipeline.py              # all three stages
    python run_pipeline.py --skip-llm  # skip Granite call (pipeline + clustering only)

Programmatic use (from onboarding API):
    from run_pipeline import run_full_pipeline
    run_full_pipeline(brand_name="My Bakery", handle="@mybakery")
"""

import argparse
import sys
from pathlib import Path


def run_full_pipeline(
    brand_name  : str = "HotCakes Bakes",
    handle      : str = "@hot_cakesbakes",
    progress_cb = None,
) -> dict:
    """
    Run all three pipeline stages programmatically.

    Stages:
      1. src/data/pipeline.py     — clean captions, split hook/logistics
      2. src/embeddings/cluster.py — embed + K-Means cluster
      3. src/embeddings/profile_extractor.py — Granite brand voice extraction

    progress_cb(pct: int, message: str) is called at each stage boundary.
    Returns the final brand_profile dict.
    Raises RuntimeError if no posts are found after Stage 1.
    """
    if progress_cb:
        progress_cb(30, "Processing captions...")

    from src.data.pipeline import run_pipeline
    records = run_pipeline()
    if not records:
        raise RuntimeError(
            "No posts with usable captions found. "
            "Check that scraped_dataset/ contains post files."
        )

    if progress_cb:
        progress_cb(50, "Clustering your content...")

    from src.embeddings.cluster import run_clustering
    run_clustering()

    if progress_cb:
        progress_cb(65, "IBM Granite is building your brand voice...")

    from src.embeddings.profile_extractor import BrandProfileExtractor
    ig_handle = handle if handle.startswith("@") else f"@{handle}"
    brand_bio = f"{brand_name} — Instagram creator analyzed by StyleSync."
    extractor = BrandProfileExtractor(
        brand_name=brand_name,
        ig_handle=ig_handle,
        brand_bio=brand_bio,
    )
    profile = extractor.build_brand_profile()

    # Enrich clusters.json with a real per-cluster engagement block derived from
    # the ingested metrics. Every consumer (BoostAdvisor, Jarvis, create/agent,
    # the insights dashboard) reads clusters["cluster_engagement"] — populating
    # it here replaces the synthetic fallback with real numbers.
    import json
    from pathlib import Path
    from src.data.insights import aggregate_cluster_engagement

    root          = Path(__file__).resolve().parent
    clusters_path = root / "data" / "clusters.json"
    try:
        clusters = json.loads(clusters_path.read_text(encoding="utf-8"))
        clusters["cluster_engagement"] = aggregate_cluster_engagement(clusters, profile)
        clusters_path.write_text(json.dumps(clusters, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — engagement is additive; never fail the build
        print(f"cluster_engagement enrichment skipped: {exc}")

    if progress_cb:
        progress_cb(100, "Done!")

    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="StyleSync Week 1 pipeline")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Run pipeline and clustering only, skip Granite brand profile extraction",
    )
    args = parser.parse_args()

    # ── Stage 1: Data pipeline ─────────────────────────────────────────────
    print("=" * 60)
    print("STAGE 1 — Data Ingestion & Normalization")
    print("=" * 60)
    from src.data.pipeline import run_pipeline
    records = run_pipeline()
    if not records:
        sys.exit("No records produced by pipeline. Check scraped_dataset/.")
    print()

    # ── Stage 2: Clustering ────────────────────────────────────────────────
    print("=" * 60)
    print("STAGE 2 — Content Clustering (MiniLM-L6-v2 + K-Means)")
    print("=" * 60)
    from src.embeddings.cluster import run_clustering
    cluster_output = run_clustering()
    print()

    # ── Stage 3: Granite brand profile ────────────────────────────────────
    if args.skip_llm:
        print("Skipping Stage 3 (--skip-llm flag set).")
        print("Run 'python src/embeddings/profile_extractor.py' when ready.")
        return

    print("=" * 60)
    print("STAGE 3 — Granite Brand Profile Extraction (local Ollama)")
    print("=" * 60)

    from src.embeddings.profile_extractor import BrandProfileExtractor
    extractor = BrandProfileExtractor()
    profile   = extractor.build_brand_profile()
    print()
    print("=" * 60)
    print(f"Week 1 complete.  Brand profile → data/brand_profile.json")
    print(f"Content pillars found: {profile['n_clusters']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
