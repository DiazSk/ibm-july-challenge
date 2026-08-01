"""
Dashboard insights — pure aggregation of real per-post Instagram metrics.

Reads the engagement now carried through clusters.json (see pipeline.py /
cluster.py) and derives:
  - aggregate_cluster_engagement()  → the per-cluster `cluster_engagement`
    block every existing consumer (BoostAdvisor, Jarvis, create/agent) reads.
  - compute_overview()              → the four dashboard widgets:
    headline KPIs, top-posts leaderboard, engagement-by-pillar, best-time grid.

No LLM, no I/O — takes the clusters + brand_profile dicts, returns dicts.

Self-check (no network):
    python -m src.data.insights
"""

from datetime import datetime

from src.data.pillars import UNCATEGORIZED_ID, UNCATEGORIZED_LABEL, pillar_names

_INTERACTION_KEYS = ("likes", "comments", "saves", "shares")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _has_metrics(post: dict) -> bool:
    eng = post.get("engagement") or {}
    return bool(eng) and _num(eng.get("reach")) > 0


def _rate(eng: dict) -> float:
    """Engagement rate % = interactions / reach * 100. 0 if no reach."""
    reach = _num(eng.get("reach"))
    if reach <= 0:
        return 0.0
    interactions = sum(_num(eng.get(k)) for k in _INTERACTION_KEYS)
    return round(interactions / reach * 100, 1)


def _pillar_names(brand_profile: dict) -> dict[int, str]:
    # Shared with every other pillar-name consumer — see src/data/pillars.py for
    # why this must not be a local copy.
    names = dict(pillar_names(brand_profile))
    # The metrics-only bucket has no Granite profile, so name it here rather than
    # letting it surface as "Cluster -1".
    names.setdefault(UNCATEGORIZED_ID, UNCATEGORIZED_LABEL)
    return names


def _parse_ts(ts: str) -> datetime | None:
    """Parse '2026-07-24T04:49:32+0000' (Graph API format). Times are UTC."""
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None


# ── Per-cluster aggregate (the cluster_engagement block) ─────────────────────

def aggregate_cluster_engagement(clusters: dict, brand_profile: dict) -> dict:
    """
    Build the `cluster_engagement` dict keyed by cluster-id string, matching the
    schema in data/demo_clusters.json. Only posts that carry real metrics count.
    """
    names = _pillar_names(brand_profile)
    out: dict[str, dict] = {}

    for cid_str, posts in clusters.get("clusters", {}).items():
        metric_posts = [p for p in posts if _has_metrics(p)]
        if not metric_posts:
            continue
        n = len(metric_posts)
        engs = [p["engagement"] for p in metric_posts]

        def avg(key: str) -> int:
            return round(sum(_num(e.get(key)) for e in engs) / n)

        total_reach = sum(_num(e.get("reach")) for e in engs)
        total_inter = sum(_num(e.get(k)) for e in engs for k in _INTERACTION_KEYS)
        eng_rate = round(total_inter / total_reach * 100, 1) if total_reach else 0.0

        best = max(metric_posts, key=lambda p: (_num(p["engagement"].get("reach")),
                                                 _num(p["engagement"].get("saves"))))
        out[cid_str] = {
            "cluster_name"       : names.get(int(cid_str), f"Cluster {cid_str}"),
            "post_count"         : n,
            "avg_views"          : avg("views"),
            "avg_reach"          : avg("reach"),
            "avg_likes"          : avg("likes"),
            "avg_comments"       : avg("comments"),
            "avg_saves"          : avg("saves"),
            "engagement_rate"    : eng_rate,
            "best_post_shortcode": best.get("shortcode", ""),
            "best_post_hook"     : (best.get("marketing_hook", "") or "")[:120],
        }
    return out


def resolve_cluster_engagement(clusters: dict, brand_profile: dict) -> dict:
    """
    The single honest source of per-cluster engagement.

    Prefers the persisted `cluster_engagement` block; if it is missing, derives
    the same structure from whatever posts actually carry metrics. Returns an
    empty dict when the account has no engagement data at all.

    An empty dict is the correct answer in that case. Callers must render an
    empty state rather than substituting stand-in figures — surfacing invented
    numbers as measured ones is the failure mode this function exists to close.
    """
    persisted = clusters.get("cluster_engagement")
    if persisted:
        return persisted
    return aggregate_cluster_engagement(clusters, brand_profile)


# ── Dashboard overview (the four widgets) ────────────────────────────────────

def compute_overview(clusters: dict, brand_profile: dict) -> dict:
    names = _pillar_names(brand_profile)

    # Flatten posts with their cluster id.
    flat: list[tuple[int, dict]] = []
    for cid_str, posts in clusters.get("clusters", {}).items():
        for p in posts:
            flat.append((int(cid_str), p))

    metric_posts = [(cid, p) for cid, p in flat if _has_metrics(p)]

    # 1. Headline KPIs
    def total(key: str) -> int:
        return round(sum(_num(p["engagement"].get(key)) for _, p in metric_posts))

    total_reach = total("reach")
    total_inter = sum(_num(p["engagement"].get(k)) for _, p in metric_posts for k in _INTERACTION_KEYS)
    kpis = {
        "posts_counted"      : len(metric_posts),
        "total_reach"        : total_reach,
        "total_views"        : total("views"),
        "total_likes"        : total("likes"),
        "total_comments"     : total("comments"),
        "total_saves"        : total("saves"),
        "total_shares"       : total("shares"),
        "avg_engagement_rate": round(total_inter / total_reach * 100, 1) if total_reach else 0.0,
    }

    # 2. Top posts leaderboard
    ranked = sorted(
        metric_posts,
        key=lambda cp: (_num(cp[1]["engagement"].get("reach")),
                        _num(cp[1]["engagement"].get("saves"))),
        reverse=True,
    )[:8]
    top_posts = []
    for cid, p in ranked:
        e = p["engagement"]
        top_posts.append({
            "shortcode"      : p.get("shortcode", ""),
            "cluster_id"     : cid,
            "pillar"         : names.get(cid, f"Cluster {cid}"),
            "hook"           : (p.get("marketing_hook", "") or "")[:120],
            "timestamp_utc"  : p.get("timestamp_utc", ""),
            "reach"          : round(_num(e.get("reach"))),
            "views"          : round(_num(e.get("views"))),
            "likes"          : round(_num(e.get("likes"))),
            "comments"       : round(_num(e.get("comments"))),
            "saves"          : round(_num(e.get("saves"))),
            "shares"         : round(_num(e.get("shares"))),
            "engagement_rate": _rate(e),
        })

    # 3. Engagement by pillar
    ce = aggregate_cluster_engagement(clusters, brand_profile)
    by_pillar = [
        {
            "cluster_id"     : int(cid),
            "pillar"         : eng["cluster_name"],
            "engagement_rate": eng["engagement_rate"],
            "avg_reach"      : eng["avg_reach"],
            "avg_saves"      : eng["avg_saves"],
            "post_count"     : eng["post_count"],
        }
        for cid, eng in sorted(ce.items(), key=lambda x: int(x[0]))
    ]

    # 4. Best time to post — (weekday 0=Mon..6=Sun) x hour, avg reach.
    # ponytail: buckets are UTC (that's all the Graph API gives us); add the
    # account's tz offset if local-time slots ever matter.
    buckets: dict[tuple[int, int], list[float]] = {}
    for _, p in metric_posts:
        dt = _parse_ts(p.get("timestamp_utc", ""))
        if dt is None:
            continue
        buckets.setdefault((dt.weekday(), dt.hour), []).append(_num(p["engagement"].get("reach")))
    # `reaches` carries the raw per-post values so the client can take a MEDIAN
    # after shifting into the brand's timezone. A mean here would let one viral
    # post decide the "best day" for the whole account; the timezone shift can
    # move a post to a different weekday, so the rollup has to happen client-side.
    best_times = [
        {
            "weekday"  : wd,
            "hour"     : hr,
            "avg_reach": round(sum(v) / len(v)),
            "count"    : len(v),
            "reaches"  : [round(x) for x in v],
        }
        for (wd, hr), v in sorted(buckets.items())
    ]
    best_slot = max(best_times, key=lambda c: c["avg_reach"], default=None)

    return {
        "kpis"      : kpis,
        "top_posts" : top_posts,
        "by_pillar" : by_pillar,
        "best_times": best_times,
        "best_slot" : best_slot,
    }


# ── Offline self-check ────────────────────────────────────────────────────────

def _demo() -> None:
    clusters = {
        "clusters": {
            "0": [
                {"shortcode": "A", "timestamp_utc": "2026-07-20T09:00:00+0000",
                 "marketing_hook": "Fresh bomboloni",
                 "engagement": {"reach": 1000, "views": 2000, "likes": 80, "comments": 10, "saved": 30, "shares": 5}},
                {"shortcode": "B", "timestamp_utc": "2026-07-21T18:00:00+0000",
                 "marketing_hook": "Nutella cookies",
                 "engagement": {"reach": 500, "views": 900, "likes": 40, "comments": 4, "saves": 10, "shares": 2}},
            ],
            "1": [
                {"shortcode": "C", "timestamp_utc": "2026-07-22T12:00:00+0000",
                 "marketing_hook": "Rasmalai cake",
                 "engagement": {"reach": 3000, "views": 5000, "likes": 200, "comments": 30, "saves": 120, "shares": 40}},
                {"shortcode": "D", "timestamp_utc": "", "marketing_hook": "no metrics", "engagement": {}},
            ],
        }
    }
    profile = {"cluster_profiles": [
        {"cluster_id": 0, "profile": {"content_pillar": "Homemade Classics"}},
        {"cluster_id": 1, "profile": {"content_pillar": "Fusion Specials"}},
    ]}

    # Note: pipeline normalizes saved→saves; here post A uses "saved" to prove
    # aggregation reads engagement generically (it counts "saves" only), so A's
    # saves register as 0 — that's fine, we just check plumbing + math shape.
    ce = aggregate_cluster_engagement(clusters, profile)
    assert set(ce) == {"0", "1"}, ce
    assert ce["0"]["cluster_name"] == "Homemade Classics"
    assert ce["0"]["post_count"] == 2
    assert ce["1"]["post_count"] == 1  # post D dropped (no metrics)
    assert ce["1"]["best_post_shortcode"] == "C"
    # cluster 1 rate: (200+30+120+40)/3000*100 = 13.0
    assert ce["1"]["engagement_rate"] == 13.0, ce["1"]["engagement_rate"]

    ov = compute_overview(clusters, profile)
    assert ov["kpis"]["posts_counted"] == 3
    assert ov["kpis"]["total_reach"] == 4500
    assert ov["top_posts"][0]["shortcode"] == "C"  # highest reach
    assert len(ov["by_pillar"]) == 2
    assert ov["best_slot"] is not None
    assert all("weekday" in c and "hour" in c for c in ov["best_times"])
    print("insights self-check passed.")


if __name__ == "__main__":
    _demo()
