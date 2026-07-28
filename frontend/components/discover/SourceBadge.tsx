"use client";

import type { StrategySource } from "@/lib/types";

const META: Record<StrategySource, { label: string; short: string; color: string }> = {
  "official"       : { label: "Instagram official", short: "Instagram", color: "var(--color-ql-accent)" },
  "your-data"      : { label: "Your data",          short: "Your data", color: "var(--color-verdict-succeeded)" },
  "industry-study" : { label: "Industry study",     short: "Study",     color: "var(--color-ql-muted)" },
};

/** Honest provenance label — is this move backed by Instagram, your own numbers,
 *  or a third-party study? `compact` uses a shorter label for narrow tiles. */
export default function SourceBadge({ source, compact = false }: { source: StrategySource; compact?: boolean }) {
  const m = META[source] ?? META["your-data"];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.06em] whitespace-nowrap"
      style={{
        color: m.color,
        background: `color-mix(in oklch, ${m.color} 10%, transparent)`,
        border: `1px solid color-mix(in oklch, ${m.color} 30%, transparent)`,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: m.color }} />
      {compact ? m.short : m.label}
    </span>
  );
}
