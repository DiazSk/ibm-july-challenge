"use client";

import { Info } from "lucide-react";
import type { DriftSide, DriftCompareResult, VoiceMatchLabel } from "@/lib/types";

const LABEL_COLOR: Record<VoiceMatchLabel, string> = {
  "closely matches": "var(--color-verdict-succeeded)",
  "some drift": "var(--color-verdict-underperformed)",
  "significant drift": "var(--color-verdict-failed)",
};

function Chip({ text, color }: { text: string; color: string }) {
  return (
    <span
      className="text-[10px] leading-none px-1.5 py-1 rounded-full whitespace-nowrap"
      style={{ background: `color-mix(in oklch, ${color} 16%, transparent)`, color }}
    >
      {text}
    </span>
  );
}

function SideCard({ title, side, winner }: { title: string; side: DriftSide; winner: boolean }) {
  const color = LABEL_COLOR[side.match_label];
  return (
    <div
      className="rounded-xl border p-4 flex flex-col"
      style={{
        borderColor: winner ? color : "var(--color-ql-border)",
        background: winner ? `color-mix(in oklch, ${color} 6%, transparent)` : "var(--color-ql-card)",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium uppercase tracking-[0.1em]" style={{ color: "var(--color-ql-muted)" }}>
          {title}
        </span>
        <span className="text-[10px] uppercase tracking-[0.06em]" style={{ color: "var(--color-ql-muted)" }}>
          {side.topical_label}
        </span>
      </div>

      {/* Hero metric */}
      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-3xl font-semibold tabular-nums" style={{ color }}>
          {side.score}
        </span>
        <span className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
          / 100 voice match
        </span>
      </div>
      <p className="text-[12px] font-medium mb-3" style={{ color }}>
        {side.match_label}
      </p>

      <p className="text-sm leading-relaxed mb-3 whitespace-pre-wrap" style={{ color: "var(--color-ql-dark)" }}>
        {side.caption}
      </p>

      <div className="mt-auto flex flex-col gap-1.5">
        {side.matched_phrases.length > 0 && (
          <div className="flex flex-wrap gap-1 items-center">
            <span className="text-[10px]" style={{ color: "var(--color-ql-muted)" }}>signature line:</span>
            {side.matched_phrases.map((p, i) => (
              <Chip key={i} text={`“${p}”`} color="var(--color-verdict-succeeded)" />
            ))}
          </div>
        )}
        {side.matched_words.length > 0 && (
          <div className="flex flex-wrap gap-1 items-center">
            <span className="text-[10px]" style={{ color: "var(--color-ql-muted)" }}>your words:</span>
            {side.matched_words.map((w, i) => (
              <Chip key={i} text={w} color="var(--color-ql-accent)" />
            ))}
          </div>
        )}
        {side.avoided_violations.length > 0 && (
          <div className="flex flex-wrap gap-1 items-center">
            <span className="text-[10px]" style={{ color: "var(--color-ql-muted)" }}>says what you avoid:</span>
            {side.avoided_violations.map((w, i) => (
              <Chip key={i} text={w} color="var(--color-verdict-failed)" />
            ))}
          </div>
        )}
        {side.matched_phrases.length === 0 && side.matched_words.length === 0 && (
          <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
            None of your signature phrases or words.
          </p>
        )}
      </div>
    </div>
  );
}

export default function DriftHeadToHead({
  result,
  loading,
  disabled,
  onRun,
}: {
  result: DriftCompareResult | null;
  loading: boolean;
  disabled: boolean;
  onRun: () => void;
}) {
  return (
    <div className="mt-8">
      <div className="flex items-center gap-1.5 mb-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: "var(--color-ql-muted)" }}>
          The Drift Test &middot; does it still sound like you?
        </p>
        <span title="Runs the same brief through a plain LLM (no brand grounding) and StyleSync, then scores each on how well it uses your own signature phrases, recurring words, and avoids your banned terms — measured against your real brand profile.">
          <Info size={14} style={{ color: "var(--color-ql-muted)" }} />
        </span>
      </div>
      <p className="text-xs mb-3" style={{ color: "var(--color-ql-muted)" }}>
        Both are on-topic. Only one sounds like your brand.
      </p>

      <button
        onClick={onRun}
        disabled={disabled || loading}
        className="text-[12px] px-4 py-2 rounded-lg font-medium mb-3 disabled:opacity-50"
        style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
      >
        {loading ? "Running the Drift Test…" : "Run the Drift Test"}
      </button>
      {disabled && !loading && (
        <p className="text-[11px] mb-3" style={{ color: "var(--color-ql-muted)" }}>
          Fill in a product and occasion above first.
        </p>
      )}

      {result && (
        <div className="grid gap-3 md:grid-cols-2">
          <SideCard title="Plain LLM" side={result.baseline} winner={false} />
          <SideCard title="StyleSync" side={result.stylesync} winner />
        </div>
      )}
    </div>
  );
}
