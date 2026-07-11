"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { MonthlyPct } from "@/lib/types";

interface Props {
  data: MonthlyPct[];
  pillarLabels?: Record<string, string>;
}

const CLUSTERS = [
  { key: "C0", color: "var(--color-cluster-0)" },
  { key: "C1", color: "var(--color-cluster-1)" },
  { key: "C2", color: "var(--color-cluster-2)" },
  { key: "C3", color: "var(--color-cluster-3)" },
  { key: "C4", color: "var(--color-cluster-4)" },
] as const;

export default function VoiceTimelineChart({ data, pillarLabels = {} }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart
        data={data}
        margin={{ top: 4, right: 8, left: -24, bottom: 0 }}
      >
        <defs>
          {CLUSTERS.map(({ key, color }) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>

        <XAxis
          dataKey="month"
          tick={{ fontSize: 10, fill: "var(--color-ql-muted)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--color-ql-border)" }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: 10, fill: "var(--color-ql-muted)" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-ql-card)",
            border: "1px solid var(--color-ql-border)",
            borderRadius: 8,
            fontSize: 11,
            color: "var(--color-ql-text)",
          }}
          formatter={(v) => [`${Number(v).toFixed(1)}%`]}
        />
        <Legend
          iconType="circle"
          iconSize={6}
          wrapperStyle={{ fontSize: 11, color: "var(--color-ql-muted)" }}
        />

        {CLUSTERS.map(({ key, color }) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            name={pillarLabels[key] ?? key}
            stackId="1"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#grad-${key})`}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
