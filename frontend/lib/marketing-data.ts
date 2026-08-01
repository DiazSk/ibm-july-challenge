// GENERATED FILE — do not edit by hand.
// Regenerate with: python scripts/sync_marketing_data.py
//
// Figures below are read directly from data/clusters.json and
// data/brand_profile.json. Last generated 2026-08-01.
//
// engagementRate is interactions/reach for posts carrying real Graph API
// metrics. These are genuine small-account numbers — do not "improve" them.

export const demoBrand = {
  handle: "@hot_cakesbakes",
  niche: "Hot Cakesbakes \u2014 Instagram creator analyzed by StyleSync.",
  postsAnalyzed: 217,
  postsWithCaptions: 208,
  pillarCount: 5,
  graniteCallSites: 23,
};

export const demoPillars = [
  { id: "C2", name: "Premium Cake Creations", avgEngagement: 1.1, postCount: 64, color: "var(--color-cluster-2)" },
  { id: "C4", name: "Personalized Pastry Gifts", avgEngagement: 1.1, postCount: 27, color: "var(--color-cluster-4)" },
  { id: "C0", name: "Golden Delights", avgEngagement: 0.9, postCount: 2, color: "var(--color-cluster-0)" },
  { id: "C1", name: "Bulk Dessert Orders", avgEngagement: 0.9, postCount: 16, color: "var(--color-cluster-1)" },
  { id: "C3", name: "Bomboloni Indulgence", avgEngagement: 0.5, postCount: 95, color: "var(--color-cluster-3)" },
] as const;

// Illustrative, hand-written. Not output from a live run — shown as an example
// of the format, not as a measured result.
export const demoCaptionSample = {
  caption:
    "Pistachio Rose Bomboloni, fresh out of the fryer. Friday nights taste like this now.",
  pillar: "Premium Cake Creations",
};

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
export const demoDiagnosisSample = {
  verdict: "Underperformed",
  postCaption: "New croissant flavor today, come try it!",
  diagnosis:
    "The opening line states the product without a sensory anchor \u2014 no texture, smell, or moment. Your top posts always open on a sense, not an announcement.",
  brandGap:
    "Signature vocabulary is missing. This reads like an announcement, not a post from this account.",
};
