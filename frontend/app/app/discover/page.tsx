"use client";

import { useQuery } from "@tanstack/react-query";
import { getVoiceTimeline, getStrategicInsights, getBoostAdvisor } from "@/lib/api";
import VoiceTimelineChart from "@/components/discover/VoiceTimelineChart";
import TimelineNarrative from "@/components/discover/TimelineNarrative";
import StrategicInsightsChart from "@/components/discover/StrategicInsightsChart";
import StrategyBrief from "@/components/discover/StrategyBrief";
import BoostAdvisorCard from "@/components/discover/BoostAdvisor";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="text-base mb-1"
      style={{ fontFamily: "Georgia, serif", color: "var(--color-ql-dark)" }}
    >
      {children}
    </h2>
  );
}

function LoadingBlock() {
  return (
    <div
      className="rounded-xl border p-6 flex items-center justify-center"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <p className="text-xs animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
        Granite is computing…
      </p>
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{
        borderColor: "var(--color-verdict-failed)",
        background: "rgba(163,90,90,0.05)",
      }}
    >
      <p className="text-xs" style={{ color: "var(--color-verdict-failed)" }}>
        {message}
      </p>
    </div>
  );
}

export default function DiscoverPage() {
  const timeline = useQuery({
    queryKey: ["voice-timeline"],
    queryFn: getVoiceTimeline,
  });

  const insights = useQuery({
    queryKey: ["strategic-insights"],
    queryFn: getStrategicInsights,
  });

  const boostAdvisor = useQuery({
    queryKey: ["boost-advisor"],
    queryFn: getBoostAdvisor,
  });

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-10">
      {/* Voice Timeline */}
      <section>
        <SectionHeading>Voice Timeline</SectionHeading>
        <p className="text-xs mb-4" style={{ color: "var(--color-ql-muted)" }}>
          How HotCakes Bakes&apos; creative voice has evolved across content pillars over 9 months.
        </p>

        {timeline.isLoading && <LoadingBlock />}
        {timeline.isError && (
          <ErrorBlock message="Could not load Voice Timeline — is the FastAPI server running?" />
        )}
        {timeline.data && (
          <div
            className="rounded-xl border p-5"
            style={{
              borderColor: "var(--color-ql-border)",
              background: "var(--color-ql-card)",
            }}
          >
            <VoiceTimelineChart data={timeline.data.monthly_pct} pillarLabels={timeline.data.pillar_labels} />
            <TimelineNarrative
              narrative={timeline.data.narrative}
              keyShift={timeline.data.key_shift}
            />
          </div>
        )}
      </section>

      {/* Strategic Insights */}
      <section>
        <SectionHeading>Strategic Insights</SectionHeading>
        <p className="text-xs mb-4" style={{ color: "var(--color-ql-muted)" }}>
          Volume vs. brand richness across content pillars — where to invest, where to pull back.
        </p>

        {insights.isLoading && <LoadingBlock />}
        {insights.isError && (
          <ErrorBlock message="Could not load Strategic Insights — is the FastAPI server running?" />
        )}
        {insights.data && (
          <div
            className="rounded-xl border p-5"
            style={{
              borderColor: "var(--color-ql-border)",
              background: "var(--color-ql-card)",
            }}
          >
            <StrategicInsightsChart scores={insights.data.scores} />
            <StrategyBrief result={insights.data} />
          </div>
        )}
      </section>

      {/* Boost Advisor */}
      <section>
        <SectionHeading>Boost Advisor</SectionHeading>
        <p className="text-xs mb-4" style={{ color: "var(--color-ql-muted)" }}>
          Instagram tells you <em>that</em> you can boost — StyleSync tells you <em>which post</em> to put money behind and why.
        </p>

        {boostAdvisor.isLoading && <LoadingBlock />}
        {boostAdvisor.isError && (
          <ErrorBlock message="Could not load Boost Advisor — is the FastAPI server running?" />
        )}
        {boostAdvisor.data && (
          <div
            className="rounded-xl border p-5"
            style={{
              borderColor: "var(--color-ql-border)",
              background: "var(--color-ql-card)",
            }}
          >
            <p
              className="text-[11px] uppercase tracking-[0.1em] font-medium"
              style={{ color: "var(--color-ql-muted)" }}
            >
              Granite #11 · Engagement-weighted recommendation
            </p>
            <BoostAdvisorCard result={boostAdvisor.data} />
          </div>
        )}
      </section>
    </div>
  );
}
