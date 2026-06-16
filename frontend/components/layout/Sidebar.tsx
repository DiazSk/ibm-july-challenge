"use client";

import { useQuery } from "@tanstack/react-query";
import { getBrandProfile, getClusters } from "@/lib/api";

const CLUSTER_COLORS = [
  "#5A8A6A",
  "#8B7355",
  "#A35A5A",
  "#5A6A8A",
  "#6A5A8A",
] as const;

export default function Sidebar() {
  const { data: profile } = useQuery({
    queryKey: ["brand-profile"],
    queryFn: getBrandProfile,
  });
  const { data: clusters } = useQuery({
    queryKey: ["clusters"],
    queryFn: getClusters,
  });

  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  return (
    <aside
      className="w-64 shrink-0 flex flex-col border-r overflow-y-auto"
      style={{
        background: "var(--color-ql-sidebar)",
        borderColor: "var(--color-ql-border)",
      }}
    >
      {/* Brand header */}
      <div
        className="px-5 py-6 border-b"
        style={{ borderColor: "var(--color-ql-border)" }}
      >
        <p
          className="text-[10px] font-medium uppercase tracking-[0.15em] mb-1"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Creative Intelligence
        </p>
        <h2
          className="text-base leading-tight"
          style={{ fontFamily: "Georgia, serif", color: "var(--color-ql-dark)" }}
        >
          {profile?.brand_name ?? "HotCakes Bakes"}
        </h2>
        <p
          className="text-xs mt-0.5"
          style={{ color: "var(--color-ql-muted)" }}
        >
          {profile?.handle ?? "@hot_cakesbakes"}
        </p>
      </div>

      {/* Content pillars */}
      {clusterList.length > 0 && (
        <div className="px-5 py-4">
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-3"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Content Pillars
          </p>
          <div className="flex flex-col gap-2">
            {clusterList.map((c) => (
              <div key={c.cluster_id} className="flex items-start gap-2">
                <span
                  className="mt-1 w-2 h-2 rounded-full shrink-0"
                  style={{ background: CLUSTER_COLORS[c.cluster_id] }}
                />
                <div>
                  <p
                    className="text-xs font-medium leading-snug"
                    style={{ color: "var(--color-ql-dark)" }}
                  >
                    {c.pillar}
                  </p>
                  <p
                    className="text-[11px]"
                    style={{ color: "var(--color-ql-muted)" }}
                  >
                    {c.post_count} posts
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tone tags */}
      {profile && (
        <div
          className="px-5 py-4 border-t mt-auto"
          style={{ borderColor: "var(--color-ql-border)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Brand Tone
          </p>
          <div className="flex flex-wrap gap-1">
            {profile.tone_descriptors.slice(0, 6).map((t) => (
              <span
                key={t}
                className="text-[10px] px-2 py-0.5 rounded-full border"
                style={{
                  borderColor: "var(--color-ql-border)",
                  color: "var(--color-ql-muted)",
                  background: "var(--color-ql-card)",
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
