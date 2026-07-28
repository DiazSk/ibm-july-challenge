"use client";

import type { StrategyScorecard } from "@/lib/types";
import SourceBadge from "./SourceBadge";

function fmt(value: number, unit: string): string {
  if (unit === "%") return `${value}%`;
  return value >= 1000 ? value.toLocaleString() : String(value);
}

/** Headline KPIs reframed on the signals Instagram actually ranks on —
 *  sends-per-reach and saves-per-reach lead, not vanity likes. */
export default function AlgoScorecard({ scorecard }: { scorecard: StrategyScorecard }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {scorecard.metrics.map((m) => (
        <div
          key={m.key}
          className="rounded-xl border p-4 flex flex-col gap-2"
          style={{
            borderColor: m.star ? "var(--color-ql-accent)" : "var(--color-ql-border)",
            background: m.star
              ? "color-mix(in oklch, var(--color-ql-accent) 5%, var(--color-ql-card))"
              : "var(--color-ql-card)",
          }}
        >
          <div className="flex items-center gap-1.5">
            <span
              className="text-[10px] uppercase tracking-[0.1em] font-medium"
              style={{ color: "var(--color-ql-muted)" }}
            >
              {m.label}
            </span>
            {m.star && (
              <span
                className="text-[11px] leading-none shrink-0"
                style={{ color: "var(--color-ql-accent)" }}
                title="#1 reach lever"
              >
                ★
              </span>
            )}
          </div>

          <span
            className="text-2xl leading-none"
            style={{ color: "var(--color-ql-dark)", fontFamily: "var(--font-display)" }}
          >
            {fmt(m.value, m.unit)}
          </span>

          <p className="text-[13px] leading-snug" style={{ color: "var(--color-ql-text)" }}>
            {m.hint}
          </p>

          <div className="mt-auto pt-1">
            <SourceBadge source={m.source} compact />
          </div>
        </div>
      ))}
    </div>
  );
}
