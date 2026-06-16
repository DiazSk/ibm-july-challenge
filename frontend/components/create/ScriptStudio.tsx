"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getClusters, generateScript, saveAsset } from "@/lib/api";
import { useLocalStorage } from "@/lib/useLocalStorage";
import type { ScriptResult } from "@/lib/types";

type Format = "Reel" | "Carousel" | "Static";

const FORMATS: Format[] = ["Reel", "Carousel", "Static"];
const CLUSTER_COLORS = ["#5A8A6A", "#8B7355", "#A35A5A", "#5A6A8A", "#6A5A8A"] as const;

const METRIC_FIELDS = [
  { key: "views", label: "Views" },
  { key: "reach", label: "Reach" },
  { key: "likes", label: "Likes" },
  { key: "comments", label: "Comments" },
  { key: "shares", label: "Shares" },
  { key: "saves", label: "Saves" },
] as const;

type MetricKey = typeof METRIC_FIELDS[number]["key"];

interface Metrics {
  views: number;
  reach: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
}

const DEFAULT_METRICS: Metrics = { views: 0, reach: 0, likes: 0, comments: 0, shares: 0, saves: 0 };

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <button
      onClick={copy}
      className="text-[10px] px-2 py-1 rounded border transition-colors"
      style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function ScriptBlock({ label, content }: { label: string; content: string }) {
  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <p
          className="text-[10px] font-medium uppercase tracking-[0.1em]"
          style={{ color: "var(--color-ql-muted)" }}
        >
          {label}
        </p>
        <CopyButton text={content} />
      </div>
      <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
        {content}
      </p>
    </div>
  );
}

function ReelOutput({ script }: { script: ScriptResult }) {
  const hook = script.hook as string | undefined;
  const openingLine = script.opening_line as string | undefined;
  const voiceover = script.voiceover_script as string | undefined;
  const caption = script.caption as string | undefined;
  const shots = (script.shot_suggestions as string[] | undefined) ?? [];
  const hashtags = (script.hashtags as string[] | undefined) ?? [];

  return (
    <div className="flex flex-col gap-3">
      {hook && (
        <div className="rounded-lg px-4 py-3 text-center" style={{ background: "var(--color-ql-dark)" }}>
          <p className="text-sm font-medium" style={{ color: "#fff", fontFamily: "Georgia, serif" }}>
            {hook}
          </p>
          <p className="text-[10px] mt-1 uppercase tracking-[0.1em]" style={{ color: "rgba(255,255,255,0.5)" }}>
            Hook
          </p>
        </div>
      )}
      {openingLine && <ScriptBlock label="Opening Line" content={openingLine} />}
      {voiceover && <ScriptBlock label="Voiceover Script" content={voiceover} />}
      {shots.length > 0 && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.1em] mb-1.5" style={{ color: "var(--color-ql-muted)" }}>
            Shot Suggestions
          </p>
          <ul className="flex flex-col gap-1">
            {shots.map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="shrink-0 text-[10px] font-medium mt-0.5" style={{ color: "var(--color-ql-accent)" }}>
                  {i + 1}.
                </span>
                <span className="text-xs" style={{ color: "var(--color-ql-text)" }}>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {caption && <ScriptBlock label="Caption" content={caption} />}
      {hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {hashtags.map((h, i) => (
            <span key={i} className="text-[11px] px-2 py-0.5 rounded-full border"
              style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-accent)" }}>
              {h}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CarouselOutput({ script }: { script: ScriptResult }) {
  const hook = script.hook as string | undefined;
  const ctaSlide = script.cta_slide as string | undefined;
  const caption = script.caption as string | undefined;
  const slides = (script.slides as Array<{ slide: number; headline: string; body: string }> | undefined) ?? [];
  const hashtags = (script.hashtags as string[] | undefined) ?? [];

  return (
    <div className="flex flex-col gap-3">
      {hook && (
        <div className="rounded-lg px-4 py-3 text-center" style={{ background: "var(--color-ql-dark)" }}>
          <p className="text-sm font-medium" style={{ color: "#fff", fontFamily: "Georgia, serif" }}>
            {hook}
          </p>
          <p className="text-[10px] mt-1 uppercase tracking-[0.1em]" style={{ color: "rgba(255,255,255,0.5)" }}>
            Cover Slide
          </p>
        </div>
      )}
      {slides.length > 0 && (
        <div className="flex flex-col gap-2">
          {slides.map((s) => (
            <div key={s.slide} className="rounded-lg border p-3"
              style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-bg)" }}>
              <div className="flex items-start gap-2">
                <span className="shrink-0 text-[10px] font-medium mt-0.5" style={{ color: "var(--color-ql-accent)" }}>
                  {s.slide}.
                </span>
                <div>
                  <p className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>{s.headline}</p>
                  <p className="text-[11px] mt-0.5 leading-snug" style={{ color: "var(--color-ql-muted)" }}>{s.body}</p>
                </div>
              </div>
            </div>
          ))}
          {ctaSlide && (
            <div className="rounded-lg border p-3 text-center"
              style={{ borderColor: "var(--color-ql-accent)", background: "var(--color-ql-gap)" }}>
              <p className="text-xs font-medium" style={{ color: "var(--color-ql-accent)" }}>{ctaSlide}</p>
              <p className="text-[10px] mt-0.5 uppercase tracking-[0.1em]" style={{ color: "var(--color-ql-muted)" }}>CTA Slide</p>
            </div>
          )}
        </div>
      )}
      {caption && <ScriptBlock label="Caption" content={caption} />}
      {hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {hashtags.map((h, i) => (
            <span key={i} className="text-[11px] px-2 py-0.5 rounded-full border"
              style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-accent)" }}>
              {h}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function StaticOutput({ script }: { script: ScriptResult }) {
  const headline = script.headline as string | undefined;
  const caption = script.caption as string | undefined;
  const visualDir = script.visual_direction as string | undefined;
  const hashtags = (script.hashtags as string[] | undefined) ?? [];
  return (
    <div className="flex flex-col gap-3">
      {headline && (
        <div className="rounded-lg px-4 py-3 text-center" style={{ background: "var(--color-ql-dark)" }}>
          <p className="text-sm font-medium" style={{ color: "#fff", fontFamily: "Georgia, serif" }}>{headline}</p>
          <p className="text-[10px] mt-1 uppercase tracking-[0.1em]" style={{ color: "rgba(255,255,255,0.5)" }}>Headline</p>
        </div>
      )}
      {caption && <ScriptBlock label="Caption" content={caption} />}
      {visualDir && (
        <div className="rounded-lg border p-3" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}>
          <p className="text-[10px] font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--color-ql-muted)" }}>
            Visual Direction
          </p>
          <p className="text-xs leading-snug" style={{ color: "var(--color-ql-dark)" }}>{visualDir}</p>
        </div>
      )}
      {hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {hashtags.map((h, i) => (
            <span key={i} className="text-[11px] px-2 py-0.5 rounded-full border"
              style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-accent)" }}>
              {h}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ScriptStudio() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  // Persisted across tab changes and refreshes
  const [refCaption, setRefCaption, clearRefCaption] = useLocalStorage("ss_script_caption", "");
  const [metrics, setMetrics, clearMetrics] = useLocalStorage<Metrics>("ss_script_metrics", DEFAULT_METRICS);
  const [format, setFormat, clearFormat] = useLocalStorage<Format>("ss_script_format", "Reel");
  const [clusterId, setClusterId, clearClusterId] = useLocalStorage("ss_script_cluster", 0);

  // Ephemeral
  const [result, setResult] = useState<ScriptResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const { data: clusters } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });
  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  function setMetric(key: MetricKey, value: number) {
    setMetrics((m) => ({ ...m, [key]: value }));
  }

  function handleClearScript() {
    clearRefCaption();
    clearMetrics();
    clearFormat();
    clearClusterId();
    setResult(null);
    setError(null);
    setSaved(false);
  }

  async function handleGenerate() {
    if (!refCaption.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setSaved(false);
    try {
      const r = await generateScript({
        reference_caption: refCaption,
        ...metrics,
        format,
        cluster_id: clusterId,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Script generation failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!result) return;
    setSaving(true);
    try {
      const clusterLabel = clusterList.find((c) => c.cluster_id === clusterId)?.pillar ?? null;
      await saveAsset({
        asset_type: format === "Reel" ? "reel_script" : format === "Carousel" ? "carousel" : "static_script",
        content: result,
        cluster_label: clusterLabel,
        cluster_id: clusterId,
        source_tab: "script_studio",
      });
      queryClient.invalidateQueries({ queryKey: ["workbench"] });
      setSaved(true);
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left transition-colors hover:bg-[#f7f5f2]"
      >
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--color-ql-dark)", fontFamily: "Georgia, serif" }}>
            Script Studio
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-ql-muted)" }}>
            Turn a high-performing post into a Reel, Carousel, or Static script
          </p>
        </div>
        <svg
          className="w-4 h-4 transition-transform"
          style={{ color: "var(--color-ql-muted)", transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t" style={{ borderColor: "var(--color-ql-border)" }}>
          <div className="pt-4 flex flex-col gap-4">
            {/* Clear button */}
            <div className="flex items-center justify-end">
              <button
                onClick={handleClearScript}
                className="text-[11px] px-2 py-1 rounded border transition-colors"
                style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
              >
                Clear
              </button>
            </div>

            {/* Reference caption */}
            <div>
              <label className="block text-[11px] font-medium uppercase tracking-[0.12em] mb-1.5" style={{ color: "var(--color-ql-muted)" }}>
                Reference Post Caption
              </label>
              <textarea
                value={refCaption}
                onChange={(e) => setRefCaption(e.target.value)}
                placeholder="Paste a caption from a post that performed really well…"
                rows={3}
                className="w-full text-sm rounded-lg border px-3 py-2.5 resize-none outline-none transition-colors"
                style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-text)", background: "var(--color-ql-bg)" }}
                onFocus={(e) => (e.target.style.borderColor = "var(--color-ql-accent)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--color-ql-border)")}
              />
            </div>

            {/* Metrics */}
            <div className="rounded-lg p-3" style={{ background: "var(--color-ql-gap)" }}>
              <p className="text-[10px] uppercase tracking-[0.12em] font-medium mb-3" style={{ color: "var(--color-ql-muted)" }}>
                Performance Metrics
              </p>
              <div className="grid grid-cols-3 gap-3">
                {METRIC_FIELDS.map(({ key, label }) => (
                  <div key={key}>
                    <label className="block text-[10px] mb-1" style={{ color: "var(--color-ql-muted)" }}>
                      {label}
                    </label>
                    <input
                      type="number"
                      min={0}
                      value={metrics[key] || ""}
                      onChange={(e) => setMetric(key, Number(e.target.value))}
                      className="w-full text-sm rounded-lg border px-2.5 py-2 outline-none"
                      style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-text)", background: "var(--color-ql-card)" }}
                      onFocus={(e) => (e.target.style.borderColor = "var(--color-ql-accent)")}
                      onBlur={(e) => (e.target.style.borderColor = "var(--color-ql-border)")}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Format selector */}
            <div>
              <label className="block text-[11px] font-medium uppercase tracking-[0.12em] mb-1.5" style={{ color: "var(--color-ql-muted)" }}>
                Output Format
              </label>
              <div className="flex gap-2">
                {FORMATS.map((f) => (
                  <button
                    key={f}
                    onClick={() => setFormat(f)}
                    className="flex-1 py-2 text-xs rounded-lg border transition-all"
                    style={{
                      borderColor: format === f ? "var(--color-ql-dark)" : "var(--color-ql-border)",
                      background: format === f ? "var(--color-ql-dark)" : "transparent",
                      color: format === f ? "#fff" : "var(--color-ql-muted)",
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>

            {/* Brand voice */}
            {clusterList.length > 0 && (
              <div>
                <label className="block text-[11px] font-medium uppercase tracking-[0.12em] mb-1.5" style={{ color: "var(--color-ql-muted)" }}>
                  Brand Voice
                </label>
                <div className="flex flex-col gap-1.5">
                  {clusterList.map((c) => (
                    <button
                      key={c.cluster_id}
                      onClick={() => setClusterId(c.cluster_id)}
                      className="flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all"
                      style={{
                        borderColor: clusterId === c.cluster_id ? "var(--color-ql-dark)" : "var(--color-ql-border)",
                        background: clusterId === c.cluster_id ? "var(--color-ql-gap)" : "transparent",
                      }}
                    >
                      <span className="w-2 h-2 rounded-full shrink-0"
                        style={{ background: CLUSTER_COLORS[c.cluster_id] ?? "#8B7355" }} />
                      <span className="text-xs" style={{ color: "var(--color-ql-dark)" }}>
                        {c.pillar}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <p className="text-xs" style={{ color: "var(--color-verdict-failed)" }}>{error}</p>
            )}

            <button
              onClick={handleGenerate}
              disabled={!refCaption.trim() || loading}
              className="w-full py-3 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
              style={{ background: "var(--color-ql-dark)", color: "#fff" }}
            >
              {loading ? <span className="animate-pulse">Generating Script…</span> : "Generate Script"}
            </button>

            {/* Result */}
            {result && (
              <div className="mt-2 pt-4 border-t" style={{ borderColor: "var(--color-ql-border)" }}>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: "var(--color-ql-muted)" }}>
                    {result.format} Script
                  </p>
                  {result.reasoning != null && (
                    <p className="text-[11px] max-w-xs text-right" style={{ color: "var(--color-ql-muted)" }}>
                      {String(result.reasoning)}
                    </p>
                  )}
                </div>
                {result.format === "Reel" && <ReelOutput script={result} />}
                {result.format === "Carousel" && <CarouselOutput script={result} />}
                {result.format === "Static" && <StaticOutput script={result} />}

                <div className="mt-4 flex justify-end">
                  <button
                    onClick={handleSave}
                    disabled={saved || saving}
                    className="text-xs px-4 py-2 rounded-lg border transition-all"
                    style={{
                      borderColor: saved ? "var(--color-ql-accent)" : "var(--color-ql-border)",
                      color: saved ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
                    }}
                  >
                    {saved ? "Saved ✓" : saving ? "Saving…" : "Save to Workbench"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
