"use client";

import type { StrategyMove, RankedPost } from "@/lib/types";
import PostPreview from "@/components/common/PostPreview";

/**
 * The single most important thing to do this week.
 *
 * The Strategy page used to open with four stacked read-only panels and roughly
 * thirty numbers, and the creator it was built for said she got lost in it. This
 * leads with one instruction in her own language, backed by one of her own posts,
 * and gives her somewhere to go when she wants to know why.
 */

const CHIPS = [
  "Why does this work?",
  "What should I post first?",
  "Show me a post I already made like this",
];

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

/**
 * Ratios like "0.43% sends-per-reach" are hard to feel. People sent this to a
 * friend N times is the same fact in a unit the creator can picture.
 */
function sendsFromPost(post: RankedPost | null): number | null {
  if (!post) return null;
  const sends = Math.round((post.sends_per_reach / 100) * post.reach);
  return sends > 0 ? sends : null;
}

export default function ThisWeekHero({
  move,
  proof,
}: {
  move: StrategyMove;
  proof: RankedPost | null;
}) {
  // Everything JARVIS needs to answer a follow-up about *this* recommendation.
  const context = [
    `Recommendation shown to the creator: "${move.title}"`,
    `Supporting number: ${move.stat}`,
    `Detail: ${move.detail}`,
    `Underlying principle: ${move.principle}`,
    proof ? `Their example post (${compact(proof.reach)} reach): "${proof.hook}"` : "",
  ]
    .filter(Boolean)
    .join("\n");

  function ask(question: string) {
    window.dispatchEvent(
      new CustomEvent("jarvis:ask", { detail: { question, context } }),
    );
  }

  const sends = sendsFromPost(proof);

  return (
    <section
      className="rounded-xl border p-6"
      style={{
        borderColor: "var(--color-ql-accent)",
        background: "color-mix(in oklch, var(--color-ql-accent) 5%, transparent)",
      }}
    >
      <p
        className="text-[10px] font-medium uppercase tracking-[0.18em] mb-3"
        style={{ color: "var(--color-ql-accent)" }}
      >
        This week
      </p>

      <h2
        className="text-2xl mb-3"
        style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
      >
        {move.title}
      </h2>

      <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--color-ql-dark)" }}>
        {move.detail}
      </p>

      <p className="text-xs mb-5" style={{ color: "var(--color-ql-muted)" }}>
        {sends !== null && (
          <>
            <span style={{ color: "var(--color-ql-dark)" }}>
              {sends.toLocaleString()} people
            </span>{" "}
            sent your best one to a friend.{" "}
          </>
        )}
        {move.stat}
      </p>

      {proof && (
        <div className="mb-5">
          <p className="text-[10px] uppercase tracking-[0.12em] mb-2" style={{ color: "var(--color-ql-muted)" }}>
            Your proof
          </p>
          <p
            className="text-sm leading-snug mb-2"
            style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
          >
            &ldquo;{proof.hook}&rdquo;
          </p>
          <PostPreview shortcode={proof.shortcode} />
        </div>
      )}

      <p className="text-[11px] mb-2" style={{ color: "var(--color-ql-muted)" }}>
        Not sure about this? Ask:
      </p>
      <div className="flex flex-wrap gap-2">
        {CHIPS.map((q) => (
          <button
            key={q}
            onClick={() => ask(q)}
            className="text-[11px] px-3 py-1.5 rounded-full border transition-colors hover:opacity-80"
            style={{
              borderColor: "var(--color-ql-border)",
              color: "var(--color-ql-dark)",
              background: "var(--color-ql-card)",
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </section>
  );
}
