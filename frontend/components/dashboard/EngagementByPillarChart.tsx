"use client";

import type { PillarEngagement } from "@/lib/types";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

// Horizontal bars, not a Recharts column chart: pillar names run 2-4 words and
// a categorical x-axis had to truncate them to the first word, which collapsed
// "Custom Cakes & Bulk Orders" and "Custom Cakes & Desserts" into two bars both
// labelled "Custom". Full names, ranked, same bar idiom as Content Pillars.
export default function EngagementByPillarChart({ data }: { data: PillarEngagement[] }) {
  const rows = [...data].sort((a, b) => b.engagement_rate - a.engagement_rate);
  const max = rows.reduce((m, d) => Math.max(m, d.engagement_rate), 0) || 1;

  if (rows.length === 0) {
    return (
      <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
        No engagement data yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {rows.map((d) => (
        <div key={d.cluster_id}>
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <span className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>
              {d.pillar}
            </span>
            <span className="text-[11px] shrink-0 tabular-nums" style={{ color: "var(--color-ql-muted)" }}>
              {d.engagement_rate}% · {d.post_count} posts
            </span>
          </div>
          <div
            className="h-1.5 rounded-full overflow-hidden"
            style={{ background: "var(--color-ql-gap)" }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${(d.engagement_rate / max) * 100}%`,
                background: CLUSTER_COLORS[d.cluster_id % CLUSTER_COLORS.length],
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
