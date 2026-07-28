import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

/**
 * Colour for a content pillar. Cluster -1 is the metrics-only bucket (posts with
 * engagement but no caption) and has no pillar colour of its own.
 *
 * Do not inline `CLUSTER_COLORS[id % 5]`: in JavaScript `-1 % 5 === -1`, which
 * indexes to `undefined` and silently renders a colourless bar.
 */
export function clusterColor(clusterId: number, fallback = "var(--color-ql-muted)"): string {
  if (!Number.isInteger(clusterId) || clusterId < 0) return fallback;
  return CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length];
}

/**
 * Split a free-text advice string into bullets.
 *
 * Granite returns "2-3 concrete changes" as one prose string, so we split on
 * real list delimiters and fall back to sentence boundaries. Hyphens are NOT
 * delimiters — treating them as such shredded "behind-the-scenes" into three
 * bullets ("…behind" / "the" / "scenes look at the baking process.").
 */
export function splitAdvice(text: string): string[] {
  const clean = (parts: string[]) => parts.map((s) => s.trim()).filter(Boolean);

  const byDelimiter = clean((text ?? "").split(/[\n•–—]+/));
  if (byDelimiter.length > 1) return byDelimiter;

  return clean((byDelimiter[0] ?? "").split(/(?<=\.)\s+(?=[A-Z])/));
}
