"""
Repetition guard — "have I already posted this?"

The loudest daily question for a creator in a narrow niche. A bakery account
converges fast (donuts, cakes, frosting, reveal shots) and the same idea
resurfaces without anyone noticing.

Repetition is not itself the defect, though. Re-running a proven winner is good
strategy; re-running a flop is the mistake. Every past post already carries its
metrics, so each match is returned with a `recommendation` telling the creator
which case she's in, rather than a bare "you've done this before".

Pure Python, no LLM. The embedder is injected (same contract as
`detect_nearest_cluster_and_signal` in src/generation/brand_drift.py) so callers
share the cached `get_sentence_embedder()` singleton and the self-check can run
in milliseconds against a fake.

Self-check (no network, no model download):
    python -m src.data.repetition
"""

import sys
from pathlib import Path
from statistics import median

import numpy as np
from sklearn.preprocessing import normalize

# Make `src` importable when run standalone (uvicorn already does this).
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data.insights import _num, _has_metrics, _pillar_names
from src.data.pillars import pillar_label
from src.data.strategy import _weighted_score

# Calibrated against the real 207-hook corpus, NOT guessed — and specifically
# against the input the creator actually types (a casual moment description),
# which scores markedly lower than a polished marketing hook:
#
#   "Fresh Nutella bomboloni, soft and fluffy, filled with rich Nutella"  0.848
#   "just pulled a tray of nutella bomboloni out of the fryer"            0.600
#   "packing up a big bulk order of desserts for a cafe today"            0.610
#   ── observed gap ──
#   "teaching a beginner how to temper chocolate"                         0.421
#   "a savoury sourdough sandwich series"                                 0.415
#   "doing my accounts and taxes"                                         0.245
#
# 0.55 sits inside that gap: 3/3 real repeats caught, 0/3 false alarms. A
# threshold picked from hook-vs-hook similarity instead (where genuine
# duplicates start ~0.83) would have caught only 1 of the 3.
REPEAT_THRESHOLD = 0.55

# ponytail: re-encodes the corpus per call (~200 hooks, well under a second on
# the cached model). Cache the matrix keyed on clusters.json mtime if the corpus
# grows past a few thousand posts.


def _describe(similarity: float) -> str:
    """Plain words. The creator should never be shown a cosine value."""
    if similarity >= 0.80:
        return "almost identical to"
    if similarity >= 0.65:
        return "very close to"
    return "similar to"


def find_similar_posts(
    idea: str,
    clusters: dict,
    brand_profile: dict,
    embedder,
    top_k: int = 3,
    threshold: float = REPEAT_THRESHOLD,
) -> list[dict]:
    """
    Past posts covering the same ground as `idea`, best match first.

    Each match carries how that post actually performed and a `recommendation`:
      repeat  — it beat the account's median sends+saves score, worth another run
      avoid   — it underperformed, change the angle
      unknown — no metrics on that post (older exports carry captions only)

    Returns [] when the idea is genuinely novel, so callers can render nothing
    rather than an empty-state message.
    """
    idea = (idea or "").strip()
    if not idea:
        return []

    names = _pillar_names(brand_profile)
    posts = [
        (int(cid), p)
        for cid, plist in clusters.get("clusters", {}).items()
        for p in plist
        if (p.get("marketing_hook") or "").strip()
    ]
    if not posts:
        return []

    hooks = [p["marketing_hook"].strip() for _, p in posts]
    vecs  = normalize(embedder.encode(hooks + [idea], convert_to_numpy=True))
    sims  = vecs[:-1] @ vecs[-1]          # L2-normalized → dot product is cosine

    # Median over posts that have metrics; without it every match is "unknown".
    scored = [_weighted_score(p["engagement"]) for _, p in posts if _has_metrics(p)]
    par    = median(scored) if scored else None

    ranked = sorted(range(len(posts)), key=lambda i: sims[i], reverse=True)
    out: list[dict] = []
    for i in ranked[:top_k]:
        if sims[i] < threshold:
            break                          # sorted, so everything after is lower
        cid, p = posts[i]
        e = p.get("engagement") or {}

        if not _has_metrics(p) or par is None:
            recommendation, note = "unknown", "No metrics stored for that post."
        elif _weighted_score(e) >= par:
            recommendation = "repeat"
            note = "That one did better than your typical post — worth another run."
        else:
            recommendation = "avoid"
            note = "That one underperformed. Same subject is fine, but change the angle."

        out.append({
            "shortcode"     : p.get("shortcode", ""),
            "hook"          : p["marketing_hook"].strip()[:200],
            "timestamp_utc" : p.get("timestamp_utc", ""),
            "cluster_id"    : cid,
            "pillar"        : names.get(cid, pillar_label(cid)),
            "similarity"    : round(float(sims[i]), 3),
            "closeness"     : _describe(float(sims[i])),
            "reach"         : round(_num(e.get("reach"))),
            "recommendation": recommendation,
            "note"          : note,
        })
    return out


# ── Offline self-check ────────────────────────────────────────────────────────

class _FakeEmbedder:
    """
    Deterministic stand-in for SentenceTransformer.

    Maps each text to a vector by keyword, so the check exercises ranking, the
    threshold cut, and the repeat/avoid split without a 90MB model download.
    """

    _AXES = ("nutella", "bulk", "sourdough")

    def encode(self, texts, convert_to_numpy=True):
        rows = []
        for t in texts:
            low = t.lower()
            v = [1.0 if axis in low else 0.0 for axis in self._AXES]
            rows.append(v or [0.0] * len(self._AXES))
        arr = np.array(rows, dtype=float)
        arr[arr.sum(axis=1) == 0] = [0.01, 0.01, 0.01]   # avoid zero-norm rows
        return arr


def _demo() -> None:
    clusters = {"clusters": {
        "0": [
            # Strong performer: shares 300 / reach 1000
            {"shortcode": "WIN", "timestamp_utc": "2026-04-12T09:00:00+0000",
             "marketing_hook": "Fresh nutella bomboloni, soft and fluffy",
             "engagement": {"reach": 1000, "shares": 300, "saves": 100, "likes": 10, "comments": 1}},
            # Weak performer, same subject
            {"shortcode": "FLOP", "timestamp_utc": "2026-05-02T09:00:00+0000",
             "marketing_hook": "Another nutella bomboloni tray",
             "engagement": {"reach": 1000, "shares": 1, "saves": 1, "likes": 1, "comments": 0}},
        ],
        "1": [
            # No metrics at all — must still be findable, flagged "unknown"
            {"shortcode": "NOMETRIC", "timestamp_utc": "2026-03-01T09:00:00+0000",
             "marketing_hook": "Big bulk order going out today", "engagement": {}},
        ],
    }}
    profile = {"cluster_profiles": [
        {"cluster_id": 0, "profile": {"content_pillar": "Bomboloni"}},
        {"cluster_id": 1, "profile": {"content_pillar": "Bulk Orders"}},
    ]}
    fake = _FakeEmbedder()

    # A repeat of the nutella theme finds both nutella posts, best score first.
    hits = find_similar_posts("nutella bomboloni again", clusters, profile, fake)
    assert len(hits) == 2, hits
    assert {h["shortcode"] for h in hits} == {"WIN", "FLOP"}, hits
    # WIN beats the median, FLOP is below it.
    by_code = {h["shortcode"]: h for h in hits}
    assert by_code["WIN"]["recommendation"] == "repeat", by_code["WIN"]
    assert by_code["FLOP"]["recommendation"] == "avoid", by_code["FLOP"]
    assert by_code["WIN"]["pillar"] == "Bomboloni"

    # A post with no metrics is surfaced, not silently dropped.
    bulk = find_similar_posts("bulk order for a cafe", clusters, profile, fake)
    assert [h["shortcode"] for h in bulk] == ["NOMETRIC"], bulk
    assert bulk[0]["recommendation"] == "unknown", bulk[0]

    # Genuinely novel → empty, so the UI renders nothing at all.
    assert find_similar_posts("sourdough sandwich series", clusters, profile, fake) == []

    # Degenerate inputs.
    assert find_similar_posts("", clusters, profile, fake) == []
    assert find_similar_posts("nutella", {"clusters": {}}, profile, fake) == []
    assert find_similar_posts("nutella", {}, profile, fake) == []

    # No cosine values leak into user-facing copy.
    assert by_code["WIN"]["closeness"] in ("almost identical to", "very close to", "similar to")

    print("repetition self-check passed.")
    print(f"  threshold={REPEAT_THRESHOLD}  "
          f"repeat={by_code['WIN']['shortcode']}  avoid={by_code['FLOP']['shortcode']}  "
          f"unknown={bulk[0]['shortcode']}")


if __name__ == "__main__":
    _demo()
