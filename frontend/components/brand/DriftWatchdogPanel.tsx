"use client";

import { useState } from "react";
import { checkBrandDrift } from "@/lib/api";
import type { DriftCheckResult } from "@/lib/types";

const SEVERITY_COLOR: Record<string, string> = {
  none: "var(--color-verdict-succeeded)",
  mild: "var(--color-verdict-underperformed)",
  significant: "var(--color-verdict-failed)",
};

// This describes the embedding-similarity signal used only to auto-detect
// the nearest pillar — it's a separate measurement from Granite's severity
// verdict below and can legitimately disagree with it, so the copy must not
// read as a second, competing drift verdict.
const DIRECTION_LABEL: Record<string, string> = {
  similar: "Matched to this pillar — recent posts read very similarly to its historical posts",
  diverging: "Matched to this pillar — recent posts read somewhat differently from its historical posts",
  very_different: "Closest available match — recent posts read quite differently from this pillar's historical posts",
};

export default function DriftWatchdogPanel() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DriftCheckResult | null>(null);

  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);

  async function handleCheck() {
    if (lines.length < 3) {
      setError("Paste at least 3 recent posts (one per line) to compare.");
      return;
    }
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await checkBrandDrift(lines);
      setResult(res);
    } catch {
      setError("Something went wrong checking for drift — try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      className="rounded-xl border p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <p
        className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
        style={{ color: "var(--color-ql-muted)" }}
      >
        Brand Drift Watchdog
      </p>
      <p className="text-xs leading-relaxed mb-3" style={{ color: "var(--color-ql-muted)" }}>
        Paste a few of your most recent post captions (one per line) — Granite compares them
        against your locked brand voice profile and flags specific drift, not a generic score.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={"One caption per line…"}
        rows={5}
        className="w-full text-xs rounded-lg px-3 py-2 outline-none resize-y"
        style={{
          background: "var(--color-ql-gap)",
          border: "1px solid var(--color-ql-border)",
          color: "var(--color-ql-dark)",
        }}
      />

      <div className="flex items-center justify-between mt-2">
        <span className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
          {lines.length} line{lines.length === 1 ? "" : "s"}
        </span>
        <button
          onClick={handleCheck}
          disabled={loading}
          className="text-[11px] px-3 py-1.5 rounded-lg font-medium disabled:opacity-60"
          style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
        >
          {loading ? "Comparing against your brand profile…" : "Check for Drift"}
        </button>
      </div>

      {error && (
        <p className="text-xs mt-2" style={{ color: "var(--color-verdict-failed)" }}>
          {error}
        </p>
      )}

      {result && (
        <div
          className="rounded-xl border p-4 mt-4"
          style={{
            borderColor: SEVERITY_COLOR[result.severity] ?? "var(--color-ql-border)",
            background: "var(--color-ql-gap)",
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>
              Nearest pillar: {result.cluster_label}
            </span>
            <span
              className="text-[10px] uppercase tracking-[0.06em] ml-auto px-1.5 py-0.5 rounded-full"
              style={{ background: SEVERITY_COLOR[result.severity], color: "var(--color-ql-bg)" }}
            >
              {result.severity === "none" ? "On brand" : `${result.severity} drift`}
            </span>
          </div>
          <p className="text-[11px] italic mb-2" style={{ color: "var(--color-ql-muted)" }}>
            {DIRECTION_LABEL[result.similarity_signal.direction] ?? "Compared to your usual voice"}
          </p>
          <p className="text-sm leading-relaxed mb-3" style={{ color: "var(--color-ql-dark)" }}>
            {result.drift_summary}
          </p>

          {result.specific_changes.length > 0 && (
            <div className="mb-3">
              <p
                className="text-[10px] font-medium uppercase tracking-[0.08em] mb-1.5"
                style={{ color: "var(--color-verdict-failed)" }}
              >
                Specific changes
              </p>
              <ul className="flex flex-col gap-1">
                {result.specific_changes.map((c, i) => (
                  <li key={i} className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
                    &bull; {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.still_on_brand.length > 0 && (
            <div>
              <p
                className="text-[10px] font-medium uppercase tracking-[0.08em] mb-1.5"
                style={{ color: "var(--color-verdict-succeeded)" }}
              >
                Still on brand
              </p>
              <ul className="flex flex-col gap-1">
                {result.still_on_brand.map((c, i) => (
                  <li key={i} className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-text)" }}>
                    &bull; {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
