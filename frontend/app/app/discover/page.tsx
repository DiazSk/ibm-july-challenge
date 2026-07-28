"use client";

import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { getStrategyOverview, getStrategyDiagnoses, getStrategyBrief } from "@/lib/api";
import AlgoScorecard from "@/components/discover/AlgoScorecard";
import PerformanceTimeline from "@/components/discover/PerformanceTimeline";
import WhatWorkedPanel from "@/components/discover/WhatWorkedPanel";
import PlaybookPanel from "@/components/discover/PlaybookPanel";
import ThisWeekHero from "@/components/discover/ThisWeekHero";
import Collapsible from "@/components/discover/Collapsible";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-base mb-1" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
      {children}
    </h2>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border p-5" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}>
      {children}
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="rounded-xl border p-6 flex items-center justify-center" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}>
      <p className="text-xs animate-pulse" style={{ color: "var(--color-ql-muted)" }}>Computing…</p>
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="rounded-xl border p-4" style={{ borderColor: "var(--color-verdict-failed)", background: "color-mix(in oklch, var(--color-verdict-failed) 5%, transparent)" }}>
      <p className="text-xs" style={{ color: "var(--color-verdict-failed)" }}>{message}</p>
    </div>
  );
}

export default function DiscoverPage() {
  // Fast, deterministic — the page's core value loads instantly.
  const overview = useQuery({ queryKey: ["strategy-overview"], queryFn: getStrategyOverview });
  // Slow Granite — progressive enhancement, never blocks the sections above.
  const diagnoses = useQuery({ queryKey: ["strategy-diagnoses"], queryFn: getStrategyDiagnoses });
  const brief = useQuery({ queryKey: ["strategy-brief"], queryFn: getStrategyBrief });

  const ov = overview.data;

  return (
    <motion.div
      className="max-w-3xl mx-auto flex flex-col gap-10"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div>
        <h1 className="text-xl mb-1" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          Strategy
        </h1>
        <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
          One thing to try this week, based on what your own posts already did.
        </p>
      </div>

      {overview.isLoading && <LoadingBlock />}
      {overview.isError && <ErrorBlock message="Could not load Strategy — is the FastAPI server running?" />}

      {ov && (
        <>
          {/* The one recommendation. Everything else is one click away. */}
          {ov.moves.length > 0 && (
            <ThisWeekHero move={ov.moves[0]} proof={ov.what_worked.winner} />
          )}

          {/* What worked vs. what didn't */}
          <section>
            <SectionHeading>What worked, what didn&apos;t</SectionHeading>
            <p className="text-xs mb-4" style={{ color: "var(--color-ql-muted)" }}>
              Your two most instructive posts, and what separates them.
            </p>
            {diagnoses.isError ? (
              <WhatWorkedPanel winner={ov.what_worked.winner} loser={ov.what_worked.loser} loading={false} />
            ) : (
              <WhatWorkedPanel
                winner={ov.what_worked.winner}
                loser={ov.what_worked.loser}
                winnerDiagnosis={diagnoses.data?.winner_diagnosis}
                loserDiagnosis={diagnoses.data?.loser_diagnosis}
                loading={diagnoses.isLoading}
              />
            )}
          </section>

          <Collapsible
            label="Show me the numbers"
            hint={`How your ${ov.scorecard.posts_counted} posts scored, and how that changed over time`}
          >
            <AlgoScorecard scorecard={ov.scorecard} />
            <Card><PerformanceTimeline data={ov.timeline} /></Card>
          </Collapsible>

          {ov.moves.length > 1 && (
            <Collapsible
              label={`${ov.moves.length - 1} more move${ov.moves.length === 2 ? "" : "s"}`}
              hint="Worth doing once this week's change is running"
            >
              <PlaybookPanel
                moves={ov.moves.slice(1)}
                brief={brief.data}
                briefLoading={brief.isLoading}
              />
            </Collapsible>
          )}
        </>
      )}
    </motion.div>
  );
}
