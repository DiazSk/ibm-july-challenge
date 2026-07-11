"use client";

import type { StrategicInsightsResult } from "@/lib/types";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

interface Props {
  result: StrategicInsightsResult;
}

export default function StrategyBrief({ result }: Props) {
  return (
    <div className="flex flex-col gap-4 mt-5">
      {/* Tensions */}
      {result.tensions.length > 0 && (
        <div
          className="rounded-xl border p-4"
          style={{
            borderColor: "var(--color-ql-border)",
            background: "var(--color-ql-card)",
          }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Detected Tensions
          </p>
          <ul className="flex flex-col gap-1.5">
            {result.tensions.map((t, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: "var(--color-verdict-underperformed)" }}
                />
                <span
                  className="text-xs leading-relaxed"
                  style={{ color: "var(--color-ql-text)" }}
                >
                  {t}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Cluster signal pills */}
      <div className="flex gap-3">
        {result.overused_cluster !== null && (
          <div
            className="flex-1 rounded-xl border p-3 text-center"
            style={{
              borderColor: "var(--color-verdict-failed)",
              background: "color-mix(in oklch, var(--color-verdict-failed) 5%, transparent)",
            }}
          >
            <p
              className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
              style={{ color: "var(--color-verdict-failed)" }}
            >
              Over-invested
            </p>
            <div className="flex items-center justify-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{
                  background:
                    CLUSTER_COLORS[result.overused_cluster] ?? "var(--color-cluster-2)",
                }}
              />
              <span
                className="text-xs font-medium"
                style={{ color: "var(--color-ql-dark)" }}
              >
                C{result.overused_cluster}
              </span>
            </div>
          </div>
        )}

        {result.underutilized_cluster !== null && (
          <div
            className="flex-1 rounded-xl border p-3 text-center"
            style={{
              borderColor: "var(--color-verdict-succeeded)",
              background: "color-mix(in oklch, var(--color-verdict-succeeded) 5%, transparent)",
            }}
          >
            <p
              className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
              style={{ color: "var(--color-verdict-succeeded)" }}
            >
              Underutilized
            </p>
            <div className="flex items-center justify-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{
                  background:
                    CLUSTER_COLORS[result.underutilized_cluster] ?? "var(--color-cluster-0)",
                }}
              />
              <span
                className="text-xs font-medium"
                style={{ color: "var(--color-ql-dark)" }}
              >
                C{result.underutilized_cluster}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Strategic brief */}
      <div
        className="rounded-xl border p-4"
        style={{
          borderColor: "var(--color-ql-border)",
          background: "var(--color-ql-gap)",
        }}
      >
        <p
          className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Strategic Brief
        </p>
        <p
          className="text-sm leading-relaxed"
          style={{
            color: "var(--color-ql-dark)",
            fontFamily: "var(--font-display)",
          }}
        >
          {result.strategic_brief}
        </p>
      </div>

      {/* Experiment callout */}
      {result.experiment && (
        <div
          className="rounded-xl border p-4"
          style={{
            borderColor: "var(--color-ql-accent)",
            background: "var(--color-ql-card)",
          }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
            style={{ color: "var(--color-ql-accent)" }}
          >
            Experiment to Run
          </p>
          <p
            className="text-sm leading-relaxed"
            style={{ color: "var(--color-ql-dark)" }}
          >
            {result.experiment}
          </p>
        </div>
      )}
    </div>
  );
}
