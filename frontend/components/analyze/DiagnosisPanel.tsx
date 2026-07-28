"use client";

import { useEffect, useState } from "react";
import type { WhyEngineResult, PostDiagnosis, VerdictLabel, RepurposeStatus } from "@/lib/types";
import ConfidenceBadge from "@/components/shared/ConfidenceBadge";
import { getRepurposeStatus } from "@/lib/api";

interface Props {
  /**
   * Accepts a full WhyEngineResult (manual form) or a per-post PostDiagnosis
   * from the Diagnose list, which has no recovery_brief/confidence/repurpose id.
   */
  result: WhyEngineResult | PostDiagnosis;
}

const VERDICT_CONFIG: Record<
  VerdictLabel,
  { bg: string; border: string; text: string; label: string }
> = {
  Succeeded: {
    bg: "color-mix(in oklch, var(--color-verdict-succeeded) 8%, transparent)",
    border: "var(--color-verdict-succeeded)",
    text: "var(--color-verdict-succeeded)",
    label: "Succeeded",
  },
  Underperformed: {
    bg: "color-mix(in oklch, var(--color-verdict-underperformed) 8%, transparent)",
    border: "var(--color-verdict-underperformed)",
    text: "var(--color-verdict-underperformed)",
    label: "Underperformed",
  },
  Failed: {
    bg: "color-mix(in oklch, var(--color-verdict-failed) 8%, transparent)",
    border: "var(--color-verdict-failed)",
    text: "var(--color-verdict-failed)",
    label: "Failed",
  },
};

function RepurposeBanner({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<RepurposeStatus | null>(null);
  const [lost, setLost] = useState(false);

  useEffect(() => {
    let missed = 0;
    const id = setInterval(async () => {
      try {
        const s = await getRepurposeStatus(jobId);
        setStatus(s);
        missed = 0;
        if (s.status === "done" || s.status === "error") clearInterval(id);
      } catch {
        missed += 1;
        if (missed >= 3) {
          clearInterval(id);
          setLost(true);
        }
      }
    }, 3000);
    return () => clearInterval(id);
  }, [jobId]);

  if (lost) {
    return (
      <div className="rounded-xl border p-3.5" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}>
        <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
          Job may have been interrupted — check Workbench for any formats that completed.
        </p>
      </div>
    );
  }

  if (!status || status.status === "error") return null;

  return (
    <div
      className="rounded-xl border p-3.5"
      style={{ borderColor: "var(--color-ql-accent)", background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)" }}
    >
      <p className="text-xs font-medium mb-1" style={{ color: "var(--color-ql-accent)" }}>
        {status.status === "done"
          ? "3 formats ready — check Workbench →"
          : "Great post — auto-generating a Reel, Carousel, and Static version..."}
      </p>
      {status.status !== "done" && (
        <div className="h-1 rounded-full overflow-hidden mt-2" style={{ background: "var(--color-ql-border)" }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${status.progress}%`, background: "var(--color-ql-accent)" }}
          />
        </div>
      )}
      <p className="text-[11px] mt-1.5" style={{ color: "var(--color-ql-muted)" }}>
        {status.message}
      </p>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="text-[10px] font-medium uppercase tracking-[0.12em] mb-1.5"
      style={{ color: "var(--color-ql-muted)" }}
    >
      {children}
    </p>
  );
}

// The backend decorates verdict_label with symbols (e.g. "✓  Succeeded"), which never
// exact-matches VERDICT_CONFIG's plain keys — so key off the raw `verdict` field instead.
function resolveVerdictKey(result: WhyEngineResult | PostDiagnosis): VerdictLabel {
  const raw = `${result.verdict} ${result.verdict_label}`.toLowerCase();
  if (raw.includes("succeed")) return "Succeeded";
  if (raw.includes("fail")) return "Failed";
  return "Underperformed";
}

export default function DiagnosisPanel({ result }: Props) {
  const conf = VERDICT_CONFIG[resolveVerdictKey(result)];
  // Present only on the manual-form result, absent on a per-post diagnosis.
  const extras = result as Partial<WhyEngineResult>;

  const changeItems = result.change_next_time
    .split(/[\n•–-]+/)
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <div className="flex flex-col gap-4 mt-6">
      {/* Verdict banner */}
      <div
        className="rounded-xl border px-5 py-4"
        style={{ background: conf.bg, borderColor: conf.border }}
      >
        <div className="flex items-center gap-3 mb-2">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: conf.text }}
          />
          <span
            className="text-xs font-medium uppercase tracking-[0.12em]"
            style={{ color: conf.text }}
          >
            {conf.label}
          </span>
          {extras.confidence && (
            <ConfidenceBadge score={extras.confidence.score} rationale={extras.confidence.rationale} />
          )}
        </div>
        <p
          className="text-sm leading-relaxed"
          style={{
            color: "var(--color-ql-dark)",
            fontFamily: "var(--font-display)",
          }}
        >
          {result.verdict}
        </p>
      </div>

      {extras.repurpose_job_id && <RepurposeBanner jobId={extras.repurpose_job_id} />}

      {/* Diagnosis */}
      <Card>
        <SectionLabel>Diagnosis</SectionLabel>
        <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
          {result.diagnosis}
        </p>
      </Card>

      {/* What worked / failed */}
      <div className="grid grid-cols-2 gap-3">
        <Card>
          <SectionLabel>What Worked</SectionLabel>
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
            {result.what_worked}
          </p>
        </Card>
        <Card>
          <SectionLabel>What Failed</SectionLabel>
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
            {result.what_failed}
          </p>
        </Card>
      </div>

      {/* Brand voice gap */}
      <div
        className="rounded-xl border p-4"
        style={{
          background: "var(--color-ql-gap)",
          borderColor: "var(--color-ql-border)",
        }}
      >
        <SectionLabel>Brand Voice Gap</SectionLabel>
        <p className="text-sm leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
          {result.brand_voice_gap}
        </p>
      </div>

      {/* Change next time */}
      <Card>
        <SectionLabel>Change Next Time</SectionLabel>
        <ul className="flex flex-col gap-1.5">
          {changeItems.map((item, i) => (
            <li key={i} className="flex items-start gap-2">
              <span
                className="mt-1.5 w-1 h-1 rounded-full shrink-0"
                style={{ background: "var(--color-ql-accent)" }}
              />
              <span className="text-xs leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
                {item}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
