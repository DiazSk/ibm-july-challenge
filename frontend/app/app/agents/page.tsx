"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery, useMutation } from "@tanstack/react-query";
import { runOrchestration, getMemoryStatus } from "@/lib/api";
import type { OrchestrateResponse, TrendBriefing, CampaignBrief } from "@/lib/types";

// ── Agent card data ────────────────────────────────────────────────────────────

const AGENTS = [
  {
    name:        "Trend Agent",
    role:        "The Ideator",
    description: "Monitors the web for micro-trends and synthesises daily content briefings.",
    color:       "var(--color-cluster-1)",
    icon:        TrendIcon,
    taskType:    "trend_briefing",
  },
  {
    name:        "Brand Voice Agent",
    role:        "The Guardian",
    description: "Enforces tone, vocabulary, and structural brand standards across every draft.",
    color:       "var(--color-cluster-2)",
    icon:        GuardianIcon,
    taskType:    null,
  },
  {
    name:        "Copywriting Agent",
    role:        "The Drafter",
    description: "Generates platform-native caption variants enriched by past performance data.",
    color:       "var(--color-cluster-3)",
    icon:        DraftIcon,
    taskType:    null,
  },
  {
    name:        "Critic Agent",
    role:        "The Reviewer",
    description: "Classifies draft failures into typed errors and routes each to the right corrector.",
    color:       "var(--color-cluster-4)",
    icon:        CriticIcon,
    taskType:    null,
  },
  {
    name:        "Visual Agent",
    role:        "The Art Director",
    description: "Produces Midjourney/DALL-E image prompts and shot-by-shot Reel storyboards.",
    color:       "var(--color-cluster-0)",
    icon:        VisualIcon,
    taskType:    null,
  },
  {
    name:        "Analytics Agent",
    role:        "The Strategist",
    description: "Post-mortems posts, pre-scores drafts, and closes the performance feedback loop.",
    color:       "var(--color-cluster-1)",
    icon:        AnalyticsIcon,
    taskType:    null,
  },
  {
    name:        "Community Agent",
    role:        "The Community Builder",
    description: "Triages comments and DMs with priority scoring and dual-tone reply variants.",
    color:       "var(--color-cluster-2)",
    icon:        CommunityIcon,
    taskType:    null,
  },
] as const;

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [campaignResult, setCampaignResult] = useState<OrchestrateResponse | null>(null);
  const [trendResult,    setTrendResult]    = useState<TrendBriefing | null>(null);
  const [activityLog,    setActivityLog]    = useState<string[]>([]);
  const [activeTask,     setActiveTask]     = useState<string | null>(null);
  const [showBrief,      setShowBrief]      = useState(false);
  const [brief,          setBrief]          = useState<CampaignBrief>({
    product: "", occasion: "", platform: "instagram", threshold: 80, useTrends: true,
  });

  // Memory status
  const { data: memStatus } = useQuery({
    queryKey:    ["memory-status"],
    queryFn:     getMemoryStatus,
    staleTime:   30_000,
  });

  // Full campaign mutation
  const campaignMutation = useMutation({
    mutationFn: () =>
      runOrchestration({
        task_type: "full_campaign",
        payload: {
          product:              brief.product  || "bakery special",
          occasion:             brief.occasion || "",
          platform:             brief.platform,
          cluster_id:           0,
          confidence_threshold: brief.threshold,
          ...(brief.useTrends && trendResult
            ? { trend_context: trendResult.content_hooks.slice(0, 2) }
            : {}),
        },
      }),
    onMutate: () => {
      setActiveTask("full_campaign");
      setActivityLog(prev => [`[${timestamp()}] Starting full campaign (goal: ${brief.threshold}/100)…`, ...prev]);
    },
    onSuccess: (data) => {
      setCampaignResult(data);
      setActiveTask(null);
      const summary = [
        `[${timestamp()}] Campaign complete — ${data.convergence_reason ?? "done"} after ${data.cycles} cycles`,
        `[${timestamp()}] Agents: ${data.agents_used.join(", ")}`,
      ];
      setActivityLog(prev => [...summary, ...prev]);
    },
    onError: () => {
      setActiveTask(null);
      setActivityLog(prev => [`[${timestamp()}] Campaign failed — check API logs`, ...prev]);
    },
  });

  // Trend briefing mutation
  const trendMutation = useMutation({
    mutationFn: () =>
      runOrchestration({ task_type: "trend_briefing", payload: { niche: "bakery homemade desserts" } }),
    onMutate: () => {
      setActiveTask("trend_briefing");
      setActivityLog(prev => [`[${timestamp()}] Trend agent searching web…`, ...prev]);
    },
    onSuccess: (data) => {
      setTrendResult((data.results.trend_briefing as TrendBriefing) ?? null);
      setActiveTask(null);
      setActivityLog(prev => [
        `[${timestamp()}] Trend briefing ready — ${(data.results.trend_briefing as TrendBriefing)?.micro_trends?.length ?? 0} trends found`,
        ...prev,
      ]);
    },
    onError: () => {
      setActiveTask(null);
      setActivityLog(prev => [`[${timestamp()}] Trend search failed`, ...prev]);
    },
  });

  const isRunning = campaignMutation.isPending || trendMutation.isPending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-5xl space-y-8 p-6"
    >
      {/* Header */}
      <div>
        <h1
          className="text-2xl"
          style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
        >
          Agent Studio
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--color-ql-muted)" }}>
          7 specialized agents coordinated by an adaptive orchestrator
        </p>
      </div>

      {/* Memory status strip */}
      {memStatus && (
        <div
          className="flex gap-6 rounded-lg border px-5 py-3 text-xs"
          style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
        >
          <span style={{ color: "var(--color-ql-muted)" }}>Memory store</span>
          <MemChip label="Brand voice rules" count={memStatus.semantic}   color="var(--color-cluster-3)" />
          <MemChip label="Past outcomes"     count={memStatus.episodic}   color="var(--color-cluster-1)" />
          <MemChip label="Platform rules"    count={memStatus.procedural} color="var(--color-cluster-2)" />
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        <ActionButton
          label="Run Full Campaign"
          sublabel="Copy → Critic loop → Visual + Analytics"
          onClick={() => setShowBrief(true)}
          loading={activeTask === "full_campaign"}
          disabled={isRunning}
          accent="var(--color-ql-accent)"
        />
        <ActionButton
          label="Get Today's Trends"
          sublabel="Trend + Analytics in parallel"
          onClick={() => trendMutation.mutate()}
          loading={activeTask === "trend_briefing"}
          disabled={isRunning}
          accent="var(--color-cluster-1)"
        />
      </div>

      {/* Campaign brief modal */}
      {showBrief && (
        <CampaignBriefModal
          brief={brief}
          onChange={setBrief}
          hasTrends={!!trendResult}
          onCancel={() => setShowBrief(false)}
          onSubmit={() => { setShowBrief(false); campaignMutation.mutate(); }}
        />
      )}

      {/* Campaign result */}
      {campaignResult && <CampaignResultCard result={campaignResult} />}

      {/* Trend briefing result */}
      {trendResult && <TrendBriefingCard briefing={trendResult} />}

      {/* Agent cards grid */}
      <div>
        <h2
          className="mb-4 text-sm font-medium uppercase tracking-widest"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Pipeline
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {AGENTS.map((agent) => (
            <AgentCard
              key={agent.name}
              agent={agent}
              isActive={
                activeTask === "full_campaign" ||
                (activeTask === "trend_briefing" && agent.name === "Trend Agent")
              }
            />
          ))}
        </div>
      </div>

      {/* Activity feed */}
      {activityLog.length > 0 && (
        <div>
          <h2
            className="mb-3 text-sm font-medium uppercase tracking-widest"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Activity log
          </h2>
          <div
            className="rounded-lg border p-4 font-mono text-xs space-y-1 max-h-48 overflow-y-auto"
            style={{
              borderColor: "var(--color-ql-border)",
              background:  "var(--color-ql-sidebar)",
              color:       "var(--color-ql-muted)",
            }}
          >
            {activityLog.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ── Campaign Brief Modal ──────────────────────────────────────────────────────

function CampaignBriefModal({
  brief, onChange, hasTrends, onCancel, onSubmit,
}: {
  brief:     CampaignBrief;
  onChange:  (b: CampaignBrief) => void;
  hasTrends: boolean;
  onCancel:  () => void;
  onSubmit:  () => void;
}) {
  const set = <K extends keyof CampaignBrief>(k: K, v: CampaignBrief[K]) =>
    onChange({ ...brief, [k]: v });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.45)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div
        className="w-full max-w-md rounded-xl border p-6 space-y-5 shadow-xl"
        style={{ background: "var(--color-ql-card)", borderColor: "var(--color-ql-border)" }}
      >
        <h2
          className="text-base font-medium"
          style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
        >
          Campaign brief
        </h2>

        {/* Product + occasion */}
        <div className="space-y-1.5">
          <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Product / occasion
          </label>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm outline-none"
            style={{
              borderColor: "var(--color-ql-border)",
              background:  "var(--color-ql-sidebar)",
              color:       "var(--color-ql-dark)",
            }}
            placeholder="e.g. Nutella Bomboloni — weekend batch"
            value={`${brief.product}${brief.occasion ? ` — ${brief.occasion}` : ""}`}
            onChange={(e) => {
              const [prod, ...rest] = e.target.value.split(" — ");
              set("product",  prod.trim());
              set("occasion", rest.join(" — ").trim());
            }}
          />
        </div>

        {/* Platform */}
        <div className="space-y-1.5">
          <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Platform
          </label>
          <div className="flex gap-3">
            {(["instagram", "tiktok", "linkedin"] as const).map((p) => (
              <button
                key={p}
                onClick={() => set("platform", p)}
                className="rounded-full border px-3 py-1 text-xs capitalize transition-colors"
                style={{
                  borderColor: brief.platform === p ? "var(--color-ql-accent)" : "var(--color-ql-border)",
                  background:  brief.platform === p
                    ? "color-mix(in oklch, var(--color-ql-accent) 12%, transparent)"
                    : "transparent",
                  color: brief.platform === p ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Quality gate */}
        <div className="space-y-1.5">
          <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Quality gate
          </label>
          <div className="flex gap-3">
            {([
              { value: 70 as const, label: "Good enough" },
              { value: 80 as const, label: "Solid" },
              { value: 90 as const, label: "High bar" },
            ]).map(({ value, label }) => (
              <button
                key={value}
                onClick={() => set("threshold", value)}
                className="flex-1 rounded-md border py-1.5 text-xs transition-colors"
                style={{
                  borderColor: brief.threshold === value ? "var(--color-ql-accent)" : "var(--color-ql-border)",
                  background:  brief.threshold === value
                    ? "color-mix(in oklch, var(--color-ql-accent) 12%, transparent)"
                    : "transparent",
                  color: brief.threshold === value ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
                }}
              >
                {label} <span className="opacity-60">({value})</span>
              </button>
            ))}
          </div>
        </div>

        {/* Trend context */}
        <div
          className="flex items-center gap-3 rounded-md border px-3 py-2.5"
          style={{
            borderColor: "var(--color-ql-border)",
            background:  "var(--color-ql-sidebar)",
            opacity:     hasTrends ? 1 : 0.45,
          }}
        >
          <input
            type="checkbox"
            id="use-trends"
            disabled={!hasTrends}
            checked={brief.useTrends && hasTrends}
            onChange={(e) => set("useTrends", e.target.checked)}
            className="h-3.5 w-3.5 accent-[var(--color-ql-accent)]"
          />
          <label
            htmlFor="use-trends"
            className="flex-1 cursor-pointer text-xs"
            style={{ color: "var(--color-ql-dark)" }}
          >
            Inject today's trend hooks
          </label>
          <span className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
            {hasTrends ? "briefing ready" : "run trend first"}
          </span>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-1">
          <button
            onClick={onCancel}
            className="rounded-md border px-4 py-1.5 text-xs transition-opacity hover:opacity-70"
            style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            className="rounded-md px-4 py-1.5 text-xs font-medium transition-opacity hover:opacity-80"
            style={{ background: "var(--color-ql-accent)", color: "#fff" }}
          >
            Run Campaign
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MemChip({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      <span style={{ color: "var(--color-ql-dark)" }}>{count}</span>
      <span style={{ color: "var(--color-ql-muted)" }}>{label}</span>
    </span>
  );
}

function ActionButton({
  label, sublabel, onClick, loading, disabled, accent,
}: {
  label: string; sublabel: string; onClick: () => void;
  loading: boolean; disabled: boolean; accent: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex flex-col items-start rounded-lg border px-5 py-3 text-left transition-opacity disabled:opacity-50"
      style={{ borderColor: accent, background: "var(--color-ql-card)" }}
    >
      <span className="flex items-center gap-2 text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
        {loading && <Spinner />}
        {label}
      </span>
      <span className="mt-0.5 text-xs" style={{ color: "var(--color-ql-muted)" }}>{sublabel}</span>
    </button>
  );
}

function AgentCard({
  agent, isActive,
}: {
  agent: typeof AGENTS[number]; isActive: boolean;
}) {
  const Icon = agent.icon;
  return (
    <div
      className="rounded-lg border p-4 transition-shadow"
      style={{
        borderColor: isActive ? agent.color : "var(--color-ql-border)",
        background:  "var(--color-ql-card)",
        boxShadow:   isActive ? `0 0 0 1px ${agent.color}` : undefined,
      }}
    >
      <div className="flex items-start gap-3">
        <div
          className="grid h-8 w-8 shrink-0 place-items-center rounded-md"
          style={{ background: `color-mix(in oklch, ${agent.color} 15%, transparent)` }}
        >
          <Icon color={agent.color} />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
            {agent.name}
          </p>
          <p className="text-[11px]" style={{ color: agent.color }}>{agent.role}</p>
        </div>
      </div>
      <p className="mt-3 text-xs leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
        {agent.description}
      </p>
      {isActive && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px]" style={{ color: agent.color }}>
          <Spinner size={10} /> Running…
        </div>
      )}
    </div>
  );
}

function CampaignResultCard({ result }: { result: OrchestrateResponse }) {
  const draft      = (result.results.draft as string) ?? "";
  const confidence = (result.results.confidence as { score?: number; rationale?: string }) ?? {};
  const imagePrompt = (result.results.image_prompt as { prompt?: string }) ?? {};
  const history    = (result.results.critic_history as { cycle: number; error_type: string; flagged: string }[]) ?? [];
  const trajectory = (result.results.confidence_trajectory as number[]) ?? [];
  const convergence = result.convergence_reason ?? "max_cycles";

  return (
    <div
      className="rounded-lg border p-5 space-y-4"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
          Campaign result
        </h3>
        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--color-ql-muted)" }}>
          <ConvergenceBadge reason={convergence} />
          <span>·</span>
          <span>{result.agents_used.length} agents</span>
          <span>·</span>
          <span>{result.cycles} cycle{result.cycles !== 1 ? "s" : ""}</span>
        </div>
      </div>

      {/* Draft caption */}
      {draft && (
        <div
          className="rounded-md p-4 text-sm leading-relaxed"
          style={{ background: "var(--color-ql-sidebar)", color: "var(--color-ql-dark)" }}
        >
          {draft}
        </div>
      )}

      {/* Critic history */}
      {history.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Critic routing
          </p>
          {history.map((h) => (
            <div key={h.cycle} className="flex items-center gap-2 text-xs">
              <ErrorTypeBadge type={h.error_type} />
              {h.flagged && (
                <span style={{ color: "var(--color-ql-muted)" }}>"{h.flagged}"</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Confidence + trajectory + image prompt */}
      <div className="flex flex-wrap gap-4 text-xs" style={{ color: "var(--color-ql-muted)" }}>
        {confidence.score != null && (
          <span>
            Confidence:{" "}
            <strong style={{ color: "var(--color-ql-dark)" }}>{confidence.score}/100</strong>
          </span>
        )}
        {trajectory.length > 0 && (
          <span>
            Path:{" "}
            <span style={{ color: "var(--color-ql-dark)" }}>
              {trajectory.join(" → ")}
            </span>
          </span>
        )}
        {imagePrompt.prompt && (
          <span className="truncate max-w-xs">
            Image prompt: <em>{imagePrompt.prompt.slice(0, 80)}…</em>
          </span>
        )}
      </div>

      {/* Agent chain */}
      <div className="flex flex-wrap gap-1.5">
        {result.agents_used.map((a, i) => (
          <span
            key={i}
            className="rounded-full px-2 py-0.5 text-[11px]"
            style={{ background: "var(--color-ql-sidebar)", color: "var(--color-ql-muted)" }}
          >
            {a}
          </span>
        ))}
      </div>
    </div>
  );
}

function ConvergenceBadge({ reason }: { reason: string }) {
  const map: Record<string, { label: string; color: string }> = {
    goal_met:   { label: "Goal met",               color: "var(--color-verdict-succeeded)" },
    plateau:    { label: "Quality plateau",         color: "var(--color-cluster-3)" },
    factual_gap:{ label: "Factual gap",             color: "var(--color-verdict-failed)" },
    max_cycles: { label: "Max cycles reached",      color: "var(--color-ql-muted)" },
  };
  const { label, color } = map[reason] ?? map["max_cycles"];
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
      style={{ background: `color-mix(in oklch, ${color} 15%, transparent)`, color }}
    >
      {label}
    </span>
  );
}

function TrendBriefingCard({ briefing }: { briefing: TrendBriefing }) {
  return (
    <div
      className="rounded-lg border p-5 space-y-4"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
          Trend briefing
        </h3>
        <span className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
          {briefing.sources_searched} sources
        </span>
      </div>

      <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
        {briefing.briefing_summary}
      </p>

      {briefing.micro_trends.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Micro-trends
          </p>
          <div className="space-y-2">
            {briefing.micro_trends.slice(0, 3).map((t, i) => (
              <div key={i} className="flex items-start gap-2">
                <UrgencyDot urgency={t.urgency} />
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>{t.trend}</p>
                  <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>{t.relevance}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {briefing.content_hooks.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Content hooks
          </p>
          <div className="space-y-1">
            {briefing.content_hooks.slice(0, 3).map((h, i) => (
              <p key={i} className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
                "{h}"
              </p>
            ))}
          </div>
        </div>
      )}

      {briefing.suggested_angles.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Suggested angles
          </p>
          <div className="flex flex-wrap gap-2">
            {briefing.suggested_angles.slice(0, 4).map((a, i) => (
              <span
                key={i}
                className="rounded-full border px-3 py-1 text-xs"
                style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-dark)" }}
              >
                {a.angle} · {a.format}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ErrorTypeBadge({ type }: { type: string }) {
  const map: Record<string, { label: string; color: string }> = {
    ai_slop:         { label: "AI slop",       color: "var(--color-verdict-failed)" },
    off_brand_vocab: { label: "Off-brand",      color: "var(--color-cluster-3)" },
    wrong_platform:  { label: "Wrong platform", color: "var(--color-cluster-1)" },
    factual_gap:     { label: "Factual gap",    color: "var(--color-verdict-underperformed)" },
    approved:        { label: "Approved",       color: "var(--color-verdict-succeeded)" },
  };
  const { label, color } = map[type] ?? { label: type, color: "var(--color-ql-muted)" };
  return (
    <span
      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
      style={{ background: `color-mix(in oklch, ${color} 15%, transparent)`, color }}
    >
      {label}
    </span>
  );
}

function UrgencyDot({ urgency }: { urgency: "high" | "medium" | "low" }) {
  const colors = { high: "var(--color-verdict-failed)", medium: "var(--color-cluster-1)", low: "var(--color-ql-muted)" };
  return (
    <span
      className="mt-1 h-2 w-2 shrink-0 rounded-full"
      style={{ background: colors[urgency] ?? colors.low }}
    />
  );
}

function Spinner({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="animate-spin"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
    </svg>
  );
}

function timestamp() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function TrendIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <path d="M2 14l4-4 4 2 4-6 4 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function GuardianIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <path d="M10 2l6 3v5c0 3.5-2.5 6-6 7-3.5-1-6-3.5-6-7V5l6-3z" strokeLinejoin="round" />
    </svg>
  );
}
function DraftIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <path d="M4 4h12v12H4z" strokeLinejoin="round" />
      <path d="M7 8h6M7 11h4" strokeLinecap="round" />
    </svg>
  );
}
function CriticIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <circle cx="10" cy="10" r="7" />
      <path d="M10 7v3M10 13.5v.5" strokeLinecap="round" />
    </svg>
  );
}
function VisualIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <rect x="3" y="4" width="14" height="12" rx="1" />
      <circle cx="7.5" cy="8.5" r="1.5" />
      <path d="M3 14l4-3 3 3 3-4 4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function AnalyticsIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <path d="M2 16l4-6 4 3 4-8 4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function CommunityIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6">
      <circle cx="7" cy="8" r="3" />
      <circle cx="14" cy="8" r="2.5" />
      <path d="M2 16c0-2.5 2-4 5-4s5 1.5 5 4" strokeLinecap="round" />
      <path d="M14 12c2 0 4 1 4 3" strokeLinecap="round" />
    </svg>
  );
}
