"use client";

import { useQuery } from "@tanstack/react-query";
import { getClusters } from "@/lib/api";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

interface Props {
  clusterId: number;
  onClusterChange: (v: number) => void;
  onLoad: () => void;
  loading: boolean;
}

export default function InboxInput({ clusterId, onClusterChange, onLoad, loading }: Props) {
  const { data: clusters } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });
  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  return (
    <div
      className="rounded-xl border p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <h3
        className="text-base mb-1"
        style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
      >
        Recent comments
      </h3>
      <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--color-ql-muted)" }}>
        Pull the latest comments on your recent posts, draft on-brand replies, and reply
        directly. Each reply is public, so you review and send them one at a time.
      </p>

      {clusterList.length > 0 && (
        <div className="mb-3">
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
        onClick={onLoad}
        disabled={loading}
        className="w-full py-2.5 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
        style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}
      >
        {loading ? <span className="animate-pulse">Loading comments…</span> : "Load comments from Instagram"}
      </button>
    </div>
  );
}
