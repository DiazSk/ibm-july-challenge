import { getPostSeed } from "@/lib/api";

/**
 * Hand a real post off to the Script Studio.
 *
 * The generator used to open as a blank form: paste a reference caption, then
 * hand-type six metric numbers for a post the app already stores. This fetches
 * those from the account data instead.
 *
 * Writes the same ss_script_* keys the weekly-brief "Develop this" button uses,
 * then the caller navigates. Writing before navigation matters — ScriptStudio
 * reads these during its first render, so a write from a sibling effect after
 * mount would arrive too late.
 */
export type SeedFormat = "Reel" | "Carousel" | "Static";

export async function seedScriptFromPost(shortcode: string, format: SeedFormat = "Reel") {
  const seed = await getPostSeed(shortcode);
  const m = seed.metrics;

  localStorage.setItem("ss_script_caption", JSON.stringify(seed.caption));
  localStorage.setItem(
    "ss_script_metrics",
    JSON.stringify({
      views: m.views ?? 0,
      reach: m.reach ?? 0,
      likes: m.likes ?? 0,
      comments: m.comments ?? 0,
      shares: m.shares ?? 0,
      saves: m.saves ?? 0,
    })
  );
  localStorage.setItem("ss_script_format", JSON.stringify(format));
  localStorage.setItem("ss_script_cluster", JSON.stringify(seed.cluster_id ?? 0));
  localStorage.setItem("ss_script_open", "1");
}
