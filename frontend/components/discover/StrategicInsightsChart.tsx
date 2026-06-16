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

const CLUSTER_COLORS = ["#5A8A6A", "#8B7355", "#A35A5A", "#5A6A8A", "#6A5A8A"] as const;

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
          tick={{ fontSize: 10, fill: "#7A6F63" }}
          tickLine={false}
          axisLine={{ stroke: "#E0DAD3" }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#7A6F63" }}
          tickLine={false}
          axisLine={false}
          domain={[0, 5]}
          ticks={[1, 2, 3, 4, 5]}
        />
        <Tooltip
          contentStyle={{
            background: "#fff",
            border: "1px solid #E0DAD3",
            borderRadius: 8,
            fontSize: 11,
            color: "#3D3D3D",
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
          wrapperStyle={{ fontSize: 11, color: "#7A6F63" }}
        />

        <Bar dataKey="Volume" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.cluster_id}
              fill={CLUSTER_COLORS[d.cluster_id] ?? "#8B7355"}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
        <Bar dataKey="Richness" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.cluster_id}
              fill={CLUSTER_COLORS[d.cluster_id] ?? "#8B7355"}
              fillOpacity={0.35}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
