"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getDiagnosePosts, getPostDiagnosis } from "@/lib/api";
import type { DiagnosePost, PerformanceTier } from "@/lib/types";
import DiagnosisPanel from "@/components/analyze/DiagnosisPanel";
import PostPreview from "@/components/common/PostPreview";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

const TIERS: PerformanceTier[] = ["Top", "Solid", "Weak", "No data"];

// The tier is the deterministic algorithm score (sends×3 + saves per reach) —
// deliberately styled apart from the LLM verdict, which can disagree with it.
const TIER_COLOR: Record<PerformanceTier, string> = {
  Top: "var(--color-verdict-succeeded)",
  Solid: "var(--color-ql-accent)",
  Weak: "var(--color-verdict-underperformed)",
  "No data": "var(--color-ql-muted)",
};

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
}

function TierBadge({ tier }: { tier: PerformanceTier }) {
  const c = TIER_COLOR[tier];
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
      style={{
        color: c,
        background: `color-mix(in oklch, ${c} 10%, transparent)`,
        border: `1px solid ${c}`,
      }}
      title="Algorithm score — sends and saves per reach (not the AI verdict)"
    >
      {tier}
    </span>
  );
}

function PostRow({ post }: { post: DiagnosePost }) {
  const [open, setOpen] = useState(false);
  const [forced, setForced] = useState(0);

  // Only fetch the ~10s Granite diagnosis once the row is actually opened.
  const { data, isFetching, error } = useQuery({
    queryKey: ["post-diagnosis", post.shortcode, forced],
    queryFn: () => getPostDiagnosis(post.shortcode, forced > 0),
    enabled: open,
    staleTime: Infinity,
    retry: false,
  });

  const date = post.timestamp_utc ? post.timestamp_utc.slice(0, 10) : "";

  return (
    <div
      className="rounded-lg border p-3"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <TierBadge tier={post.tier} />
            <span className="text-[10px]" style={{ color: "var(--color-ql-muted)" }}>
              {post.post_type} · {date}
            </span>
            {post.has_diagnosis && (
              <span className="text-[10px]" style={{ color: "var(--color-ql-accent)" }} title="Diagnosis already generated">
                ✓ diagnosed
              </span>
            )}
          </div>

          <p
            className="text-xs line-clamp-2 leading-relaxed"
            style={{ color: "var(--color-ql-text)" }}
          >
            {post.hook || post.caption || "(no caption)"}
          </p>

          <div
            className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-[10px]"
            style={{ color: "var(--color-ql-muted)" }}
          >
            <span>{compact(post.reach)} reach</span>
            {post.views > 0 && <span>{compact(post.views)} views</span>}
            <span>{compact(post.likes)} likes</span>
            <span>{compact(post.shares)} shares</span>
            <span>{compact(post.saves)} saves</span>
            <span>{post.engagement_rate}% eng</span>
          </div>
        </div>

        <button
          onClick={() => setOpen((o) => !o)}
          className="text-[11px] font-medium shrink-0 transition-colors"
          style={{ color: "var(--color-ql-accent)" }}
        >
          {open ? "Hide" : "Diagnose ▸"}
        </button>
      </div>

      {open && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: "var(--color-ql-border)" }}>
          {/* defaultOpen matches the Strategy page: the embed shows as soon as
              the row is expanded. Still one iframe per *expanded* row only. */}
          <PostPreview shortcode={post.shortcode} height={420} defaultOpen />

          {isFetching && (
            <p className="text-xs mt-3 animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
              Why Engine is diagnosing this post — visual + caption + metrics…
            </p>
          )}

          {error && (
            <p className="text-xs mt-3" style={{ color: "var(--color-verdict-failed)" }}>
              {error instanceof Error ? error.message : "Diagnosis failed"}
            </p>
          )}

          {data && !isFetching && (
            <>
              <DiagnosisPanel result={data} />
              <button
                onClick={() => setForced((f) => f + 1)}
                className="mt-3 text-[11px] px-2 py-1 rounded border transition-colors"
                style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
              >
                Re-diagnose
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function PostDiagnosisList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["diagnose-posts"],
    queryFn: getDiagnosePosts,
  });
  const [tierFilter, setTierFilter] = useState<PerformanceTier | "All">("All");

  if (isLoading) {
    return (
      <p className="text-sm animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
        Loading your posts…
      </p>
    );
  }
  if (error) {
    return (
      <p className="text-sm" style={{ color: "var(--color-verdict-failed)" }}>
        {error instanceof Error ? error.message : "Could not load posts"}
      </p>
    );
  }
  if (!data || !data.groups.length) {
    return (
      <p className="text-sm" style={{ color: "var(--color-ql-muted)" }}>
        No posts yet — sync from Instagram to populate this.
      </p>
    );
  }

  const shown = data.groups
    .map((g) => ({
      ...g,
      posts: tierFilter === "All" ? g.posts : g.posts.filter((p) => p.tier === tierFilter),
    }))
    .filter((g) => g.posts.length > 0);

  const shownCount = shown.reduce((n, g) => n + g.posts.length, 0);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2 flex-wrap">
        {(["All", ...TIERS] as const).map((t) => {
          const active = tierFilter === t;
          return (
            <button
              key={t}
              onClick={() => setTierFilter(t as PerformanceTier | "All")}
              className="text-[11px] px-2.5 py-1 rounded-full border transition-colors"
              style={{
                borderColor: active ? "var(--color-ql-dark)" : "var(--color-ql-border)",
                background: active ? "var(--color-ql-dark)" : "transparent",
                color: active ? "var(--color-ql-bg)" : "var(--color-ql-muted)",
              }}
            >
              {t}
            </button>
          );
        })}
        <span className="text-[11px] ml-auto" style={{ color: "var(--color-ql-muted)" }}>
          {shownCount} of {data.total} posts
        </span>
      </div>

      <p className="text-[11px] -mt-3" style={{ color: "var(--color-ql-muted)" }}>
        The badge is your <strong style={{ color: "var(--color-ql-text)" }}>algorithm score</strong> —
        sends and saves per reach, the signals Instagram rewards for distribution. The AI verdict
        inside a post weighs the caption and visuals too, so the two can legitimately differ.
      </p>

      {shown.map((g) => (
        <div key={g.group_key}>
          <div className="flex items-center gap-2 mb-2">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{
                background:
                  g.cluster_id === null
                    ? "var(--color-ql-muted)"
                    : CLUSTER_COLORS[g.cluster_id % CLUSTER_COLORS.length],
              }}
            />
            <span className="text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
              {g.pillar}
            </span>
            <span className="text-[11px] ml-auto" style={{ color: "var(--color-ql-muted)" }}>
              {g.posts.length}
              {tierFilter !== "All" && ` of ${g.post_count}`} posts
            </span>
          </div>

          {g.note && (
            <p className="text-[11px] mb-2" style={{ color: "var(--color-ql-muted)" }}>
              {g.note}
            </p>
          )}

          <div className="flex flex-col gap-2">
            {g.posts.map((p) => (
              <PostRow key={p.shortcode} post={p} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
