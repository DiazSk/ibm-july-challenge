"use client";

import type { BoostAdvisorResult } from "@/lib/types";
import ConfidenceBadge from "@/components/shared/ConfidenceBadge";

const CLUSTER_COLORS: Record<number, string> = {
  0: "var(--color-cluster-0)",
  1: "var(--color-cluster-1)",
  2: "var(--color-cluster-2)",
  3: "var(--color-cluster-3)",
  4: "var(--color-cluster-4)",
};

interface Props {
  result: BoostAdvisorResult;
}

export default function BoostAdvisor({ result }: Props) {
  const accentColor = CLUSTER_COLORS[result.boost_cluster_id] ?? "var(--color-ql-accent)";
  const warnColor   = CLUSTER_COLORS[result.dont_boost_cluster_id] ?? "var(--color-ql-muted)";

  return (
    <div className="flex flex-col gap-4 mt-5">
      {/* Recommendation card */}
      <div
        className="rounded-xl border p-5"
        style={{
          borderColor: accentColor,
          background: "var(--color-ql-card)",
        }}
      >
        {/* Cluster badge */}
        <div className="flex items-center gap-2 mb-3">
          <span
            className="text-[10px] font-medium uppercase tracking-[0.1em] px-2.5 py-1 rounded-md"
            style={{ background: accentColor, color: "var(--color-ql-bg)" }}
          >
            Boost This
          </span>
          <span
            className="text-xs font-medium"
            style={{ color: accentColor }}
          >
            C{result.boost_cluster_id} · {result.boost_cluster_name}
          </span>
          {result.confidence && (
            <ConfidenceBadge score={result.confidence.score} rationale={result.confidence.rationale} />
          )}
        </div>

        {/* Best post hook */}
        <p
          className="text-sm leading-relaxed mb-4"
          style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
        >
          &ldquo;{result.boost_post_hook}&rdquo;
        </p>

        {/* Reasoning */}
        <div className="mb-3">
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-1"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Why
          </p>
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
            {result.reasoning}
          </p>
        </div>

        {/* Boost strategy */}
        <div className="mb-3">
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-1"
            style={{ color: "var(--color-ql-muted)" }}
          >
            How to Boost
          </p>
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
            {result.boost_strategy}
          </p>
        </div>

        {/* Expected impact */}
        <div
          className="rounded-lg px-3 py-2.5"
          style={{ background: "var(--color-ql-gap)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-1"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Expected Impact
          </p>
          <p className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
            {result.expected_impact}
          </p>
        </div>
      </div>

      {/* Don't boost warning */}
      <div
        className="rounded-xl border p-4"
        style={{
          borderColor: "var(--color-ql-border)",
          background: "var(--color-ql-card)",
          opacity: 0.75,
        }}
      >
        <div className="flex items-center gap-2 mb-2">
          <span
            className="text-[10px] font-medium uppercase tracking-[0.1em] px-2 py-0.5 rounded-md"
            style={{ background: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
          >
            Don&apos;t Boost
          </span>
          <span
            className="text-[11px]"
            style={{ color: warnColor }}
          >
            C{result.dont_boost_cluster_id} · {result.dont_boost_cluster_name}
          </span>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
          {result.dont_boost_reason}
        </p>
      </div>
    </div>
  );
}
