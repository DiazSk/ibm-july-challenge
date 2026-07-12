"use client";

import { useState } from "react";
import type { GuardianReviewResult, GuardianRound } from "@/lib/types";

const SEVERITY_COLOR: Record<string, string> = {
  none: "var(--color-verdict-succeeded)",
  minor: "var(--color-verdict-underperformed)",
  major: "var(--color-verdict-failed)",
};

function RoundCard({ round }: { round: GuardianRound }) {
  const color = SEVERITY_COLOR[round.critique.severity] ?? "var(--color-ql-muted)";
  return (
    <div
      className="rounded-xl border p-3.5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] font-medium uppercase tracking-[0.08em]" style={{ color: "var(--color-ql-accent)" }}>
          Round {round.round}
        </span>
        <span
          className="text-[10px] uppercase tracking-[0.06em] ml-auto px-1.5 py-0.5 rounded-full"
          style={{ background: color, color: "var(--color-ql-bg)" }}
        >
          {round.critique.verdict === "approve" ? "Approved" : round.critique.severity}
        </span>
      </div>
      <p className="text-[11px] leading-relaxed mb-2 whitespace-pre-wrap" style={{ color: "var(--color-ql-dark)" }}>
        {round.caption}
      </p>
      {round.critique.issues.length > 0 && (
        <ul className="flex flex-col gap-1">
          {round.critique.issues.map((issue, i) => (
            <li key={i} className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
              &bull; {issue}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function GuardianPanel({
  result,
  onUse,
}: {
  result: GuardianReviewResult;
  onUse?: (caption: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const topIssue = result.history[result.history.length - 1]?.critique.issues[0];

  return (
    <div className="mt-6">
      <p
        className="text-[11px] font-medium uppercase tracking-[0.12em] mb-3"
        style={{ color: "var(--color-ql-muted)" }}
      >
        Brand Guardian Courtroom &middot; adversarial critique &amp; refine
      </p>

      <div
        className="rounded-xl border p-4 mb-3"
        style={{
          borderColor: "var(--color-ql-accent)",
          background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)",
        }}
      >
        <p
          className="text-[10px] font-medium uppercase tracking-[0.1em] mb-1.5"
          style={{ color: "var(--color-ql-accent)" }}
        >
          {result.converged
            ? `Approved after ${result.rounds_used} round${result.rounds_used === 1 ? "" : "s"}`
            : `Best of ${result.rounds_used} rounds — still flagged`}
        </p>
        <p className="text-sm leading-relaxed mb-2 whitespace-pre-wrap" style={{ color: "var(--color-ql-dark)" }}>
          {result.final_caption}
        </p>
        {!result.converged && topIssue && (
          <p className="text-xs leading-relaxed mb-2" style={{ color: "var(--color-ql-text)" }}>
            <span className="font-medium" style={{ color: "var(--color-ql-accent)" }}>
              Still not fully approved:{" "}
            </span>
            {topIssue}
          </p>
        )}
        <div className="flex gap-2 mt-2">
          {onUse && (
            <button
              onClick={() => onUse(result.final_caption)}
              className="text-[11px] px-3 py-1.5 rounded-lg font-medium"
              style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
            >
              Use this version
            </button>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-[11px] px-3 py-1.5 rounded-lg border"
            style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
          >
            {expanded ? "Hide round history" : "Show round history"}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="grid gap-3 md:grid-cols-3">
          {result.history.map((round, i) => (
            <RoundCard key={i} round={round} />
          ))}
        </div>
      )}
    </div>
  );
}
