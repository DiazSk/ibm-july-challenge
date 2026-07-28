"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Dot,
} from "recharts";
import type { TimelinePoint } from "@/lib/types";

type MetricKey = "sends_per_reach" | "saves_per_reach" | "reach";

const METRICS: Record<MetricKey, { label: string; unit: string }> = {
  sends_per_reach: { label: "Sends / reach", unit: "%" },
  saves_per_reach: { label: "Saves / reach", unit: "%" },
  reach:           { label: "Reach",         unit: "" },
};

function CustomTooltip({ active, payload }: {
  active?: boolean;
  payload?: { payload: TimelinePoint }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div
      className="rounded-lg px-3 py-2 text-[11px]"
      style={{
        background: "var(--color-ql-card)",
        border: "1px solid var(--color-ql-border)",
        color: "var(--color-ql-text)",
      }}
    >
      <p className="font-medium" style={{ color: "var(--color-ql-dark)" }}>{p.month}</p>
      <p>Sends/reach: {p.sends_per_reach}%</p>
      <p>Saves/reach: {p.saves_per_reach}%</p>
      <p>Reach: {p.reach.toLocaleString()}</p>
      <p style={{ color: "var(--color-ql-muted)" }}>
        {p.post_count} post{p.post_count === 1 ? "" : "s"}
        {p.top_pillar ? ` · led by ${p.top_pillar}` : ""}
      </p>
    </div>
  );
}

/** One clean line, not five stacked bands. Toggle the metric; best month is
 *  marked green, weakest red, so "what worked when" reads at a glance. */
export default function PerformanceTimeline({ data }: { data: TimelinePoint[] }) {
  const [metric, setMetric] = useState<MetricKey>("sends_per_reach");
  const cfg = METRICS[metric];

  const values = data.map((d) => d[metric]);
  const maxV = Math.max(...values);
  const minV = Math.min(...values);

  return (
    <div className="flex flex-col gap-3">
      {/* Metric toggle */}
      <div className="flex gap-1.5">
        {(Object.keys(METRICS) as MetricKey[]).map((k) => {
          const active = k === metric;
          return (
            <button
              key={k}
              onClick={() => setMetric(k)}
              className="text-[11px] px-2.5 py-1 rounded-full transition-colors"
              style={{
                color: active ? "var(--color-ql-card)" : "var(--color-ql-muted)",
                background: active ? "var(--color-ql-accent)" : "transparent",
                border: `1px solid ${active ? "var(--color-ql-accent)" : "var(--color-ql-border)"}`,
              }}
            >
              {METRICS[k].label}
            </button>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="month"
            tickFormatter={(m: string) => m.slice(5)}
            tick={{ fontSize: 10, fill: "var(--color-ql-muted)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--color-ql-border)" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--color-ql-muted)" }}
            tickLine={false}
            axisLine={false}
            unit={cfg.unit}
            width={48}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "var(--color-ql-border)" }} />
          <Line
            type="monotone"
            dataKey={metric}
            stroke="var(--color-ql-accent)"
            strokeWidth={2}
            dot={(props: { cx?: number; cy?: number; payload: TimelinePoint; index: number }) => {
              const v = props.payload[metric];
              const isBest = v === maxV && maxV !== minV;
              const isWorst = v === minV && maxV !== minV;
              const color = isBest
                ? "var(--color-verdict-succeeded)"
                : isWorst
                ? "var(--color-verdict-failed)"
                : "var(--color-ql-accent)";
              return (
                <Dot
                  key={props.index}
                  cx={props.cx}
                  cy={props.cy}
                  r={isBest || isWorst ? 5 : 3}
                  fill={color}
                  stroke="var(--color-ql-card)"
                  strokeWidth={1.5}
                />
              );
            }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex gap-4 text-[10px]" style={{ color: "var(--color-ql-muted)" }}>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-verdict-succeeded)" }} />
          Best month
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-verdict-failed)" }} />
          Weakest month
        </span>
      </div>
    </div>
  );
}
