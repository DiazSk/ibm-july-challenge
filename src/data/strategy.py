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
from datetime import datetime, timedelta
from pathlib import Path

# Make `src` importable when run standalone (uvicorn already does this).
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data.insights import (
    _num, _has_metrics, _pillar_names, _parse_ts, compute_overview,
)
from src.data.pillars import pillar_label

# Sends outrank saves as a reach signal — weight them 3:1 when ranking posts.
_WEIGHT_SENDS = 3.0
_WEIGHT_SAVES = 1.0

# A pillar carrying at least this share of total reach is never labelled "scale back".
_REACH_SHARE_PROTECT = 0.25

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


# ── Per-pillar movement ──────────────────────────────────────────────────────

# Below this many posts in a window, a "multiple" is noise rather than a trend.
_MIN_WINDOW_POSTS = 3
# How far a pillar has to move before it counts as rising/cooling rather than steady.
_MOVE_THRESHOLD   = 1.25


def pillar_velocity(clusters: dict, brand_profile: dict, window_days: int = 60) -> list[dict]:
    """
    What is actually gaining or losing ground in this account.

    Compares each pillar's trailing `window_days` against the equally-sized window
    before it. Ranked by how far sends-per-reach moved, falling back to reach when
    the account records no shares at all.

    `monthly_timeseries` can't answer this — it aggregates per month and keeps only
    the single top pillar, so a pillar that is quietly accelerating never surfaces.

    Small windows are reported as "steady" rather than as a dramatic multiple: one
    viral post already distorted the best-day metric once, and a 1-post window would
    do the same here.
    """
    names = _pillar_names(brand_profile)

    stamped: list[tuple[int, datetime, dict]] = []
    for cid_str, posts in clusters.get("clusters", {}).items():
        for p in posts:
            ts = _parse_ts(p.get("timestamp_utc", ""))
            if ts is None or not _has_metrics(p):
                continue
            stamped.append((int(cid_str), ts, p["engagement"]))

    if not stamped:
        return []

    # Anchor on the newest post, not on "now" — a demo dataset may be months old and
    # anchoring on today would report every pillar as empty.
    latest = max(ts for _, ts, _ in stamped)
    recent_start = latest - timedelta(days=window_days)
    prior_start  = latest - timedelta(days=window_days * 2)

    def agg(rows: list[dict]) -> dict:
        reach  = sum(_num(e.get("reach")) for e in rows)
        shares = sum(_num(e.get("shares")) for e in rows)
        saves  = sum(_num(e.get("saves")) for e in rows)
        return {
            "posts"          : len(rows),
            "reach"          : round(reach),
            "sends_per_reach": round(shares / reach * 100, 2) if reach else 0.0,
            "saves_per_reach": round(saves / reach * 100, 2) if reach else 0.0,
        }

    out: list[dict] = []
    for cid in sorted({c for c, _, _ in stamped}):
        recent = agg([e for c, ts, e in stamped if c == cid and ts >= recent_start])
        prior  = agg([e for c, ts, e in stamped if c == cid and prior_start <= ts < recent_start])

        # Prefer sends-per-reach; some accounts record no shares at all, and then
        # raw reach is the only movement signal available.
        key = "sends_per_reach" if (recent["sends_per_reach"] or prior["sends_per_reach"]) else "reach"
        r_val, p_val = recent[key], prior[key]

        thin = recent["posts"] < _MIN_WINDOW_POSTS or prior["posts"] < _MIN_WINDOW_POSTS
        if thin or not p_val:
            direction, multiple = "steady", None
        else:
            multiple  = round(r_val / p_val, 2)
            direction = ("rising"  if multiple >= _MOVE_THRESHOLD else
                         "cooling" if multiple <= 1 / _MOVE_THRESHOLD else "steady")

        out.append({
            "cluster_id" : cid,
            "pillar"     : names.get(cid, pillar_label(cid)),
            "direction"  : direction,
            "metric"     : key,
            "multiple"   : multiple,
            "recent"     : recent,
            "prior"      : prior,
            "post_count" : recent["posts"] + prior["posts"],
        })

    # Biggest movers first; steady pillars sink to the bottom.
    out.sort(key=lambda d: abs((d["multiple"] or 1) - 1), reverse=True)
    return out


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
            "source"    : "official",
            "lever"     : "sends",
            "cluster_id": rd["cluster_id"],
        })

        sd = max(pillars, key=lambda p: p["saves_per_reach"])
        moves.append({
            "title"    : f"Turn {sd['pillar']} into 'save this' content",
            "stat"     : f"{sd['saves_per_reach']}% saves-per-reach — your highest",
            "detail"   : "Package these as carousels or how-tos people save to return to.",
            "principle": "Saves are the next-highest-value signal after sends — they mark "
                         "lasting, returnable value.",
            "source"    : "official",
            "lever"     : "saves",
            "cluster_id": sd["cluster_id"],
        })

        # Never advise scaling back a pillar that is actually carrying the account.
        # Per-reach ratios punish breakout posts — a viral reel earns enormous
        # reach but proportionally fewer shares, so the pillar holding the
        # account's biggest hit can read as its weakest on sends-per-reach alone.
        # Without this guard the page told a bakery to scale back the pillar
        # containing her 5.2M-reach reel.
        total_reach = sum(p.get("reach", 0) for p in by_pillar) or 1
        vol_pillars = [
            p for p in pillars
            if p["volume_pct"] >= fair_share
            and p.get("reach", 0) / total_reach < _REACH_SHARE_PROTECT
        ]
        if vol_pillars:
            wk = min(vol_pillars, key=lambda p: p["sends_per_reach"])
            if wk["cluster_id"] != rd["cluster_id"]:
                moves.append({
                    "title"    : f"Rework or scale back {wk['pillar']}",
                    "stat"     : f"{wk['volume_pct']}% of posts, only {wk['sends_per_reach']}% sends-per-reach",
                    "detail"   : "You invest here often but it rarely gets sent onward. Rework "
                                 "the hook, or reallocate the slots to your reach-driver.",
                    "principle": "Reach follows share-worthiness per view, not post volume.",
                    "source"    : "your-data",
                    "lever"     : "sends",
                    "cluster_id": wk["cluster_id"],
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
            "source"    : "industry-study",
            "lever"     : "consistency",
            "cluster_id": w["cluster_id"],
        })
    return moves


def best_post_in_pillar(clusters: dict, brand_profile: dict, cluster_id: int) -> dict | None:
    """
    Top algorithm-weighted post inside one pillar — the reference to build from
    when a move says "double down on X". `rank_posts` answers the account-wide
    question; this answers the per-pillar one, so the script the Today page hands
    off is drawn from the same pillar the recommendation names.

    Falls back to the account-wide winner when the pillar has no usable post.
    """
    names = _pillar_names(brand_profile)
    cand = [
        p for p in clusters.get("clusters", {}).get(str(cluster_id), [])
        if _has_metrics(p) and (p.get("marketing_hook") or "").strip()
    ]
    if not cand:
        return rank_posts(clusters, brand_profile).get("winner")
    best = max(cand, key=lambda p: _weighted_score(p["engagement"]))
    return _pack_post(cluster_id, best, names.get(cluster_id, f"Cluster {cluster_id}"))


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
    # Every move must carry a resolvable pillar — the Today page seeds its script
    # from move.cluster_id, so a missing/unknown id breaks the hand-off silently.
    known = {p["cluster_id"] for p in sc["by_pillar"]}
    assert all(x.get("cluster_id") in known for x in moves), moves

    # ── best_post_in_pillar ──────────────────────────────────────────────────
    # Pillar-scoped, so it must pick C2 inside cluster 1 — not the account-wide
    # winner C, and not anything from cluster 0.
    assert best_post_in_pillar(clusters, profile, 1)["shortcode"] == "C", "cluster 1 top"
    assert best_post_in_pillar(clusters, profile, 0)["shortcode"] == "A", "cluster 0 top"
    # Unknown pillar falls back to the account-wide winner rather than returning None.
    assert best_post_in_pillar(clusters, profile, 99)["shortcode"] == "C"

    # ── pillar_velocity ──────────────────────────────────────────────────────
    # Cluster 0 cools (sends/reach halves), cluster 1 rises (roughly doubles),
    # cluster 2 has a single post per window and must stay "steady" rather than
    # reporting a dramatic multiple off n=1.
    def _posts(cid_ts_shares):
        return [
            {"shortcode": f"{cid}{i}", "timestamp_utc": ts, "marketing_hook": "x",
             "engagement": {"reach": 1000, "views": 1000, "likes": 1,
                            "comments": 0, "saves": 10, "shares": sh}}
            for i, (cid, ts, sh) in enumerate(cid_ts_shares)
        ]

    recent, prior = "2026-07-10T09:00:00+0000", "2026-05-10T09:00:00+0000"
    vclusters = {"clusters": {
        "0": _posts([(0, prior, 40)] * 3 + [(0, recent, 20)] * 3),   # halves  → cooling
        "1": _posts([(1, prior, 20)] * 3 + [(1, recent, 40)] * 3),   # doubles → rising
        "2": _posts([(2, prior, 10), (2, recent, 90)]),              # n=1/window → steady
    }}
    vprofile = {"cluster_profiles": [
        {"cluster_id": 0, "profile": {"content_pillar": "Cooling Pillar"}},
        {"cluster_id": 1, "profile": {"content_pillar": "Rising Pillar"}},
        {"cluster_id": 2, "profile": {"content_pillar": "Tiny Pillar"}},
    ]}
    vel = {v["cluster_id"]: v for v in pillar_velocity(vclusters, vprofile, window_days=45)}
    assert vel[0]["direction"] == "cooling", vel[0]
    assert vel[1]["direction"] == "rising", vel[1]
    assert vel[2]["direction"] == "steady", vel[2]   # not "rising" off one post
    assert vel[2]["multiple"] is None, vel[2]
    assert vel[1]["pillar"] == "Rising Pillar", vel[1]
    assert pillar_velocity({"clusters": {}}, vprofile) == []

    print("strategy self-check passed.")
    print(f"  sends/reach={m['sends_per_reach']['value']}%  winner={ranked['winner']['shortcode']}  "
          f"loser={ranked['loser']['shortcode']}  moves={len(moves)}  "
          f"velocity={ {v['pillar']: v['direction'] for v in vel.values()} }")


if __name__ == "__main__":
    _demo()
