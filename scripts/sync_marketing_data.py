"""
Regenerate frontend/lib/marketing-data.ts from the real dataset.

The marketing site previously carried a hand-maintained copy of these figures
with a comment asserting it was "kept in sync with the live product". It was
not: it claimed 113 posts against an actual 217, and pillar engagement rates of
4.6-11.1% against actual rates of 0.5-1.1%. Hand-maintained numbers that claim
to be derived numbers will drift again, so derive them.

Everything below is read from data/clusters.json and data/brand_profile.json.
The illustrative prose samples stay hand-written and are labelled as such.

Run after any re-ingest or re-cluster:
    python scripts/sync_marketing_data.py
"""

import json
import subprocess
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLUSTERS_PATH = _PROJECT_ROOT / "data" / "clusters.json"
PROFILE_PATH = _PROJECT_ROOT / "data" / "brand_profile.json"
OUT_PATH = _PROJECT_ROOT / "frontend" / "lib" / "marketing-data.ts"

UNCATEGORIZED_ID = -1


def count_granite_call_sites() -> int:
    """Files that instantiate an Ollama model — the honest definition of a call site."""
    res = subprocess.run(
        ["grep", "-rl", "-e", "OllamaLLM(", "-e", "ChatOllama(", "src", "api"],
        cwd=_PROJECT_ROOT, capture_output=True, text=True,
    )
    return len([l for l in res.stdout.splitlines() if l.strip()])


def main() -> None:
    clusters = json.loads(CLUSTERS_PATH.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    engagement = clusters.get("cluster_engagement", {})

    posts_total = sum(len(v) for v in clusters["clusters"].values())
    posts_voiced = sum(
        1 for v in clusters["clusters"].values()
        for p in v if p.get("marketing_hook", "").strip()
    )

    pillars = []
    for entry in profile["cluster_profiles"]:
        cid = entry["cluster_id"]
        if cid == UNCATEGORIZED_ID:
            continue
        eng = engagement.get(str(cid), {})
        pillars.append({
            "id": f"C{cid}",
            "name": entry["profile"].get("content_pillar", f"Cluster {cid}"),
            "avgEngagement": eng.get("engagement_rate", 0.0),
            "postCount": eng.get("post_count", 0),
            "color": f"var(--color-cluster-{cid})",
        })
    pillars.sort(key=lambda p: p["avgEngagement"], reverse=True)

    pillar_lines = ",\n".join(
        f'  {{ id: "{p["id"]}", name: {json.dumps(p["name"])}, '
        f'avgEngagement: {p["avgEngagement"]}, postCount: {p["postCount"]}, '
        f'color: "{p["color"]}" }}'
        for p in pillars
    )

    ts = f"""\
// GENERATED FILE — do not edit by hand.
// Regenerate with: python scripts/sync_marketing_data.py
//
// Figures below are read directly from data/clusters.json and
// data/brand_profile.json. Last generated {date.today().isoformat()}.
//
// engagementRate is interactions/reach for posts carrying real Graph API
// metrics. These are genuine small-account numbers — do not "improve" them.

export const demoBrand = {{
  handle: {json.dumps(profile.get("ig_handle", ""))},
  niche: {json.dumps(profile.get("brand_bio", ""))},
  postsAnalyzed: {posts_total},
  postsWithCaptions: {posts_voiced},
  pillarCount: {len(pillars)},
  graniteCallSites: {count_granite_call_sites()},
}};

export const demoPillars = [
{pillar_lines},
] as const;

// Illustrative, hand-written. Not output from a live run — shown as an example
// of the format, not as a measured result.
export const demoCaptionSample = {{
  caption:
    "Pistachio Rose Bomboloni, fresh out of the fryer. Friday nights taste like this now.",
  pillar: {json.dumps(pillars[0]["name"] if pillars else "")},
}};

// What Granite is used for, by surface. A descriptive list, not a count —
// the authoritative number is demoBrand.graniteCallSites above, which is
// derived. Previously this list was numbered "#1..#14" and read as exhaustive
// while the real call-site count was different.
export const graniteInvocations: [string, string][] = [
  ["Brand voice", "Voice profile extraction"],
  ["Create", "Caption and script generation"],
  ["Create", "Image direction"],
  ["Diagnose", "Why Engine diagnosis"],
  ["Diagnose", "Recovery brief"],
  ["Strategy", "Voice timeline"],
  ["Strategy", "Strategic insights"],
  ["Strategy", "Boost advisor"],
  ["Today", "Moment analysis"],
  ["Today", "Creative directions"],
  ["Brand voice", "Voice refinement"],
  ["Agents", "JARVIS agent"],
  ["Agents", "Inspiration synthesis"],
];

// Illustrative, hand-written. See note above.
export const demoDiagnosisSample = {{
  verdict: "Underperformed",
  postCaption: "New croissant flavor today, come try it!",
  diagnosis:
    "The opening line states the product without a sensory anchor \\u2014 no texture, smell, or moment. Your top posts always open on a sense, not an announcement.",
  brandGap:
    "Signature vocabulary is missing. This reads like an announcement, not a post from this account.",
}};
"""

    OUT_PATH.write_text(ts, encoding="utf-8")
    print(f"posts {posts_total} ({posts_voiced} with captions) · "
          f"{len(pillars)} pillars · {count_granite_call_sites()} Granite call sites")
    for p in pillars:
        print(f"   {p['id']}  {p['name']:<32} {p['avgEngagement']}%  ({p['postCount']} posts)")
    print(f"\nWrote → {OUT_PATH.relative_to(_PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
