"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  startAgentRun,
  getAgentRun,
  answerAgentRun,
  getMemoryStatus,
  saveAsset,
  reflectPlaybook,
  getReflectStatus,
  getPlaybookRules,
} from "@/lib/api";
import type { AgentRunState, AgentTraceEntry, AutopilotPost, ReflectJob, PlaybookRule } from "@/lib/types";

// The agent's toolbelt — the specialized agents it can call while it works.
const TOOLBELT = [
  { name: "Analytics Agent", role: "assesses brand gaps + scores drafts", color: "var(--color-cluster-1)", icon: AnalyticsIcon },
  { name: "Trend Agent", role: "pulls live web trends", color: "var(--color-cluster-1)", icon: TrendIcon },
  { name: "Copywriting Agent", role: "drafts + rewrites captions", color: "var(--color-cluster-3)", icon: DraftIcon },
  { name: "Critic Agent", role: "flags typed failures", color: "var(--color-cluster-4)", icon: CriticIcon },
  { name: "Brand Voice Agent", role: "enforces your voice", color: "var(--color-cluster-2)", icon: GuardianIcon },
  { name: "Visual Agent", role: "writes image direction", color: "var(--color-cluster-0)", icon: VisualIcon },
] as const;

const PLATFORMS = ["instagram", "tiktok"] as const;
const GATES = [
  { value: 70, label: "Good enough" },
  { value: 80, label: "Solid" },
  { value: 90, label: "High bar" },
] as const;

export default function AgentsPage() {
  const queryClient = useQueryClient();

  const [jobId, setJobId] = useState<string | null>(null);
  const [steer, setSteer] = useState("");
  const [targetCount, setTargetCount] = useState(3);
  const [platform, setPlatform] = useState<(typeof PLATFORMS)[number]>("instagram");
  const [threshold, setThreshold] = useState<70 | 80 | 90>(80);
  const [answerDraft, setAnswerDraft] = useState("");
  const savedRef = useRef<string | null>(null);

  // Adopt a run launched elsewhere (e.g. JARVIS voice → /app/agents?run=<job_id>)
  useEffect(() => {
    const run = new URLSearchParams(window.location.search).get("run");
    if (run) setJobId(run);
  }, []);

  const { data: memStatus } = useQuery({ queryKey: ["memory-status"], queryFn: getMemoryStatus, staleTime: 30_000 });

  const { data: run } = useQuery<AgentRunState>({
    queryKey: ["agent-run", jobId],
    queryFn: () => getAgentRun(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "running" || s === "awaiting_input" ? 1500 : false;
    },
    refetchIntervalInBackground: true,
  });

  const startMutation = useMutation({
    mutationFn: () =>
      startAgentRun({ steer, target_count: targetCount, platform, confidence_threshold: threshold }),
    onSuccess: (data) => {
      savedRef.current = null;
      setAnswerDraft("");
      setJobId(data.job_id);
    },
  });

  const answerMutation = useMutation({
    mutationFn: (answer: string) => answerAgentRun(jobId as string, answer),
    onSuccess: () => {
      setAnswerDraft("");
      queryClient.invalidateQueries({ queryKey: ["agent-run", jobId] });
    },
  });

  // Once the run finishes, drop the produced posts into the Workbench (once).
  useEffect(() => {
    if (run?.status !== "done" || !jobId || savedRef.current === jobId) return;
    savedRef.current = jobId;
    (async () => {
      for (const p of run.posts) {
        if (!p.caption) continue;
        try {
          await saveAsset({
            asset_type: "autopilot_post",
            content: {
              caption: p.caption,
              pillar: p.pillar,
              angle: p.angle,
              rationale: p.rationale,
              image_prompt: p.image_prompt,
              confidence: p.confidence,
            },
            cluster_id: p.cluster_id,
            source_tab: "autopilot",
          });
        } catch {
          // silent — a failed save shouldn't break the results view
        }
      }
      queryClient.invalidateQueries({ queryKey: ["workbench"] });
    })();
  }, [run?.status, jobId, run?.posts, queryClient]);

  const isBusy = run?.status === "running" || run?.status === "awaiting_input" || startMutation.isPending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-5xl space-y-8 p-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          Autopilot
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--color-ql-muted)" }}>
          An autonomous agent that plans your week and produces every post &mdash; asking you only when it&apos;s genuinely unsure.
        </p>
      </div>

      {/* Memory strip */}
      {memStatus && (
        <div
          className="flex flex-wrap gap-6 rounded-lg border px-5 py-3 text-xs"
          style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
        >
          <span style={{ color: "var(--color-ql-muted)" }}>Agent memory</span>
          <MemChip label="Brand voice rules" count={memStatus.semantic} color="var(--color-cluster-3)" />
          <MemChip label="Past outcomes" count={memStatus.episodic} color="var(--color-cluster-1)" />
          <MemChip label="Platform rules" count={memStatus.procedural} color="var(--color-cluster-2)" />
        </div>
      )}

      {/* Start card */}
      <div
        className="rounded-xl border p-5 space-y-4"
        style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
      >
        <div className="space-y-1.5">
          <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>
            Optional steer (leave blank to let it decide)
          </label>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm outline-none"
            style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-sidebar)", color: "var(--color-ql-dark)" }}
            placeholder="e.g. lean into Ramadan gifting, or revive Behind the Scenes"
            value={steer}
            onChange={(e) => setSteer(e.target.value)}
            disabled={isBusy}
          />
        </div>

        <div className="flex flex-wrap gap-6">
          {/* Post count */}
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>Posts</label>
            <div className="flex gap-2">
              {[2, 3, 4, 5].map((n) => (
                <Pill key={n} active={targetCount === n} onClick={() => setTargetCount(n)} disabled={isBusy}>
                  {n}
                </Pill>
              ))}
            </div>
          </div>
          {/* Platform */}
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>Platform</label>
            <div className="flex gap-2">
              {PLATFORMS.map((p) => (
                <Pill key={p} active={platform === p} onClick={() => setPlatform(p)} disabled={isBusy} className="capitalize">
                  {p}
                </Pill>
              ))}
            </div>
          </div>
          {/* Gate */}
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-wider" style={{ color: "var(--color-ql-muted)" }}>Quality gate</label>
            <div className="flex gap-2">
              {GATES.map((g) => (
                <Pill key={g.value} active={threshold === g.value} onClick={() => setThreshold(g.value)} disabled={isBusy}>
                  {g.label} <span className="opacity-60">({g.value})</span>
                </Pill>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={() => startMutation.mutate()}
          disabled={isBusy}
          className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium disabled:opacity-50"
          style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
        >
          {isBusy && <Spinner />}
          {isBusy ? "Autopilot is working…" : "Plan my week"}
        </button>
      </div>

      {/* Pending question — the human-in-the-loop moment */}
      {run?.status === "awaiting_input" && run.pending_question && (
        <div
          className="rounded-xl border p-5 space-y-3"
          style={{ borderColor: "var(--color-ql-accent)", background: "color-mix(in oklch, var(--color-ql-accent) 7%, transparent)" }}
        >
          <p className="text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: "var(--color-ql-accent)" }}>
            The agent needs your call
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
            {run.pending_question.question}
          </p>
          <div className="flex flex-wrap gap-2">
            {run.pending_question.options.map((opt, i) => (
              <button
                key={i}
                onClick={() => answerMutation.mutate(opt)}
                disabled={answerMutation.isPending}
                className="rounded-lg border px-3 py-1.5 text-xs disabled:opacity-50"
                style={{ borderColor: "var(--color-ql-accent)", color: "var(--color-ql-accent)" }}
              >
                {opt}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              className="flex-1 rounded-md border px-3 py-2 text-sm outline-none"
              style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-sidebar)", color: "var(--color-ql-dark)" }}
              placeholder="…or type your own answer"
              value={answerDraft}
              onChange={(e) => setAnswerDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && answerDraft.trim()) answerMutation.mutate(answerDraft.trim()); }}
            />
            <button
              onClick={() => answerDraft.trim() && answerMutation.mutate(answerDraft.trim())}
              disabled={answerMutation.isPending || !answerDraft.trim()}
              className="rounded-md px-4 py-2 text-xs font-medium disabled:opacity-50"
              style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
            >
              Answer
            </button>
          </div>
        </div>
      )}

      {/* Live reasoning trace */}
      {run && run.trace.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-medium uppercase tracking-widest" style={{ color: "var(--color-ql-muted)" }}>
            {run.status === "done" ? "How it thought" : "Thinking live…"}
          </h2>
          <div
            className="rounded-lg border p-4 space-y-1.5 max-h-72 overflow-y-auto"
            style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-sidebar)" }}
          >
            {run.trace.map((e, i) => (
              <TraceRow key={i} entry={e} />
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {run?.status === "error" && (
        <div className="rounded-lg border p-4 text-sm" style={{ borderColor: "var(--color-verdict-failed)", color: "var(--color-verdict-failed)" }}>
          Autopilot hit an error: {run.error}
        </div>
      )}

      {/* Results */}
      {run?.status === "done" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-widest" style={{ color: "var(--color-ql-muted)" }}>
              This week&apos;s plan &mdash; {run.posts.length} posts
            </h2>
            <span className="text-xs" style={{ color: "var(--color-ql-muted)" }}>saved to Workbench</span>
          </div>
          {run.reasoning && (
            <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
              <span className="font-medium" style={{ color: "var(--color-ql-accent)" }}>Strategy: </span>
              {run.reasoning}
            </p>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {run.posts.map((p) => <PostCard key={p.index} post={p} />)}
          </div>
        </div>
      )}

      {/* Self-improving playbook */}
      <PlaybookPanel />

      {/* Toolbelt */}
      <div>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-widest" style={{ color: "var(--color-ql-muted)" }}>
          The agent&apos;s toolbelt
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {TOOLBELT.map((tool) => {
            const Icon = tool.icon;
            return (
              <div
                key={tool.name}
                className="flex items-start gap-3 rounded-lg border p-4"
                style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
              >
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-md" style={{ background: `color-mix(in oklch, ${tool.color} 15%, transparent)` }}>
                  <Icon color={tool.color} />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>{tool.name}</p>
                  <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>{tool.role}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}

// ── Self-improving playbook panel ──────────────────────────────────────────────

function PlaybookPanel() {
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);

  const { data: rules } = useQuery<PlaybookRule[]>({
    queryKey: ["playbook-rules"],
    queryFn: getPlaybookRules,
    staleTime: 30_000,
  });

  const { data: job } = useQuery<ReflectJob>({
    queryKey: ["reflect", jobId],
    queryFn: () => getReflectStatus(jobId as string),
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 1500 : false),
    refetchIntervalInBackground: true,
  });

  const start = useMutation({ mutationFn: reflectPlaybook, onSuccess: (d) => setJobId(d.job_id) });

  useEffect(() => {
    if (job?.status === "done") qc.invalidateQueries({ queryKey: ["playbook-rules"] });
  }, [job?.status, qc]);

  const result = job?.status === "done" ? job.result : null;
  const busy = start.isPending || job?.status === "running";

  return (
    <div>
      <h2 className="mb-1 text-sm font-medium uppercase tracking-widest" style={{ color: "var(--color-ql-muted)" }}>
        Self-improving playbook
      </h2>
      <p className="mb-4 text-xs" style={{ color: "var(--color-ql-muted)" }}>
        The agent learns from your real post outcomes and rewrites the rules it writes captions by.
      </p>

      <button
        onClick={() => start.mutate()}
        disabled={busy}
        className="text-[12px] px-4 py-2 rounded-lg font-medium mb-3 disabled:opacity-50"
        style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
      >
        {busy ? "Reflecting on what's working…" : "Reflect on what's working"}
      </button>

      {result && (
        <div className="rounded-xl border p-4 mb-4"
          style={{ borderColor: "var(--color-ql-accent)", background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)" }}>
          <p className="text-[10px] font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--color-ql-accent)" }}>
            What it learned {result.winners + result.losers > 0 ? `(from ${result.winners} wins · ${result.losers} misses)` : ""}
          </p>
          <p className="text-sm leading-relaxed mb-2" style={{ color: "var(--color-ql-dark)" }}>{result.learned}</p>
          {result.rules.length > 0 && (
            <ul className="flex flex-col gap-1.5 mt-2">
              {result.rules.map((r, i) => (
                <li key={i} className="text-xs leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
                  <span className="font-medium" style={{ color: "var(--color-ql-accent)" }}>+ {r.rule_name}: </span>
                  {r.instruction}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {rules && rules.length > 0 && (
        <div className="rounded-lg border p-4" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}>
          <p className="text-[10px] font-medium uppercase tracking-[0.1em] mb-2" style={{ color: "var(--color-ql-muted)" }}>
            Current playbook · {rules.length} rules
          </p>
          <ul className="flex flex-col gap-2">
            {rules.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
                <span className="shrink-0 text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded mt-0.5"
                  style={{
                    background: r.source === "reflection" ? "color-mix(in oklch, var(--color-ql-accent) 15%, transparent)" : "var(--color-ql-sidebar)",
                    color: r.source === "reflection" ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
                  }}>
                  {r.source === "reflection" ? "learned" : "seed"}
                </span>
                <span>{r.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Pill({
  children, active, onClick, disabled, className = "",
}: { children: React.ReactNode; active: boolean; onClick: () => void; disabled?: boolean; className?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-full border px-3 py-1 text-xs transition-colors disabled:opacity-50 ${className}`}
      style={{
        borderColor: active ? "var(--color-ql-accent)" : "var(--color-ql-border)",
        background: active ? "color-mix(in oklch, var(--color-ql-accent) 12%, transparent)" : "transparent",
        color: active ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
      }}
    >
      {children}
    </button>
  );
}

const PHASE_COLOR: Record<string, string> = {
  start: "var(--color-ql-muted)",
  think: "var(--color-cluster-1)",
  act: "var(--color-cluster-3)",
  done: "var(--color-verdict-succeeded)",
};

function TraceRow({ entry }: { entry: AgentTraceEntry }) {
  const color = PHASE_COLOR[entry.phase] ?? "var(--color-ql-muted)";
  return (
    <div className="flex items-baseline gap-2 text-xs">
      <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px] uppercase tracking-wider" style={{ background: `color-mix(in oklch, ${color} 15%, transparent)`, color }}>
        {entry.post ? `${entry.phase} ${entry.post}` : entry.phase}
      </span>
      <span style={{ color: "var(--color-ql-dark)" }}>{entry.label}</span>
      {entry.detail && <span className="truncate" style={{ color: "var(--color-ql-muted)" }}>&mdash; {entry.detail}</span>}
    </div>
  );
}

function PostCard({ post }: { post: AutopilotPost }) {
  return (
    <div className="rounded-xl border p-4 flex flex-col gap-2" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-[0.08em]" style={{ color: "var(--color-ql-accent)" }}>
          {post.pillar}
        </span>
        <div className="flex items-center gap-2">
          {post.confidence != null && (
            <span className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>{post.confidence}/100</span>
          )}
          <ConvergenceBadge reason={post.convergence_reason} />
        </div>
      </div>
      <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>{post.angle}</p>
      <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--color-ql-dark)" }}>{post.caption}</p>
      {post.rationale && (
        <p className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
          <span className="font-medium">Why: </span>{post.rationale}
        </p>
      )}
      {post.needs_review && (
        <span className="text-[10px] font-medium" style={{ color: "var(--color-verdict-underperformed)" }}>
          Flagged for your review
        </span>
      )}
    </div>
  );
}

function ConvergenceBadge({ reason }: { reason: string }) {
  const map: Record<string, { label: string; color: string }> = {
    goal_met: { label: "Goal met", color: "var(--color-verdict-succeeded)" },
    plateau: { label: "Plateau", color: "var(--color-cluster-3)" },
    factual_gap: { label: "Factual gap", color: "var(--color-verdict-failed)" },
    max_cycles: { label: "Max cycles", color: "var(--color-ql-muted)" },
  };
  const { label, color } = map[reason] ?? map["max_cycles"];
  return (
    <span className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: `color-mix(in oklch, ${color} 15%, transparent)`, color }}>
      {label}
    </span>
  );
}

function MemChip({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      <span style={{ color: "var(--color-ql-dark)" }}>{count}</span>
      <span style={{ color: "var(--color-ql-muted)" }}>{label}</span>
    </span>
  );
}

function Spinner({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
    </svg>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function TrendIcon({ color }: { color: string }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6"><path d="M2 14l4-4 4 2 4-6 4 2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
function GuardianIcon({ color }: { color: string }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6"><path d="M10 2l6 3v5c0 3.5-2.5 6-6 7-3.5-1-6-3.5-6-7V5l6-3z" strokeLinejoin="round" /></svg>;
}
function DraftIcon({ color }: { color: string }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6"><path d="M4 4h12v12H4z" strokeLinejoin="round" /><path d="M7 8h6M7 11h4" strokeLinecap="round" /></svg>;
}
function CriticIcon({ color }: { color: string }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6"><circle cx="10" cy="10" r="7" /><path d="M10 7v3M10 13.5v.5" strokeLinecap="round" /></svg>;
}
function VisualIcon({ color }: { color: string }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6"><rect x="3" y="4" width="14" height="12" rx="1" /><circle cx="7.5" cy="8.5" r="1.5" /><path d="M3 14l4-3 3 3 3-4 4 4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
function AnalyticsIcon({ color }: { color: string }) {
  return <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke={color} strokeWidth="1.6"><path d="M2 16l4-6 4 3 4-8 4 4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
