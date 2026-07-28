"""
Single source of truth for content-pillar display names.

Pillar names are produced by Granite and live in brand_profile.json under
cluster_profiles[].profile.content_pillar. Six modules used to each carry their
own hardcoded {cluster_id: label} dict instead; all six had drifted to a set of
names ("Homemade Classics", "Fusion Specials", "Behind the Scenes", …) that
appear in no dataset the project ships, so every one of them mislabelled the
dashboard and, worse, fed wrong pillar names into Granite prompts.

Read the profile instead. Cached because it's on hot request paths; the cache is
cleared on re-sync via onboard._clear_caches, same as the other derived caches.

Self-check (no network):
    python -m src.data.pillars
"""

import json
from functools import lru_cache
from pathlib import Path

_PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "brand_profile.json"


def pillar_names(brand_profile: dict) -> dict[int, str]:
    """{cluster_id: content_pillar} from an already-loaded profile dict."""
    out: dict[int, str] = {}
    for cp in brand_profile.get("cluster_profiles", []):
        cid  = cp.get("cluster_id")
        name = (cp.get("profile") or {}).get("content_pillar")
        if cid is not None and name:
            out[int(cid)] = name
    return out


@lru_cache(maxsize=1)
def _cached_names() -> dict[int, str]:
    if not _PROFILE_PATH.exists():
        return {}
    try:
        return pillar_names(json.loads(_PROFILE_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return {}


# Posts with real metrics but no caption copy. They have no voice to profile, so
# they never get a Granite-generated pillar name — but they do appear in analytics.
UNCATEGORIZED_ID    = -1
UNCATEGORIZED_LABEL = "Uncategorized"


def pillar_label(cluster_id: int) -> str:
    """Display name for one cluster; 'Cluster N' when the profile has no name."""
    if cluster_id == UNCATEGORIZED_ID:
        return UNCATEGORIZED_LABEL
    return _cached_names().get(cluster_id, f"Cluster {cluster_id}")


def all_pillar_labels() -> dict[int, str]:
    """Every known {cluster_id: label}. Copy, so callers can't poison the cache."""
    return dict(_cached_names())


def clear_cache() -> None:
    _cached_names.cache_clear()


# ── Offline self-check ────────────────────────────────────────────────────────

def _demo() -> None:
    profile = {"cluster_profiles": [
        {"cluster_id": 0, "profile": {"content_pillar": "Nutella Series"}},
        {"cluster_id": 1, "profile": {"content_pillar": "Bomboloni"}},
        {"cluster_id": 2, "profile": {"parse_error": True}},      # no name → skipped
        {"cluster_id": 3, "profile": None},                        # null profile → skipped
        {"cluster_id": "4", "profile": {"content_pillar": "Custom Cakes"}},  # str id → int
    ]}
    names = pillar_names(profile)
    assert names == {0: "Nutella Series", 1: "Bomboloni", 4: "Custom Cakes"}, names
    assert pillar_names({}) == {}

    # The real profile should be readable and complete.
    real = all_pillar_labels()
    assert real, "brand_profile.json produced no pillar names"
    assert all(not v.startswith("Cluster ") for v in real.values()), real
    print(f"pillars self-check passed — {len(real)} pillars: {list(real.values())}")


if __name__ == "__main__":
    _demo()
