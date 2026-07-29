"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { getToday, getTodayTrend, getStrategyDiagnoses } from "@/lib/api";
import { seedScriptFromPost, type SeedFormat } from "@/lib/seedScript";
import Collapsible from "@/components/discover/Collapsible";
import SourceBadge from "@/components/discover/SourceBadge";

/**
 * The daily briefing.
 *
 * Every ingredient here already existed — the strategy moves, the winning post,
 * the Why Engine diagnosis, the trend read. They just lived on four different
 * pages, so answering "what do I post today?" meant visiting all four. This
 * composes them into one screen and hands the answer straight to the generator.
 *
 * Loads in two waves: the recommendation is pure Python and instant, the lesson
 * and trend read are Granite and arrive when they arrive. Neither blocks.
 */

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl border p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      {children}
    </div>
  );
}

function StepLabel({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span
        className="inline-flex items-center justify-center h-5 w-5 rounded-full text-[10px] font-medium"
        style={{ background: "var(--color-ql-accent)", color: "white" }}
      >
        {n}
      </span>
      <h2 className="text-base" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
        {children}
      </h2>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>{children}</p>;
}

export default function TodayPage() {
  const router = useRouter();
  const [seeding, setSeeding] = useState(false);
  const [seedError, setSeedError] = useState<string | null>(null);

  const today = useQuery({ queryKey: ["today"], queryFn: getToday });
  // Both Granite-backed and cached server-side — progressive, never blocking.
  const diagnoses = useQuery({ queryKey: ["strategy-diagnoses"], queryFn: getStrategyDiagnoses });
  const trend = useQuery({ queryKey: ["today-trend"], queryFn: getTodayTrend });

  const t = today.data;
  const rec = t?.recommendation;
  const seed = t?.seed_post;
  const lesson = diagnoses.data?.winner_diagnosis;

  async function handleWriteScript() {
    if (!seed || !rec) return;
    setSeeding(true);
    setSeedError(null);
    try {
      await seedScriptFromPost(seed.shortcode, rec.format as SeedFormat);
      router.push("/app/create");
    } catch (e) {
      setSeedError(e instanceof Error ? e.message : "Could not load that post.");
      setSeeding(false);
    }
  }

  return (
    <motion.div
      className="max-w-3xl mx-auto flex flex-col gap-8"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div>
        <h1 className="text-xl mb-1" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          Today
        </h1>
        <Muted>
          {t ? `${t.weekday}, ${t.date} — one post to make, drawn from your own ${t.posts_counted} posts.`
             : "Your morning briefing."}
        </Muted>
      </div>

      {today.isLoading && <Card><Muted>Composing your briefing…</Muted></Card>}
      {today.isError && (
        <div
          className="rounded-xl border p-4"
          style={{
            borderColor: "var(--color-verdict-failed)",
            background: "color-mix(in oklch, var(--color-verdict-failed) 5%, transparent)",
          }}
        >
          <p className="text-xs" style={{ color: "var(--color-verdict-failed)" }}>
            Could not load today&apos;s briefing — is the FastAPI server running?
          </p>
        </div>
      )}

      {t && !rec && (
        <Card>
          <Muted>
            Not enough post history yet to recommend a move. Sync your Instagram account from the
            Dashboard and this fills in.
          </Muted>
        </Card>
      )}

      {rec && (
        <>
          {/* 1 — Today's best post */}
          <section>
            <StepLabel n={1}>Today&apos;s best post</StepLabel>
            <Card>
              <div className="flex items-start justify-between gap-3 mb-3">
                <span
                  className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium"
                  style={{ background: "var(--color-ql-accent)", color: "white" }}
                >
                  {rec.format}
                </span>
                <SourceBadge source={rec.source} />
              </div>

              <h3 className="text-lg mb-1" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
                {rec.title}
              </h3>
              <p className="text-sm mb-3" style={{ color: "var(--color-ql-dark)" }}>{rec.stat}</p>
              <p className="text-sm mb-3" style={{ color: "var(--color-ql-muted)" }}>{rec.detail}</p>

              <div
                className="rounded-lg p-3 text-xs leading-relaxed"
                style={{ background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)", color: "var(--color-ql-muted)" }}
              >
                <strong style={{ color: "var(--color-ql-dark)" }}>Why {rec.format}? </strong>
                {rec.why_format}
                <br />
                <span className="block mt-1.5">{rec.principle}</span>
              </div>
            </Card>
          </section>

          {/* 2 — Ready-to-film script */}
          <section>
            <StepLabel n={2}>Ready-to-film script</StepLabel>
            <Card>
              {seed ? (
                <>
                  <Muted>
                    Building on your best <strong style={{ color: "var(--color-ql-dark)" }}>{seed.pillar}</strong> post —
                    its caption and real numbers get loaded for you, nothing to retype.
                  </Muted>
                  <p
                    className="mt-3 mb-3 text-sm italic pl-3 border-l-2"
                    style={{ color: "var(--color-ql-dark)", borderColor: "var(--color-ql-accent)" }}
                  >
                    “{seed.hook}”
                  </p>
                  <Muted>
                    {seed.reach.toLocaleString()} reach · {seed.sends_per_reach}% sends-per-reach ·{" "}
                    {seed.saves_per_reach}% saves-per-reach
                  </Muted>

                  <button
                    onClick={handleWriteScript}
                    disabled={seeding}
                    className="mt-4 rounded-lg px-4 py-2 text-sm font-medium transition-opacity disabled:opacity-60"
                    style={{ background: "var(--color-ql-accent)", color: "white" }}
                  >
                    {seeding ? "Loading your post…" : `Write today's ${rec.format} →`}
                  </button>
                  {seedError && (
                    <p className="mt-2 text-xs" style={{ color: "var(--color-verdict-failed)" }}>{seedError}</p>
                  )}
                </>
              ) : (
                <Muted>No post in this pillar has enough data to build from yet.</Muted>
              )}
            </Card>
          </section>

          {/* 3 — Story plan (Phase 2 fills this) */}
          <section>
            <StepLabel n={3}>Story plan</StepLabel>
            <Card>
              <Muted>
                Story sequences aren&apos;t generated yet — Reels, carousels and static posts are.
                This is the next format going in.
              </Muted>
            </Card>
          </section>

          {/* 4 — Trend read */}
          <Collapsible
            label="Trend read"
            hint="From your own pillar momentum and comments — not an external trend feed"
          >
            {trend.isLoading && <Muted>Reading your signals…</Muted>}
            {trend.isError && <Muted>Trend read unavailable right now.</Muted>}
            {trend.data && !trend.data.available && (
              <Muted>{trend.data.reason || "No signal to read yet."}</Muted>
            )}
            {trend.data?.available && (
              <div className="flex flex-col gap-3">
                {trend.data.briefing_summary && (
                  <p className="text-sm" style={{ color: "var(--color-ql-dark)" }}>{trend.data.briefing_summary}</p>
                )}
                {!!trend.data.content_hooks?.length && (
                  <div>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-ql-dark)" }}>Hook angles</p>
                    <ul className="list-disc pl-5 space-y-1">
                      {trend.data.content_hooks.slice(0, 4).map((h, i) => (
                        <li key={i} className="text-xs" style={{ color: "var(--color-ql-muted)" }}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {!!trend.data.audience_questions?.length && (
                  <div>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-ql-dark)" }}>
                      What your audience keeps asking
                    </p>
                    <ul className="list-disc pl-5 space-y-1">
                      {trend.data.audience_questions.slice(0, 4).map((q, i) => (
                        <li key={i} className="text-xs" style={{ color: "var(--color-ql-muted)" }}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <Muted>
                  Signals used: your pillar momentum
                  {trend.data.signals_used?.comments_status === "ok" ? " and your recent comments" : ""}.
                  No external trend feed.
                </Muted>
              </div>
            )}
          </Collapsible>

          {/* 5 — Performance lesson */}
          <Collapsible
            label="What your last winner taught you"
            hint="One lesson, and the change to test today"
            defaultOpen
          >
            {diagnoses.isLoading && <Muted>IBM Granite is reading your best post…</Muted>}
            {diagnoses.isError && <Muted>Diagnosis unavailable right now.</Muted>}
            {lesson && (
              <div className="flex flex-col gap-3">
                {lesson.what_worked && (
                  <div>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-ql-dark)" }}>What worked</p>
                    <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>{lesson.what_worked}</p>
                  </div>
                )}
                {lesson.brand_voice_gap && (
                  <div>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-ql-dark)" }}>Voice gap</p>
                    <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>{lesson.brand_voice_gap}</p>
                  </div>
                )}
                {lesson.change_next_time && (
                  <div
                    className="rounded-lg p-3"
                    style={{ background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)" }}
                  >
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-ql-dark)" }}>
                      Test this today
                    </p>
                    <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>{lesson.change_next_time}</p>
                  </div>
                )}
              </div>
            )}
          </Collapsible>
        </>
      )}
    </motion.div>
  );
}
