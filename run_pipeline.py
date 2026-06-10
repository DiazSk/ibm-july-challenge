"""
Week 1 pipeline orchestrator — runs all three stages in sequence.

Usage:
    python run_pipeline.py              # all three stages
    python run_pipeline.py --skip-llm  # skip Granite call (pipeline + clustering only)
"""

import argparse
import sys
from pathlib import Path


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
    print("STAGE 3 — Granite Brand Profile Extraction (watsonx.ai)")
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
