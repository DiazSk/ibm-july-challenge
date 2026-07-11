// Illustrative content for the public marketing site.
// Numbers here are the real @hot_cakesbakes demo dataset (see PROJECT-BRAIN.md §7),
// not fabricated — kept in sync with the live product so marketing copy never
// contradicts what the studio actually shows.

export const demoBrand = {
  handle: "@hot_cakesbakes",
  niche: "Artisanal bakery, Navi Mumbai",
  postsAnalyzed: 113,
  pillarCount: 5,
  graniteInvocations: 14,
};

export const demoPillars = [
  { id: "C1", name: "Artisan Techniques", avgEngagement: 7.8, color: "var(--color-cluster-1)" },
  { id: "C4", name: "Bomboloni", avgEngagement: 11.1, color: "var(--color-cluster-4)" },
  { id: "C2", name: "Seasonal Specials", avgEngagement: 6.2, color: "var(--color-cluster-2)" },
  { id: "C3", name: "Behind the Scenes", avgEngagement: 5.1, color: "var(--color-cluster-3)" },
  { id: "C0", name: "Homemade Classics", avgEngagement: 4.6, color: "var(--color-cluster-0)" },
] as const;

export const demoCaptionSample = {
  caption:
    "Pistachio Rose Bomboloni, fresh out of the fryer. Friday nights taste like this now.",
  pillar: "Bomboloni",
};

export const demoDiagnosisSample = {
  verdict: "Underperformed",
  postCaption: "New croissant flavor today, come try it!",
  diagnosis:
    "The opening line states the product without a sensory anchor — no texture, smell, or moment. Your top posts (Bomboloni cluster) always open on a sense, not an announcement.",
  brandGap:
    "Signature vocabulary like \"laminate,\" \"fold,\" and \"first bite\" is missing. This reads like an announcement, not a HotCakes Bakes post.",
};

// Real 14 Granite invocations (PROJECT-BRAIN.md §5)
export const graniteInvocations: [string, string][] = [
  ["Granite #1", "Brand voice extraction"],
  ["Granite #2", "Caption generation"],
  ["Granite #3", "Image direction"],
  ["Granite #4", "Why Engine diagnosis"],
  ["Granite #5", "Voice timeline"],
  ["Granite #6", "Moment analysis"],
  ["Granite #7", "Creative directions"],
  ["Granite #8", "Strategic insights"],
  ["Granite #9", "Script generation"],
  ["Granite #10", "Recovery brief"],
  ["Granite #11", "Boost advisor"],
  ["Granite #12", "Voice refinement"],
  ["Granite #13", "JARVIS agent"],
  ["Granite #14", "Inspiration synthesis"],
];
