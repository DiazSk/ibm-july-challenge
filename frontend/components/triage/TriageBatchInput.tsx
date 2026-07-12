"use client";

import { useQuery } from "@tanstack/react-query";
import { getClusters } from "@/lib/api";

const MAX_MESSAGES = 20;

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

interface Props {
  text: string;
  onTextChange: (v: string) => void;
  clusterId: number;
  onClusterChange: (v: number) => void;
  onSubmit: () => void;
  loading: boolean;
}

export default function TriageBatchInput({
  text,
  onTextChange,
  clusterId,
  onClusterChange,
  onSubmit,
  loading,
}: Props) {
  const { data: clusters } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });
  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const overLimit = lines.length > MAX_MESSAGES;

  return (
    <div
      className="rounded-xl border p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <h3
        className="text-base mb-1"
        style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
      >
        Paste Comments / DMs
      </h3>
      <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--color-ql-muted)" }}>
        StyleSync doesn&apos;t have live Instagram inbox access (that requires Meta platform
        approval) — this is a batch triage tool, not real-time automation. Paste up to{" "}
        {MAX_MESSAGES} messages below, one per line.
      </p>

      <textarea
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder={"One message per line…"}
        rows={6}
        className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y"
        style={{
          background: "var(--color-ql-gap)",
          border: `1px solid ${overLimit ? "var(--color-verdict-failed)" : "var(--color-ql-border)"}`,
          color: "var(--color-ql-dark)",
        }}
      />
      <p
        className="text-[11px] mt-1"
        style={{ color: overLimit ? "var(--color-verdict-failed)" : "var(--color-ql-muted)" }}
      >
        {overLimit
          ? `${lines.length} lines — trim ${lines.length - MAX_MESSAGES} to fit the ${MAX_MESSAGES}-message max`
          : `${lines.length} / ${MAX_MESSAGES} messages`}
      </p>

      {clusterList.length > 0 && (
        <div className="mt-3">
          <p
            className="text-[10px] font-medium uppercase tracking-[0.1em] mb-1.5"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Reply voice
          </p>
          <div className="flex flex-wrap gap-1.5">
            {clusterList.map((c) => (
              <button
                key={c.cluster_id}
                onClick={() => onClusterChange(c.cluster_id)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] transition-colors"
                style={{
                  borderColor: clusterId === c.cluster_id ? "var(--color-ql-dark)" : "var(--color-ql-border)",
                  background: clusterId === c.cluster_id ? "var(--color-ql-gap)" : "transparent",
                  color: "var(--color-ql-dark)",
                }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: CLUSTER_COLORS[c.cluster_id % CLUSTER_COLORS.length] }}
                />
                {c.pillar}
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={onSubmit}
        disabled={loading || lines.length === 0 || overLimit}
        className="w-full mt-4 py-2.5 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
        style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}
      >
        {loading ? (
          <span className="animate-pulse">Triaging {lines.length} messages…</span>
        ) : (
          "Triage Messages"
        )}
      </button>
    </div>
  );
}
