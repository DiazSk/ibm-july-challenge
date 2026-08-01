"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import { analyzeMoment, getDirections } from "@/lib/api";
import type { MomentAnalysis, Direction } from "@/lib/types";

interface Props {
  onApply: (desiredFeel: string, clusterId: number, product: string, occasion: string) => void;
}

type Step = "idle" | "analyzing" | "directions" | "generating-directions" | "applied";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

export default function BlankPageSolver({ onApply }: Props) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("idle");
  const [moment, setMoment] = useState("");
  const [analysis, setAnalysis] = useState<MomentAnalysis | null>(null);
  const [directions, setDirections] = useState<Direction[]>([]);
  const [chosen, setChosen] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    if (!moment.trim()) return;
    setError(null);
    setStep("analyzing");
    try {
      const a = await analyzeMoment(moment);
      setAnalysis(a);
      setStep("generating-directions");
      const d = await getDirections(a, moment);
      setDirections(d);
      setChosen(0);
      setStep("directions");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setStep("idle");
    }
  }

  function handleApply() {
    if (!analysis || !directions[chosen]) return;
    const dir = directions[chosen];
    onApply(`${dir.angle} ${dir.tone_note}`, analysis.best_cluster_id, analysis.product ?? "", analysis.occasion ?? "");
    setStep("applied");
    setTimeout(() => setOpen(false), 800);
  }

  function reset() {
    setStep("idle");
    setMoment("");
    setAnalysis(null);
    setDirections([]);
    setError(null);
  }

  return (
    <div
      className="rounded-xl border overflow-hidden mb-6"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left transition-colors hover:bg-[var(--color-ql-gap)]"
      >
        <div>
          <p
            className="text-sm font-medium flex items-center gap-1.5"
            style={{ color: "var(--color-ql-dark)", fontFamily: "var(--font-display)" }}
          >
            Blank Page Solver
            <span title="Describe a moment and Granite finds the emotional angle and brand-voice cluster to write from — no blank-page staring.">
              <Info size={14} style={{ color: "var(--color-ql-muted)" }} />
            </span>
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-ql-muted)" }}>
            Describe a moment — Granite finds your creative angle
          </p>
        </div>
        <svg
          className="w-4 h-4 transition-transform"
          style={{
            color: "var(--color-ql-muted)",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
          }}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className="px-5 pb-5 border-t"
          style={{ borderColor: "var(--color-ql-border)" }}
        >
          {step === "applied" ? (
            <div className="pt-4 text-center">
              <p className="text-sm" style={{ color: "var(--color-ql-accent)" }}>
                Direction applied to caption brief
              </p>
            </div>
          ) : (
            <>
              {/* Moment input */}
              <div className="pt-4">
                <label
                  className="block text-[11px] font-medium uppercase tracking-[0.12em] mb-2"
                  style={{ color: "var(--color-ql-muted)" }}
                >
                  What&apos;s the moment?
                </label>
                <textarea
                  value={moment}
                  onChange={(e) => setMoment(e.target.value)}
                  placeholder="e.g. It's Friday evening, we just pulled our last batch of Pistachio Rose bomboloni…"
                  rows={3}
                  className="w-full text-sm rounded-lg border px-3 py-2.5 resize-none outline-none transition-colors"
                  style={{
                    borderColor: "var(--color-ql-border)",
                    color: "var(--color-ql-text)",
                    background: "var(--color-ql-bg)",
                    fontFamily: "var(--font-family-sans)",
                  }}
                  onFocus={(e) =>
                    (e.target.style.borderColor = "var(--color-ql-accent)")
                  }
                  onBlur={(e) =>
                    (e.target.style.borderColor = "var(--color-ql-border)")
                  }
                  disabled={step !== "idle"}
                />
              </div>

              {error && (
                <p className="text-xs mt-2" style={{ color: "var(--color-verdict-failed)" }}>
                  {error}
                </p>
              )}

              {/* Analysis result */}
              {analysis && (
                <div
                  className="mt-4 p-3 rounded-lg"
                  style={{ background: "var(--color-ql-gap)" }}
                >
                  {(analysis.product || analysis.occasion) && (
                    <div className="grid grid-cols-2 gap-3 mb-3 pb-3 border-b" style={{ borderColor: "var(--color-ql-border)" }}>
                      {analysis.product && (
                        <div>
                          <p
                            className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
                            style={{ color: "var(--color-ql-muted)" }}
                          >
                            Product
                          </p>
                          <p className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
                            {analysis.product}
                          </p>
                        </div>
                      )}
                      {analysis.occasion && (
                        <div>
                          <p
                            className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
                            style={{ color: "var(--color-ql-muted)" }}
                          >
                            Occasion
                          </p>
                          <p className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
                            {analysis.occasion}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p
                        className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
                        style={{ color: "var(--color-ql-muted)" }}
                      >
                        Emotional Core
                      </p>
                      <p className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
                        {analysis.emotional_core}
                      </p>
                    </div>
                    <div>
                      <p
                        className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
                        style={{ color: "var(--color-ql-muted)" }}
                      >
                        Business Signal
                      </p>
                      <p className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
                        {analysis.business_signal}
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ background: CLUSTER_COLORS[analysis.best_cluster_id] ?? "var(--color-cluster-1)" }}
                    />
                    <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
                      {analysis.cluster_reason}
                    </p>
                  </div>
                </div>
              )}

              {/* Repetition guard — silent when the idea is genuinely new */}
              {!!analysis?.similar_posts?.length && (
                <div className="mt-4">
                  <p
                    className="text-[10px] uppercase tracking-[0.12em] font-medium mb-2"
                    style={{ color: "var(--color-ql-muted)" }}
                  >
                    You&apos;ve posted about this before
                  </p>
                  <div className="flex flex-col gap-2">
                    {analysis.similar_posts.map((s) => {
                      const tone =
                        s.recommendation === "repeat"
                          ? "var(--color-verdict-succeeded)"
                          : s.recommendation === "avoid"
                          ? "var(--color-ql-accent)"
                          : "var(--color-ql-muted)";
                      return (
                        <div
                          key={s.shortcode}
                          className="rounded-lg border p-3"
                          style={{
                            borderColor: "var(--color-ql-border)",
                            background: "var(--color-ql-card)",
                          }}
                        >
                          <div className="flex items-baseline justify-between gap-2 mb-1 flex-wrap">
                            <span className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
                              {s.closeness}{" "}
                              <span style={{ color: "var(--color-ql-dark)" }}>
                                {new Date(s.timestamp_utc).toLocaleDateString(undefined, {
                                  day: "numeric",
                                  month: "short",
                                  year: "numeric",
                                })}
                              </span>
                            </span>
                            <span
                              className="text-[10px] uppercase tracking-[0.08em] font-medium px-2 py-0.5 rounded-full shrink-0"
                              style={{ color: tone, background: "var(--color-ql-gap)" }}
                            >
                              {s.recommendation === "repeat"
                                ? "worth repeating"
                                : s.recommendation === "avoid"
                                ? "change the angle"
                                : "no metrics"}
                            </span>
                          </div>
                          <p
                            className="text-xs leading-relaxed line-clamp-2 mb-1"
                            style={{ color: "var(--color-ql-dark)" }}
                          >
                            &ldquo;{s.hook}&rdquo;
                          </p>
                          <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
                            {s.reach > 0 && <>{s.reach.toLocaleString()} reach · </>}
                            {s.note}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Direction cards */}
              {directions.length > 0 && (
                <div className="mt-4">
                  <p
                    className="text-[10px] uppercase tracking-[0.12em] font-medium mb-2"
                    style={{ color: "var(--color-ql-muted)" }}
                  >
                    Choose a direction
                  </p>
                  <div className="flex flex-col gap-2">
                    {directions.map((d, i) => (
                      <button
                        key={i}
                        onClick={() => setChosen(i)}
                        className="text-left p-3 rounded-lg border transition-all"
                        style={{
                          borderColor:
                            chosen === i
                              ? "var(--color-ql-dark)"
                              : "var(--color-ql-border)",
                          background:
                            chosen === i
                              ? "var(--color-ql-dark)"
                              : "var(--color-ql-card)",
                        }}
                      >
                        <p
                          className="text-xs font-medium"
                          style={{
                            color:
                              chosen === i ? "var(--color-ql-bg)" : "var(--color-ql-dark)",
                            fontFamily: "var(--font-display)",
                          }}
                        >
                          {d.direction_title}
                        </p>
                        <p
                          className="text-[11px] mt-0.5"
                          style={{
                            color:
                              chosen === i ? "color-mix(in oklch, var(--color-ql-bg) 70%, transparent)" : "var(--color-ql-muted)",
                          }}
                        >
                          {d.angle}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="mt-4 flex gap-2">
                {step === "idle" && (
                  <button
                    onClick={handleAnalyze}
                    disabled={!moment.trim()}
                    className="flex-1 py-2.5 text-xs font-medium rounded-lg transition-colors disabled:opacity-40"
                    style={{
                      background: "var(--color-ql-dark)",
                      color: "var(--color-ql-bg)",
                    }}
                  >
                    Analyze Moment
                  </button>
                )}
                {(step === "analyzing" || step === "generating-directions") && (
                  <button
                    disabled
                    className="flex-1 py-2.5 text-xs font-medium rounded-lg opacity-60"
                    style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}
                  >
                    <span className="animate-pulse">
                      {step === "analyzing" ? "Analyzing…" : "Finding directions…"}
                    </span>
                  </button>
                )}
                {step === "directions" && (
                  <>
                    <button
                      onClick={handleApply}
                      className="flex-1 py-2.5 text-xs font-medium rounded-lg transition-colors"
                      style={{
                        background: "var(--color-ql-dark)",
                        color: "var(--color-ql-bg)",
                      }}
                    >
                      Apply Direction
                    </button>
                    <button
                      onClick={reset}
                      className="px-4 py-2.5 text-xs rounded-lg border"
                      style={{
                        borderColor: "var(--color-ql-border)",
                        color: "var(--color-ql-muted)",
                      }}
                    >
                      Reset
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
