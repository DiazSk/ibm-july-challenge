"""
Score the held-out caption set on signals that have ground truth.

The shipped Drift Test (src/generation/voice_fidelity.py) awards points for
reusing vocabulary the generation prompt already injected, so a brand-blind
baseline structurally scores 0 and the comparison proves nothing. These three
signals are graded against the account's real captions instead:

  centroid proximity   cosine to the pillar centre, in the same MiniLM space the
                       pillars were built in. Real held-out captions establish
                       the reference band; generated captions land in it or not.

  authorship AUC       a logistic-regression discriminator is fitted on TRAIN
                       real captions vs. baseline-generated ones, then asked to
                       score the held-out real / stylesync / baseline captions.
                       Reported as: how often does the discriminator rank a
                       generated caption as more authentic than the real caption
                       it was written to replace? 0.5 means indistinguishable.

  distributional match length, emoji rate, hashtag count, sentence count against
                       the real distribution. Catches the obvious tells.

The headline is the STYLESYNC MINUS BASELINE gap on authorship AUC, with a
bootstrap CI over the held-out items. If that interval straddles zero, brand
grounding is not doing measurable work.

The legacy Drift Test is computed alongside, on the same captions, purely so the
two metrics can be compared.

Run (after eval/generate.py):
    python eval/score.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

from src.embeddings.cluster import embed  # noqa: E402
from src.generation.voice_fidelity import score_voice_fidelity  # noqa: E402

ARTIFACTS = _PROJECT_ROOT / "eval" / "artifacts"
SPLIT_PATH = ARTIFACTS / "split.json"
TRAIN_CLUSTERS_PATH = ARTIFACTS / "clusters_train.json"
HOLDOUT_PROFILE_PATH = ARTIFACTS / "profile_holdout.json"
CAPTIONS_PATH = ARTIFACTS / "captions.json"
REPORT_PATH = ARTIFACTS / "score_report.json"

N_BOOTSTRAP = 5000
SEED = 20260801

ARMS = ("real", "stylesync", "baseline")

_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿]"
)


# ── Surface features ─────────────────────────────────────────────────────────

def surface_features(text: str) -> dict:
    return {
        "chars": len(text),
        "words": len(text.split()),
        "emoji": len(_EMOJI.findall(text)),
        "hashtags": len(re.findall(r"#\w+", text)),
        "sentences": len([s for s in re.split(r"[.!?\n]+", text) if s.strip()]),
    }


def summarise(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    return {"mean": round(float(a.mean()), 2), "median": round(float(np.median(a)), 2)}


# ── Bootstrap ────────────────────────────────────────────────────────────────

def bootstrap_ci(
    paired: np.ndarray, rng: np.random.Generator, n: int = N_BOOTSTRAP
) -> tuple[float, float]:
    """Percentile CI for the mean of a paired per-item difference."""
    idx = rng.integers(0, len(paired), size=(n, len(paired)))
    means = paired[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    rng = np.random.default_rng(SEED)

    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    train_data = json.loads(TRAIN_CLUSTERS_PATH.read_text(encoding="utf-8"))
    profile = json.loads(HOLDOUT_PROFILE_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CAPTIONS_PATH.read_text(encoding="utf-8"))

    items = [
        v for v in cache.values()
        if v["stylesync"].strip() and v["baseline"].strip() and v["real"].strip()
    ]
    dropped = len(cache) - len(items)
    print(f"── {len(items)} scorable held-out items"
          + (f" ({dropped} dropped for empty generations)" if dropped else ""))

    centroids = np.asarray(train_data["centroids"], dtype=float)
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)

    train_real = [
        p["marketing_hook"]
        for posts in train_data["clusters"].values()
        for p in posts
    ]

    # ── Embed everything once ────────────────────────────────────────────────
    print("── Embedding captions")
    texts = {arm: [it[arm] for it in items] for arm in ARMS}
    vecs = {arm: embed(texts[arm]) for arm in ARMS}
    train_vecs = embed(train_real)

    # ── 1. Centroid proximity ────────────────────────────────────────────────
    cids = np.array([it["assigned_cluster"] for it in items])
    prox = {
        arm: np.einsum("ij,ij->i", vecs[arm], centroids[cids]) for arm in ARMS
    }

    # ── 2. Authorship discrimination ─────────────────────────────────────────
    # Fitted only on TRAIN real captions vs. held-out baseline captions, so the
    # held-out real and stylesync captions are both unseen at fit time.
    X = np.vstack([train_vecs, vecs["baseline"]])
    y = np.r_[np.ones(len(train_vecs)), np.zeros(len(vecs["baseline"]))]
    clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(X, y)

    authenticity = {arm: clf.predict_proba(vecs[arm])[:, 1] for arm in ARMS}

    # Sanity: the discriminator must separate train-real from baseline. If it
    # cannot, the embedding space carries no authorship signal and every number
    # below is noise.
    fit_auc = roc_auc_score(y, clf.predict_proba(X)[:, 1])

    # Held-out separability: real vs. each generated arm.
    def held_out_auc(arm: str) -> float:
        yy = np.r_[np.ones(len(items)), np.zeros(len(items))]
        ss = np.r_[authenticity["real"], authenticity[arm]]
        return float(roc_auc_score(yy, ss))

    auc_vs_stylesync = held_out_auc("stylesync")
    auc_vs_baseline = held_out_auc("baseline")

    # Paired per-item difference — the headline.
    paired = authenticity["stylesync"] - authenticity["baseline"]
    lo, hi = bootstrap_ci(paired, rng)

    # ── 3. Legacy Drift Test, same captions ──────────────────────────────────
    by_cluster = {c["cluster_id"]: c["profile"] for c in profile["cluster_profiles"]}
    legacy = {arm: [] for arm in ARMS}
    for it in items:
        prof = by_cluster.get(it["assigned_cluster"]) or next(iter(by_cluster.values()))
        for arm in ARMS:
            legacy[arm].append(
                score_voice_fidelity(
                    it[arm],
                    prof.get("vocabulary_patterns", {}),
                    prof.get("avoided_terms", []),
                )["score"]
            )

    # ── 4. Surface features ──────────────────────────────────────────────────
    feats = {
        arm: {
            k: summarise([surface_features(t)[k] for t in texts[arm]])
            for k in ("chars", "words", "emoji", "hashtags", "sentences")
        }
        for arm in ARMS
    }

    # ── Report ───────────────────────────────────────────────────────────────
    report = {
        "n_items": len(items),
        "discriminator_fit_auc": round(fit_auc, 4),
        "centroid_proximity": {arm: summarise(prox[arm].tolist()) for arm in ARMS},
        "authenticity_score": {arm: summarise(authenticity[arm].tolist()) for arm in ARMS},
        "held_out_auc_real_vs": {
            "stylesync": round(auc_vs_stylesync, 4),
            "baseline": round(auc_vs_baseline, 4),
        },
        "headline_paired_gap": {
            "mean": round(float(paired.mean()), 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "excludes_zero": bool(lo > 0 or hi < 0),
        },
        "legacy_drift_test": {arm: summarise(legacy[arm]) for arm in ARMS},
        "surface_features": feats,
    }

    print(f"\n── Discriminator sanity: train-real vs baseline AUC = {fit_auc:.3f}")
    if fit_auc < 0.75:
        print("   WARNING: weak separation — authorship numbers below are unreliable.")

    print("\n── Centroid proximity (cosine to assigned pillar centre)")
    for arm in ARMS:
        print(f"   {arm:<10} mean {report['centroid_proximity'][arm]['mean']:.2f}")

    print("\n── Authenticity (P(written by the account)), 1.0 = most authentic")
    for arm in ARMS:
        print(f"   {arm:<10} mean {report['authenticity_score'][arm]['mean']:.2f}")

    print("\n── Held-out AUC, real vs generated (0.5 = indistinguishable)")
    print(f"   real vs stylesync  {auc_vs_stylesync:.3f}")
    print(f"   real vs baseline   {auc_vs_baseline:.3f}")

    g = report["headline_paired_gap"]
    print(f"\n── HEADLINE  stylesync − baseline authenticity, paired over n={len(items)}")
    print(f"   mean {g['mean']:+.4f}   95% CI [{g['ci95'][0]:+.4f}, {g['ci95'][1]:+.4f}]")
    print(f"   {'CI excludes zero — measurable effect'if g['excludes_zero'] else 'CI straddles zero — no measurable effect'}")

    print("\n── Legacy Drift Test on the same captions (for comparison)")
    for arm in ARMS:
        print(f"   {arm:<10} mean {report['legacy_drift_test'][arm]['mean']:.1f}/100")

    print("\n── Surface features (mean)")
    hdr = f"   {'':<10}" + "".join(f"{k:>11}" for k in ("chars", "words", "emoji", "hashtags", "sentences"))
    print(hdr)
    for arm in ARMS:
        row = "".join(f"{feats[arm][k]['mean']:>11.1f}"
                      for k in ("chars", "words", "emoji", "hashtags", "sentences"))
        print(f"   {arm:<10}{row}")

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved → {REPORT_PATH.relative_to(_PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
