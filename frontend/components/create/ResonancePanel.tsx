"use client";

import type { ResonanceResult, PersonaReaction } from "@/lib/types";

const POSITIVE_WORDS = ["delight", "excit", "intrigu", "love", "happy", "eager", "curious"];
const NEGATIVE_WORDS = ["annoy", "bored", "indiffer", "skeptic", "unimpress", "frustrat", "uncertain"];

function polarityColor(polarity: string): string {
  const p = polarity.toLowerCase();
  if (POSITIVE_WORDS.some((w) => p.includes(w))) return "var(--color-verdict-succeeded)";
  if (NEGATIVE_WORDS.some((w) => p.includes(w))) return "var(--color-verdict-failed)";
  return "var(--color-verdict-underperformed)";
}

function resonanceLabel(score: number): string {
  if (score >= 75) return "Strongly resonates";
  if (score >= 50) return "Moderately resonates";
  return "Weak resonance";
}

function PersonaCard({ reaction }: { reaction: PersonaReaction }) {
  const color = polarityColor(reaction.emotional_polarity);
  return (
    <div
      className="rounded-xl border p-3.5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
        <span className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>
          {reaction.persona}
        </span>
        <span
          className="text-[10px] uppercase tracking-[0.06em] ml-auto"
          style={{ color }}
        >
          {resonanceLabel(reaction.predicted_resonance)}
        </span>
      </div>
      <p className="text-[11px] italic mb-2" style={{ color: "var(--color-ql-muted)" }}>
        Mood: {reaction.emotional_polarity}
      </p>
      <ul className="flex flex-col gap-1">
        {reaction.critique_per_caption.map((c, i) => (
          <li key={i} className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
            <span style={{ color: "var(--color-ql-accent)" }}>V{i + 1}:</span> {c}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ResonancePanel({ result }: { result: ResonanceResult }) {
  return (
    <div className="mt-6">
      <p
        className="text-[11px] font-medium uppercase tracking-[0.12em] mb-3"
        style={{ color: "var(--color-ql-muted)" }}
      >
        Resonance Simulator · 3 audience personas, grounded in your real content clusters
      </p>

      {/* Lead with the actionable fix — the most useful part */}
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
          Panel&apos;s Pick — V{result.synthesis.winner_index + 1}
        </p>
        <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--color-ql-dark)" }}>
          {result.synthesis.reasoning}
        </p>
        {result.synthesis.top_actionable_fix && (
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
            <span className="font-medium" style={{ color: "var(--color-ql-accent)" }}>
              Try this:{" "}
            </span>
            {result.synthesis.top_actionable_fix}
          </p>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {result.persona_reactions.map((r, i) => (
          <PersonaCard key={i} reaction={r} />
        ))}
      </div>
    </div>
  );
}
