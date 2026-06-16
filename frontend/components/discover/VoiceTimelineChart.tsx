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
  { key: "C0", color: "#5A8A6A" },
  { key: "C1", color: "#8B7355" },
  { key: "C2", color: "#A35A5A" },
  { key: "C3", color: "#5A6A8A" },
  { key: "C4", color: "#6A5A8A" },
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
          tick={{ fontSize: 10, fill: "#7A6F63" }}
          tickLine={false}
          axisLine={{ stroke: "#E0DAD3" }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: 10, fill: "#7A6F63" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#fff",
            border: "1px solid #E0DAD3",
            borderRadius: 8,
            fontSize: 11,
            color: "#3D3D3D",
          }}
          formatter={(v) => [`${Number(v).toFixed(1)}%`]}
        />
        <Legend
          iconType="circle"
          iconSize={6}
          wrapperStyle={{ fontSize: 11, color: "#7A6F63" }}
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
