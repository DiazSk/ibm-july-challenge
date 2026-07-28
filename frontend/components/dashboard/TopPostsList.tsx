"use client";

import type { TopPost } from "@/lib/types";
import PostPreview from "@/components/common/PostPreview";
import { clusterColor } from "@/lib/utils";

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function TopPostsList({ posts }: { posts: TopPost[] }) {
  if (posts.length === 0) {
    return (
      <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
        No posts with metrics yet — sync from Instagram to populate this.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {posts.map((p, i) => (
        <div key={p.shortcode || i} className="flex items-start gap-3">
          <span
            className="shrink-0 text-[11px] font-medium w-5 text-center"
            style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-muted)" }}
          >
            {i + 1}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-0.5">
              <span
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: clusterColor(p.cluster_id) }}
              />
              <span className="text-[10px] truncate" style={{ color: "var(--color-ql-muted)" }}>
                {p.pillar}
              </span>
            </div>
            <p className="text-xs leading-snug line-clamp-2" style={{ color: "var(--color-ql-dark)" }}>
              {p.hook || "(no caption)"}
            </p>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-[10px]" style={{ color: "var(--color-ql-muted)" }}>
              <span>{compact(p.reach)} reach</span>
              <span>{compact(p.saves)} saves</span>
              <span>{compact(p.likes)} likes</span>
              <span>{p.engagement_rate}% eng</span>
            </div>
            <div className="mt-1.5">
              <PostPreview shortcode={p.shortcode} height={420} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
