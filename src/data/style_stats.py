"""
Per-pillar structural statistics, measured from the account's own posts.

The caption prompt used to hardcode "stay under 150 words" and "use a maximum
of 5 hashtags". Measured against @hot_cakesbakes those instructions are wrong by
a wide margin — the account's median caption is 29 words and it uses no hashtags
at all — and they override the extracted voice profile, so generated captions
came out 2.2x too long with hashtags the brand never uses.

These numbers replace the guesses. Medians, not means: caption length is
right-skewed and one long post should not move the target.

Run standalone (self-check):
    python src/data/style_stats.py
"""

import re
import statistics

_HASHTAG = re.compile(r"#\w+")
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)
_SENTENCE_SPLIT = re.compile(r"[.!?\n]+")

# Below this many captions a median is noise; the caller should fall back to
# whole-account stats rather than trusting a two-post pillar.
MIN_POSTS_FOR_PILLAR_STATS = 5


def caption_shape(text: str) -> dict:
    return {
        "words": len(text.split()),
        "hashtags": len(_HASHTAG.findall(text)),
        "emoji": len(_EMOJI.findall(text)),
        "sentences": len([s for s in _SENTENCE_SPLIT.split(text) if s.strip()]),
    }


def _median_shape(captions: list[str]) -> dict:
    shapes = [caption_shape(c) for c in captions]
    return {
        k: int(statistics.median([s[k] for s in shapes]))
        for k in ("words", "hashtags", "emoji", "sentences")
    }


def compute_pillar_style(clusters: dict, cluster_id: int) -> dict:
    """
    Median caption shape for one pillar, falling back to the whole account when
    the pillar is too small to measure.
    """
    by_cluster = clusters.get("clusters", {})
    own = [
        p["marketing_hook"]
        for p in by_cluster.get(str(cluster_id), [])
        if p.get("marketing_hook", "").strip()
    ]
    if len(own) >= MIN_POSTS_FOR_PILLAR_STATS:
        return {**_median_shape(own), "n_posts": len(own), "scope": "pillar"}

    everything = [
        p["marketing_hook"]
        for posts in by_cluster.values()
        for p in posts
        if p.get("marketing_hook", "").strip()
    ]
    if not everything:
        return {}
    return {**_median_shape(everything), "n_posts": len(everything), "scope": "account"}


def render_style_constraints(style: dict) -> str:
    """
    The prompt fragment. Returns "" when there are no stats, so the caller keeps
    whatever default it had rather than asserting a made-up target.
    """
    if not style:
        return ""

    words = max(8, style["words"])
    # Allow some headroom above the median without licensing a 150-word essay.
    ceiling = int(round(words * 1.4))

    if style["hashtags"] == 0:
        hashtag_rule = (
            "- Use NO hashtags. This account does not use them, and adding any "
            "is an immediate tell that the caption was not written by them"
        )
    else:
        hashtag_rule = (
            f"- Use about {style['hashtags']} hashtags, matching this account's habit"
        )

    return (
        f"Measured from this account's own {style['n_posts']} posts "
        f"({style['scope']}-level) — match these, they are not suggestions:\n"
        f"- Target about {words} words, and never exceed {ceiling}\n"
        f"{hashtag_rule}\n"
        f"- Around {style['emoji']} emoji and about {style['sentences']} sentences\n"
    )


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    clusters = json.loads((root / "data" / "clusters.json").read_text(encoding="utf-8"))

    for cid in range(5):
        st = compute_pillar_style(clusters, cid)
        print(f"cluster {cid}: {st}")

    account = compute_pillar_style(clusters, 999)  # forces the account fallback
    assert account["scope"] == "account", "small pillars must fall back to account stats"
    assert account["words"] > 0
    print(f"\naccount fallback: {account}")

    tiny = compute_pillar_style(clusters, 0)
    print(f"\ncluster 0 has 2 posts → scope={tiny['scope']} (must be 'account')")
    assert tiny["scope"] == "account"

    print("\n" + render_style_constraints(account))
    assert render_style_constraints({}) == "", "empty stats must yield no constraint text"
    print("OK — style stats measured, small pillars fall back, empty is safe.")
