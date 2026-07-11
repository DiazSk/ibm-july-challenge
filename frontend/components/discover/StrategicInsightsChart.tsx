"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { ClusterScore } from "@/lib/types";

interface Props {
  scores: ClusterScore[];
}

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

export default function StrategicInsightsChart({ scores }: Props) {
  const data = scores.map((s) => ({
    name: s.pillar.split(" ")[0],
    pillar: s.pillar,
    Volume: s.volume_score,
    Richness: s.richness_score_display,
    cluster_id: s.cluster_id,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart
        data={data}
        margin={{ top: 4, right: 8, left: -24, bottom: 0 }}
        barCategoryGap="30%"
        barGap={2}
      >
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: "var(--color-ql-muted)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--color-ql-border)" }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "var(--color-ql-muted)" }}
          tickLine={false}
          axisLine={false}
          domain={[0, 5]}
          ticks={[1, 2, 3, 4, 5]}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-ql-card)",
            border: "1px solid var(--color-ql-border)",
            borderRadius: 8,
            fontSize: 11,
            color: "var(--color-ql-text)",
          }}
          formatter={(v, name) => [`${v} / 5`, name]}
          labelFormatter={(label, payload) => {
            const d = (payload?.[0] as { payload?: { pillar?: string } } | undefined)?.payload;
            return d?.pillar ?? String(label);
          }}
        />
        <Legend
          iconType="square"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, color: "var(--color-ql-muted)" }}
        />

        <Bar dataKey="Volume" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.cluster_id}
              fill={CLUSTER_COLORS[d.cluster_id] ?? "var(--color-cluster-1)"}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
        <Bar dataKey="Richness" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.cluster_id}
              fill={CLUSTER_COLORS[d.cluster_id] ?? "var(--color-cluster-1)"}
              fillOpacity={0.35}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
