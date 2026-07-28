"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { getClusters, generateScript, saveAsset } from "@/lib/api";
import { useLocalStorage } from "@/lib/useLocalStorage";
import type { ScriptResult, ReelClip } from "@/lib/types";

type Format = "Reel" | "Carousel" | "Static";

const FORMATS: Format[] = ["Reel", "Carousel", "Static"];
const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

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
  const caption = script.caption as string | undefined;
  const clips = (script.clips as ReelClip[] | undefined) ?? [];
  const musicRecommendation = script.music_recommendation as string | undefined;
  const hashtags = (script.hashtags as string[] | undefined) ?? [];

  return (
    <div className="flex flex-col gap-3">
      {hook && (
        <div className="rounded-lg px-4 py-3 text-center" style={{ background: "var(--color-ql-dark)" }}>
          <p className="text-sm font-medium" style={{ color: "var(--color-ql-bg)", fontFamily: "var(--font-display)" }}>
            {hook}
          </p>
          <p className="text-[10px] mt-1 uppercase tracking-[0.1em]" style={{ color: "color-mix(in oklch, var(--color-ql-bg) 50%, transparent)" }}>
            Hook
          </p>
        </div>
      )}

      {clips.length > 0 && (
        <div className="flex flex-col gap-2">
          {clips.map((c) => (
            <div
              key={c.clip_number}
              className="rounded-lg border p-3"
              style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-bg)" }}
            >
              <div className="flex items-start gap-2">
                <span className="shrink-0 text-[10px] font-medium mt-0.5" style={{ color: "var(--color-ql-accent)" }}>
                  {c.clip_number}.
                </span>
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium" style={{ color: "var(--color-ql-dark)" }}>{c.action}</p>
                    <span className="text-[10px] shrink-0" style={{ color: "var(--color-ql-muted)" }}>{c.duration_secs}s</span>
                  </div>
                  {c.voiceover_line && (
                    <p className="text-[11px] mt-1 italic leading-snug" style={{ color: "var(--color-ql-text)" }}>
                      &ldquo;{c.voiceover_line}&rdquo;
                    </p>
                  )}
                  <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-1.5">
                    <p className="text-[10px] leading-snug" style={{ color: "var(--color-ql-muted)" }}>
                      <span style={{ color: "var(--color-ql-accent)" }}>Camera:</span> {c.camera_angle}
                    </p>
                    <p className="text-[10px] leading-snug" style={{ color: "var(--color-ql-muted)" }}>
                      <span style={{ color: "var(--color-ql-accent)" }}>Lighting:</span> {c.lighting}
                    </p>
                    <p className="text-[10px] leading-snug" style={{ color: "var(--color-ql-muted)" }}>
                      <span style={{ color: "var(--color-ql-accent)" }}>Setting:</span> {c.setting}
                    </p>
                    <p className="text-[10px] leading-snug" style={{ color: "var(--color-ql-muted)" }}>
                      <span style={{ color: "var(--color-ql-accent)" }}>Audio:</span> {c.audio_cue}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {musicRecommendation && (
        <div className="rounded-lg border p-3" style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}>
          <p className="text-[10px] font-medium uppercase tracking-[0.1em] mb-1" style={{ color: "var(--color-ql-muted)" }}>
            Music
          </p>
          <p className="text-xs leading-snug" style={{ color: "var(--color-ql-dark)" }}>{musicRecommendation}</p>
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
          <p className="text-sm font-medium" style={{ color: "var(--color-ql-bg)", fontFamily: "var(--font-display)" }}>
            {hook}
          </p>
          <p className="text-[10px] mt-1 uppercase tracking-[0.1em]" style={{ color: "color-mix(in oklch, var(--color-ql-bg) 50%, transparent)" }}>
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
          <p className="text-sm font-medium" style={{ color: "var(--color-ql-bg)", fontFamily: "var(--font-display)" }}>{headline}</p>
          <p className="text-[10px] mt-1 uppercase tracking-[0.1em]" style={{ color: "color-mix(in oklch, var(--color-ql-bg) 50%, transparent)" }}>Headline</p>
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
  const containerRef = useRef<HTMLDivElement>(null);

  // One-shot: "Develop this" on a weekly-brief draft seeds the ss_script_* keys
  // and sets ss_script_open, so we open + scroll into view on arrival.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem("ss_script_open") !== "1") return;
    localStorage.removeItem("ss_script_open");
    setOpen(true);
    requestAnimationFrame(() =>
      containerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    );
  }, []);

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
      ref={containerRef}
      className="rounded-xl border overflow-hidden scroll-mt-20"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left transition-colors hover:bg-[var(--color-ql-gap)]"
      >
        <div>
          <p className="text-sm font-medium flex items-center gap-1.5" style={{ color: "var(--color-ql-dark)", fontFamily: "var(--font-display)" }}>
            Script Studio
            <span title="Paste a post that performed well and Granite turns it into a new Reel, Carousel, or Static script in the same successful mold.">
              <Info size={14} style={{ color: "var(--color-ql-muted)" }} />
            </span>
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
                Reference caption or idea
              </label>
              <textarea
                value={refCaption}
                onChange={(e) => setRefCaption(e.target.value)}
                placeholder="Paste a caption from a post that performed well — or develop a weekly-brief idea…"
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
                      color: format === f ? "var(--color-ql-bg)" : "var(--color-ql-muted)",
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
                        style={{ background: CLUSTER_COLORS[c.cluster_id] ?? "var(--color-cluster-1)" }} />
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
              style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}
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
