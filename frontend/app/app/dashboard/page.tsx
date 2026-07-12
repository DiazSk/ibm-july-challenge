"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getBrandProfile,
  getClusters,
  getWorkbenchAssets,
  getStrategicInsights,
  startWeeklyBrief,
  getWeeklyBriefStatus,
} from "@/lib/api";
import type { WorkbenchAsset, WeeklyBriefStatus } from "@/lib/types";
import { useWorkbenchDrawer } from "@/lib/workbench-drawer-context";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

const ASSET_LABELS: Record<string, string> = {
  caption: "Caption",
  image_prompt: "Image Direction",
  reel_script: "Reel Script",
  carousel: "Carousel",
  static_script: "Static Post",
  recovery_brief: "Recovery Brief",
  weekly_brief_draft: "Weekly Brief Draft",
  guardian_refined_caption: "Guardian-Refined Caption",
  triage_reply: "Drafted Reply",
};

function previewText(asset: WorkbenchAsset): string {
  if (typeof asset.content === "string") return asset.content;
  const obj = asset.content as Record<string, unknown>;
  return String(obj.hook ?? obj.caption ?? obj.headline ?? obj.new_hook ?? obj.drafted_reply ?? "Saved asset");
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      className="rounded-xl border p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <p
        className="text-[10px] font-medium uppercase tracking-[0.15em] mb-2"
        style={{ color: "var(--color-ql-muted)" }}
      >
        {label}
      </p>
      <p className="text-2xl" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
        {value}
      </p>
    </div>
  );
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { setOpen: setDrawerOpen } = useWorkbenchDrawer();

  const { data: profile } = useQuery({ queryKey: ["brand-profile"], queryFn: getBrandProfile });
  const { data: clusters } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });
  const { data: assets = [] } = useQuery({
    queryKey: ["workbench"],
    queryFn: () => getWorkbenchAssets(),
  });
  const { data: insights } = useQuery({
    queryKey: ["strategic-insights"],
    queryFn: getStrategicInsights,
  });

  const [wbJobId, setWbJobId] = useState<string | null>(null);
  const [wbStatus, setWbStatus] = useState<WeeklyBriefStatus | null>(null);
  const [wbLost, setWbLost] = useState(false);
  const [wbStarting, setWbStarting] = useState(false);

  useEffect(() => {
    if (!wbJobId || wbLost) return;
    if (wbStatus?.status === "done" || wbStatus?.status === "error") return;

    let failCount = 0;
    const id = setInterval(async () => {
      try {
        const s = await getWeeklyBriefStatus(wbJobId);
        setWbStatus(s);
        failCount = 0;
        if (s.status === "done") {
          clearInterval(id);
          queryClient.invalidateQueries({ queryKey: ["workbench"] });
        } else if (s.status === "error") {
          clearInterval(id);
        }
      } catch {
        failCount += 1;
        if (failCount >= 3) {
          clearInterval(id);
          setWbLost(true);
        }
      }
    }, 3000);

    return () => clearInterval(id);
  }, [wbJobId, wbStatus?.status, wbLost, queryClient]);

  async function handleStartWeeklyBrief() {
    setWbStarting(true);
    try {
      const { job_id } = await startWeeklyBrief(2);
      setWbJobId(job_id);
      setWbStatus({ status: "queued", progress: 0, message: "Starting…" });
      setWbLost(false);
    } catch {
      // leave idle; button remains clickable to retry
    } finally {
      setWbStarting(false);
    }
  }

  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];
  const totalPosts = clusterList.reduce((sum, c) => sum + c.post_count, 0);

  const recent = [...assets]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <motion.div
      className="max-w-4xl mx-auto flex flex-col gap-8"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div>
        <p
          className="text-[10px] font-medium uppercase tracking-[0.18em] mb-1"
          style={{ color: "var(--color-ql-accent)" }}
        >
          Dashboard
        </p>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          {profile?.brand_name ?? "Your brand"}
        </h1>
      </div>

      {/* KPI row — only real/derived numbers, nothing fabricated */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <KpiCard label="Posts Analyzed" value={totalPosts || "—"} />
        <KpiCard label="Content Pillars" value={clusterList.length || "—"} />
        <KpiCard label="Saved Assets" value={assets.length} />
      </div>

      {/* Strategic brief — real synthesized recommendation, not fabricated copy */}
      {insights?.strategic_brief && (
        <div
          className="rounded-xl border p-5"
          style={{
            borderColor: "var(--color-ql-accent)",
            background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)",
          }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.15em] mb-2"
            style={{ color: "var(--color-ql-accent)" }}
          >
            Strategic Brief
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
            {insights.strategic_brief}
          </p>
          <Link
            href="/app/discover"
            className="inline-block mt-3 text-[11px] font-medium"
            style={{ color: "var(--color-ql-accent)" }}
          >
            View full strategy →
          </Link>
        </div>
      )}

      {/* Weekly Brief Agent — proactive content planning for underused pillars */}
      <div
        className="rounded-xl border p-5"
        style={{
          borderColor: "var(--color-ql-accent)",
          background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)",
        }}
      >
        <p
          className="text-[10px] font-medium uppercase tracking-[0.15em] mb-2"
          style={{ color: "var(--color-ql-accent)" }}
        >
          Weekly Brief Agent
        </p>

        {!wbJobId && (
          <>
            <p className="text-sm leading-relaxed mb-3" style={{ color: "var(--color-ql-dark)" }}>
              Let Granite scout your most underused content pillar and draft a few ready-to-post ideas for this week.
            </p>
            <button
              onClick={handleStartWeeklyBrief}
              disabled={wbStarting}
              className="text-[11px] font-medium px-3 py-1.5 rounded-lg border"
              style={{
                borderColor: "var(--color-ql-accent)",
                color: "var(--color-ql-accent)",
                opacity: wbStarting ? 0.6 : 1,
              }}
            >
              {wbStarting ? "Starting…" : "Generate This Week's Brief"}
            </button>
          </>
        )}

        {wbJobId && wbLost && (
          <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
            Job may have been interrupted — check Workbench for any completed drafts.
          </p>
        )}

        {wbJobId && !wbLost && wbStatus && wbStatus.status !== "done" && wbStatus.status !== "error" && (
          <div>
            <p className="text-sm mb-2" style={{ color: "var(--color-ql-dark)" }}>
              {wbStatus.message}
            </p>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--color-ql-gap)" }}>
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${wbStatus.progress}%`, background: "var(--color-ql-accent)" }}
              />
            </div>
          </div>
        )}

        {wbJobId && !wbLost && wbStatus?.status === "error" && (
          <p className="text-sm" style={{ color: "var(--color-ql-dark)" }}>
            Something went wrong generating the brief. Check Workbench, or try again.
          </p>
        )}

        {wbJobId && !wbLost && wbStatus?.status === "done" && (
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-sm" style={{ color: "var(--color-ql-dark)" }}>
              {wbStatus.n ?? "A few"} draft{wbStatus.n === 1 ? "" : "s"} ready
              {wbStatus.cluster_label ? ` for ${wbStatus.cluster_label}` : ""}.
            </p>
            <button
              onClick={() => setDrawerOpen(true)}
              className="text-[11px] font-medium"
              style={{ color: "var(--color-ql-accent)" }}
            >
              Review drafts →
            </button>
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Content pillars */}
        <section
          className="rounded-xl border p-5"
          style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-4"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Content Pillars
          </p>
          {clusterList.length === 0 && (
            <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
              No clusters yet.
            </p>
          )}
          <div className="flex flex-col gap-3">
            {clusterList.map((c) => {
              const share = totalPosts > 0 ? Math.round((c.post_count / totalPosts) * 100) : 0;
              return (
                <div key={c.cluster_id}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>
                      {c.pillar}
                    </span>
                    <span className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
                      {share}% · {c.post_count} posts
                    </span>
                  </div>
                  <div
                    className="h-1.5 rounded-full overflow-hidden"
                    style={{ background: "var(--color-ql-gap)" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${share}%`,
                        background: CLUSTER_COLORS[c.cluster_id % CLUSTER_COLORS.length],
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <Link
            href="/app/brand"
            className="inline-block mt-4 text-[11px] font-medium"
            style={{ color: "var(--color-ql-accent)" }}
          >
            View brand voice →
          </Link>
        </section>

        {/* Recent generations — from Workbench, real & persisted */}
        <section
          className="rounded-xl border p-5"
          style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
        >
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em] mb-4"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Recent Generations
          </p>
          {recent.length === 0 && (
            <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
              Nothing saved yet — pin captions and scripts from Create or Analyze.
            </p>
          )}
          <div className="flex flex-col gap-3">
            {recent.map((asset) => (
              <div key={asset.id}>
                <div className="flex items-center justify-between mb-1">
                  <span
                    className="text-[10px] font-medium uppercase tracking-[0.08em] px-2 py-0.5 rounded-md"
                    style={{ background: "var(--color-ql-gap)", color: "var(--color-ql-muted)" }}
                  >
                    {ASSET_LABELS[asset.asset_type] ?? asset.asset_type}
                  </span>
                  <span className="text-[10px]" style={{ color: "var(--color-ql-muted)" }}>
                    {timeAgo(asset.created_at)}
                  </span>
                </div>
                <p
                  className="text-xs leading-relaxed line-clamp-2"
                  style={{ color: "var(--color-ql-text)" }}
                >
                  {previewText(asset)}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </motion.div>
  );
}
