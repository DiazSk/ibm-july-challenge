"use client";

import type { StrategyMove, StrategyBriefResult } from "@/lib/types";
import SourceBadge from "./SourceBadge";

/** Result-proven moves: each pairs a number from the creator's own data with a
 *  sourced Instagram-ranking principle. Optionally topped with a Granite brief. */
export default function PlaybookPanel({ moves, brief, briefLoading }: {
  moves: StrategyMove[];
  brief?: StrategyBriefResult;
  briefLoading: boolean;
}) {
  return (
    <div className="flex flex-col gap-4">
      {/* Granite brief (progressive — page works without it) */}
      <div
        className="rounded-xl border p-4"
        style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}
      >
        <p className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2" style={{ color: "var(--color-ql-muted)" }}>
          Strategic Brief
        </p>
        {briefLoading && !brief && (
          <p className="text-xs animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
            Granite is writing your brief…
          </p>
        )}
        {brief?.strategic_brief && (
          <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-dark)", fontFamily: "var(--font-display)" }}>
            {brief.strategic_brief}
          </p>
        )}
        {brief?.experiment && (
          <p className="text-xs leading-relaxed mt-3 pt-3 border-t" style={{ color: "var(--color-ql-text)", borderColor: "var(--color-ql-border)" }}>
            <span className="font-medium" style={{ color: "var(--color-ql-accent)" }}>Experiment · </span>
            {brief.experiment}
          </p>
        )}
      </div>

      {/* Result-proven moves */}
      <div className="flex flex-col gap-3">
        {moves.map((m, i) => (
          <div
            key={i}
            className="rounded-xl border p-4 flex flex-col gap-2"
            style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-sm font-medium" style={{ color: "var(--color-ql-dark)", fontFamily: "var(--font-display)" }}>
                {m.title}
              </h3>
              <SourceBadge source={m.source} />
            </div>

            <p className="text-xs font-medium" style={{ color: "var(--color-ql-accent)" }}>{m.stat}</p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-text)" }}>{m.detail}</p>

            <p
              className="text-[11px] leading-relaxed mt-1 pl-2.5 border-l-2"
              style={{ color: "var(--color-ql-muted)", borderColor: "var(--color-ql-border)" }}
            >
              Why it works: {m.principle}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
