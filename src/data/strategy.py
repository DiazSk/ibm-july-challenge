"""
Performance-first strategy engine — pure Python, no LLM.

Turns the real per-post Instagram metrics carried in clusters.json into an
algorithm-grounded strategy: an algorithm-weighted scorecard, a clean
performance-over-time series, the account's best/worst post, and a set of
"result-proven moves" that each pair a number from the creator's OWN data with
a real Instagram-ranking principle (labelled by source).

Ranking backbone (Mosseri, Jan 2025): the top signals are watch time,
likes-per-reach, and *sends-per-reach* — the last being the most heavily
weighted driver of new-audience reach. Saves are the next-highest-value signal.
We store `shares` (≈ sends) and `saves` per post, so we rank content by the
metrics the algorithm actually rewards.

Reuses src/data/insights.py for the metric plumbing (_num, _has_metrics,
_pillar_names, _parse_ts, compute_overview).

Self-check (no network):
    python src/data/strategy.py
"""

import sys
from collections import defaultdict
from pathlib import Path

# Make `src` importable when run standalone (uvicorn already does this).
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data.insights import (
    _num, _has_metrics, _pillar_names, _parse_ts, compute_overview,
)

# Sends outrank saves as a reach signal — weight them 3:1 when ranking posts.
_WEIGHT_SENDS = 3.0
_WEIGHT_SAVES = 1.0

_INTERACTION_KEYS = ("likes", "comments", "saves", "shares")


# ── Per-pillar aggregates ─────────────────────────────────────────────────────

def _pillar_aggregates(clusters: dict, brand_profile: dict) -> list[dict]:
    """Per-cluster real-metric rollup with the algorithm rates that drive strategy."""
    names = _pillar_names(brand_profile)
    rows = []
    for cid_str, posts in clusters.get("clusters", {}).items():
        cid = int(cid_str)
        mp = [p for p in posts if _has_metrics(p)]
        if not mp:
            continue
        reach  = sum(_num(p["engagement"].get("reach"))  for p in mp)
        shares = sum(_num(p["engagement"].get("shares")) for p in mp)
        saves  = sum(_num(p["engagement"].get("saves"))  for p in mp)
        inter  = sum(_num(p["engagement"].get(k)) for p in mp for k in _INTERACTION_KEYS)
        r = reach or 1
        rows.append({
            "cluster_id"     : cid,
            "pillar"         : names.get(cid, f"Cluster {cid}"),
            "post_count"     : len(mp),
            "reach"          : round(reach),
            "sends_per_reach": round(shares / r * 100, 2),
            "saves_per_reach": round(saves / r * 100, 2),
            "engagement_rate": round(inter / r * 100, 1),
        })

    total = sum(row["post_count"] for row in rows) or 1
    for row in rows:
        row["volume_pct"] = round(row["post_count"] / total * 100, 1)
    return sorted(rows, key=lambda r: r["cluster_id"])


# ── Scorecard ─────────────────────────────────────────────────────────────────

def compute_algo_scorecard(clusters: dict, brand_profile: dict) -> dict:
    """Headline KPIs reframed on the signals Instagram actually ranks on."""
    k = compute_overview(clusters, brand_profile)["kpis"]
    r = k["total_reach"] or 1
    metrics = [
        {"key": "sends_per_reach", "label": "Sends per reach",
         "value": round(k["total_shares"] / r * 100, 2), "unit": "%", "star": True,
         "hint": "Instagram's most heavily weighted driver of new-audience reach.",
         "source": "official"},
        {"key": "saves_per_reach", "label": "Saves per reach",
         "value": round(k["total_saves"] / r * 100, 2), "unit": "%", "star": False,
         "hint": "A save marks lasting value — the next-highest signal after sends.",
         "source": "official"},
        {"key": "engagement_rate", "label": "Engagement rate",
         "value": k["avg_engagement_rate"], "unit": "%", "star": False,
         "hint": "All interactions ÷ reach across your posts.",
         "source": "your-data"},
        {"key": "reach", "label": "Total reach",
         "value": k["total_reach"], "unit": "", "star": False,
         "hint": f"Across {k['posts_counted']} posts with metrics.",
         "source": "your-data"},
    ]
    return {
        "metrics"      : metrics,
        "posts_counted": k["posts_counted"],
        "by_pillar"    : _pillar_aggregates(clusters, brand_profile),
    }


# ── Performance-over-time (one clean line, all metrics for client toggle) ─────

def monthly_timeseries(clusters: dict, brand_profile: dict) -> list[dict]:
    """month → {sends_per_reach, saves_per_reach, reach, post_count, top_pillar}."""
    names = _pillar_names(brand_profile)
    monthly: dict[str, dict] = defaultdict(
        lambda: {"reach": 0.0, "shares": 0.0, "saves": 0.0, "n": 0,
                 "pillar_reach": defaultdict(float)}
    )
    for cid_str, posts in clusters.get("clusters", {}).items():
        cid = int(cid_str)
        for p in posts:
            if not _has_metrics(p) or _parse_ts(p.get("timestamp_utc", "")) is None:
                continue
            m = p["timestamp_utc"][:7]
            e = p["engagement"]
            b = monthly[m]
            b["reach"]  += _num(e.get("reach"))
            b["shares"] += _num(e.get("shares"))
            b["saves"]  += _num(e.get("saves"))
            b["n"]      += 1
            b["pillar_reach"][cid] += _num(e.get("reach"))

    series = []
    for m in sorted(monthly):
        b = monthly[m]
        r = b["reach"] or 1
        top = max(b["pillar_reach"], key=b["pillar_reach"].get) if b["pillar_reach"] else None
        series.append({
            "month"          : m,
            "sends_per_reach": round(b["shares"] / r * 100, 2),
            "saves_per_reach": round(b["saves"] / r * 100, 2),
            "reach"          : round(b["reach"]),
            "post_count"     : b["n"],
            "top_pillar"     : names.get(top, f"Cluster {top}") if top is not None else "",
            "top_pillar_id"  : top,
        })
    return series


# ── Best / worst post by algorithm-weighted score ────────────────────────────

def _weighted_score(e: dict) -> float:
    r = _num(e.get("reach")) or 1
    return (_num(e.get("shares")) / r) * _WEIGHT_SENDS + (_num(e.get("saves")) / r) * _WEIGHT_SAVES


def _pack_post(cid: int, p: dict, pillar: str) -> dict:
    e = p["engagement"]
    r = _num(e.get("reach")) or 1
    return {
        "shortcode"      : p.get("shortcode", ""),
        "cluster_id"     : cid,
        "pillar"         : pillar,
        "hook"           : (p.get("marketing_hook", "") or "")[:200],
        "timestamp_utc"  : p.get("timestamp_utc", ""),
        "reach"          : round(_num(e.get("reach"))),
        "views"          : round(_num(e.get("views"))),
        "likes"          : round(_num(e.get("likes"))),
        "comments"       : round(_num(e.get("comments"))),
        "saves"          : round(_num(e.get("saves"))),
        "shares"         : round(_num(e.get("shares"))),
        "sends_per_reach": round(_num(e.get("shares")) / r * 100, 2),
        "saves_per_reach": round(_num(e.get("saves")) / r * 100, 2),
        "engagement_rate": round(sum(_num(e.get(k)) for k in _INTERACTION_KEYS) / r * 100, 1),
    }


def rank_posts(clusters: dict, brand_profile: dict) -> dict:
    """
    Returns {winner, loser}. Both are drawn from posts that earned real reach —
    a floor filters out low-reach posts whose per-reach rates are noise (1 share
    on 20 reach = 5%). The loser is a post that DID reach people but failed to
    convert to sends/saves — the instructive failure, not the smallest post.
    """
    names = _pillar_names(brand_profile)
    flat = [(int(cid), p) for cid, posts in clusters.get("clusters", {}).items()
            for p in posts if _has_metrics(p)]
    if not flat:
        return {"winner": None, "loser": None}

    avg_reach = sum(_num(p["engagement"].get("reach")) for _, p in flat) / len(flat)
    floor = max(100.0, 0.15 * avg_reach)
    # Need real reach AND a stored hook — a post with no caption text can't be
    # meaningfully diagnosed by the Why Engine.
    cand = [(cid, p) for cid, p in flat
            if _num(p["engagement"].get("reach")) >= floor and (p.get("marketing_hook") or "").strip()]
    if len(cand) < 2:
        cand = [(cid, p) for cid, p in flat if (p.get("marketing_hook") or "").strip()] or flat

    ranked = sorted(cand, key=lambda cp: _weighted_score(cp[1]["engagement"]), reverse=True)
    win_cid, win_p = ranked[0]
    lose_cid, lose_p = ranked[-1]
    return {
        "winner": _pack_post(win_cid, win_p, names.get(win_cid, f"Cluster {win_cid}")),
        "loser" : _pack_post(lose_cid, lose_p, names.get(lose_cid, f"Cluster {lose_cid}")),
    }


# ── Result-proven moves (data pattern × sourced algorithm principle) ─────────

def derive_moves(by_pillar: list[dict], ranked: dict) -> list[dict]:
    """Deterministic strategy cards. Each pairs the creator's own number with a
    labelled Instagram-ranking principle. No LLM — instant and always grounded."""
    moves: list[dict] = []
    pillars = [p for p in by_pillar if p["post_count"] >= 2] or by_pillar
    fair_share = 100 / max(len(by_pillar), 1)  # even volume split across pillars

    if pillars:
        rd = max(pillars, key=lambda p: p["sends_per_reach"])
        under_posted = rd["volume_pct"] < fair_share
        moves.append({
            "title"    : f"Double down on {rd['pillar']}",
            "stat"     : f"{rd['sends_per_reach']}% sends-per-reach — your highest",
            "detail"   : ("It's your strongest reach engine"
                          + (" and you under-post it. " if under_posted else ". ")
                          + "End each post with a reason to DM it to a friend."),
            "principle": "Sends-per-reach is Instagram's most heavily weighted driver of "
                         "new-audience reach (Mosseri, 2025).",
            "source"   : "official",
            "lever"    : "sends",
        })

        sd = max(pillars, key=lambda p: p["saves_per_reach"])
        moves.append({
            "title"    : f"Turn {sd['pillar']} into 'save this' content",
            "stat"     : f"{sd['saves_per_reach']}% saves-per-reach — your highest",
            "detail"   : "Package these as carousels or how-tos people save to return to.",
            "principle": "Saves are the next-highest-value signal after sends — they mark "
                         "lasting, returnable value.",
            "source"   : "official",
            "lever"    : "saves",
        })

        vol_pillars = [p for p in pillars if p["volume_pct"] >= fair_share]
        if vol_pillars:
            wk = min(vol_pillars, key=lambda p: p["sends_per_reach"])
            if wk["cluster_id"] != rd["cluster_id"]:
                moves.append({
                    "title"    : f"Rework or scale back {wk['pillar']}",
                    "stat"     : f"{wk['volume_pct']}% of posts, only {wk['sends_per_reach']}% sends-per-reach",
                    "detail"   : "You invest here often but it rarely gets sent onward. Rework "
                                 "the hook, or reallocate the slots to your reach-driver.",
                    "principle": "Reach follows share-worthiness per view, not post volume.",
                    "source"   : "your-data",
                    "lever"    : "sends",
                })

    w = ranked.get("winner")
    if w:
        moves.append({
            "title"    : "Build a repeatable series from your top post",
            "stat"     : f"Winner: {w['sends_per_reach']}% sends-per-reach in {w['pillar']}",
            "detail"   : f"Hook: “{w['hook'][:90]}”. Reuse this exact format on a fixed "
                         "cadence so it becomes a recognizable series.",
            "principle": "Recurring, recognizable formats compound repeat viewers over "
                         "~6–12 weeks.",
            "source"   : "industry-study",
            "lever"    : "consistency",
        })
    return moves


# ── Offline self-check ────────────────────────────────────────────────────────

def _demo() -> None:
    clusters = {"clusters": {
        # Cluster 0 — high reach, but weak sends/saves (the instructive loser lives here)
        "0": [
            {"shortcode": "A", "timestamp_utc": "2026-05-02T09:00:00+0000",
             "marketing_hook": "Chocolate cake, DM to order",
             "engagement": {"reach": 4000, "views": 4200, "likes": 60, "comments": 2, "saves": 8, "shares": 3}},
            {"shortcode": "B", "timestamp_utc": "2026-06-11T18:00:00+0000",
             "marketing_hook": "Fresh donuts today",
             "engagement": {"reach": 2000, "views": 2100, "likes": 30, "comments": 1, "saves": 4, "shares": 1}},
        ],
        # Cluster 1 — lower volume, high sends-per-reach (the reach-driver + winner)
        "1": [
            {"shortcode": "C", "timestamp_utc": "2026-07-22T12:00:00+0000",
             "marketing_hook": "one bite of rasmalai cake & all diet plans got cancelled",
             "engagement": {"reach": 3000, "views": 5000, "likes": 200, "comments": 30, "saves": 180, "shares": 160}},
            {"shortcode": "C2", "timestamp_utc": "2026-04-05T12:00:00+0000",
             "marketing_hook": "the fusion box everyone's DMing about",
             "engagement": {"reach": 2000, "views": 3200, "likes": 130, "comments": 20, "saves": 120, "shares": 100}},
        ],
    }}
    profile = {"brand_name": "Test Bakery", "cluster_profiles": [
        {"cluster_id": 0, "post_count": 2, "profile": {"content_pillar": "Homemade Classics"}},
        {"cluster_id": 1, "post_count": 2, "profile": {"content_pillar": "Fusion Specials"}},
    ]}

    sc = compute_algo_scorecard(clusters, profile)
    m = {x["key"]: x for x in sc["metrics"]}
    # sends-per-reach = total_shares/total_reach = 264 / 11000 * 100 = 2.40
    assert abs(m["sends_per_reach"]["value"] - 2.40) < 0.05, m["sends_per_reach"]["value"]
    assert m["sends_per_reach"]["star"] is True
    assert len(sc["by_pillar"]) == 2

    ts = monthly_timeseries(clusters, profile)
    assert [r["month"] for r in ts] == ["2026-04", "2026-05", "2026-06", "2026-07"], ts
    assert ts[-1]["top_pillar"] == "Fusion Specials"  # cluster 1 drove July reach

    ranked = rank_posts(clusters, profile)
    assert ranked["winner"]["shortcode"] == "C", ranked["winner"]  # best sends/saves rate
    assert ranked["loser"]["shortcode"] == "B", ranked["loser"]    # real reach, weakest sends+saves
    assert ranked["winner"]["sends_per_reach"] == 5.33

    moves = derive_moves(sc["by_pillar"], ranked)
    titles = " | ".join(x["title"] for x in moves)
    assert any("Fusion Specials" in x["title"] for x in moves), titles  # reach-driver
    assert any(x["source"] == "official" for x in moves)
    assert any(x["lever"] == "consistency" for x in moves)  # series from winner
    assert all({"title", "stat", "detail", "principle", "source"} <= set(x) for x in moves)

    print("strategy self-check passed.")
    print(f"  sends/reach={m['sends_per_reach']['value']}%  winner={ranked['winner']['shortcode']}  "
          f"loser={ranked['loser']['shortcode']}  moves={len(moves)}")


if __name__ == "__main__":
    _demo()
