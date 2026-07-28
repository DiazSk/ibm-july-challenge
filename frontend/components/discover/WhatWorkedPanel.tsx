"use client";

import type { RankedPost, PostDiagnosis } from "@/lib/types";
import PostPreview from "@/components/common/PostPreview";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>{value}</span>
      <span className="text-[9px] uppercase tracking-[0.08em]" style={{ color: "var(--color-ql-muted)" }}>
        {label}
      </span>
    </div>
  );
}

function DiagnosisLine({ label, text, color }: { label: string; text: string; color: string }) {
  if (!text || text === "N/A") return null;
  return (
    <div>
      <span className="text-[9px] uppercase tracking-[0.1em] font-medium" style={{ color }}>{label}</span>
      <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-text)" }}>{text}</p>
    </div>
  );
}

function PostCard({ post, variant, diagnosis, loading }: {
  post: RankedPost;
  variant: "winner" | "loser";
  diagnosis?: PostDiagnosis | null;
  loading: boolean;
}) {
  const isWinner = variant === "winner";
  const accent = isWinner ? "var(--color-verdict-succeeded)" : "var(--color-verdict-failed)";

  return (
    <div
      className="flex-1 rounded-xl border p-4 flex flex-col gap-3"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-[0.1em] font-semibold" style={{ color: accent }}>
          {isWinner ? "▲ Top post" : "▼ Weakest post"}
        </span>
        <span
          className="text-[10px] px-2 py-0.5 rounded-full"
          style={{ color: "var(--color-ql-muted)", background: "var(--color-ql-gap)" }}
        >
          {post.pillar}
        </span>
      </div>

      <p className="text-sm leading-snug" style={{ color: "var(--color-ql-dark)", fontFamily: "var(--font-display)" }}>
        “{post.hook}”
      </p>

      <PostPreview shortcode={post.shortcode} defaultOpen />

      <div className="grid grid-cols-4 gap-2 py-2 border-y" style={{ borderColor: "var(--color-ql-border)" }}>
        <Metric label="Reach" value={post.reach.toLocaleString()} />
        <Metric label="Sends/reach" value={`${post.sends_per_reach}%`} />
        <Metric label="Saves/reach" value={`${post.saves_per_reach}%`} />
        <Metric label="Eng." value={`${post.engagement_rate}%`} />
      </div>

      {loading && (
        <p className="text-[11px] animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
          Why Engine is diagnosing…
        </p>
      )}
      {diagnosis && (
        <div className="flex flex-col gap-2.5">
          <DiagnosisLine label={isWinner ? "What worked" : "What failed"}
            text={isWinner ? diagnosis.what_worked : diagnosis.what_failed} color={accent} />
          <DiagnosisLine label="Brand-voice gap" text={diagnosis.brand_voice_gap} color="var(--color-ql-muted)" />
          <DiagnosisLine label="Next time" text={diagnosis.change_next_time} color="var(--color-ql-accent)" />
        </div>
      )}
    </div>
  );
}

/** The two most instructive posts, auto-selected by algorithm-weighted score,
 *  each explained by the Why Engine against the brand's own voice. */
export default function WhatWorkedPanel({ winner, loser, winnerDiagnosis, loserDiagnosis, loading }: {
  winner: RankedPost | null;
  loser: RankedPost | null;
  winnerDiagnosis?: PostDiagnosis | null;
  loserDiagnosis?: PostDiagnosis | null;
  loading: boolean;
}) {
  if (!winner && !loser) {
    return (
      <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
        No posts with metrics yet — sync your Instagram to unlock this.
      </p>
    );
  }
  return (
    <div className="flex flex-col md:flex-row gap-3">
      {winner && <PostCard post={winner} variant="winner" diagnosis={winnerDiagnosis} loading={loading} />}
      {loser && <PostCard post={loser} variant="loser" diagnosis={loserDiagnosis} loading={loading} />}
    </div>
  );
}
