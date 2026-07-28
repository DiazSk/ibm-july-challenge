"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getClusters, describeImage } from "@/lib/api";
import type { WhyEngineRequest } from "@/lib/types";

interface Props {
  value: WhyEngineRequest;
  onChange: (v: WhyEngineRequest) => void;
  onSubmit: () => void;
  loading: boolean;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label
        className="block text-[11px] font-medium uppercase tracking-[0.12em] mb-1.5"
        style={{ color: "var(--color-ql-muted)" }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

const inputClass =
  "w-full text-sm rounded-lg border px-3 py-2.5 outline-none transition-colors";
const inputStyle = {
  borderColor: "var(--color-ql-border)",
  color: "var(--color-ql-text)",
  background: "var(--color-ql-bg)",
};
function onFocus(e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
  e.target.style.borderColor = "var(--color-ql-accent)";
}
function onBlur(e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) {
  e.target.style.borderColor = "var(--color-ql-border)";
}

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

export default function WhyEngineForm({ value, onChange, onSubmit, loading }: Props) {
  const { data: clusters } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });
  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  function set<K extends keyof WhyEngineRequest>(k: K, v: WhyEngineRequest[K]) {
    onChange({ ...value, [k]: v });
  }

  const [describing, setDescribing] = useState(false);
  const [visionError, setVisionError] = useState<string | null>(null);

  async function onImagePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setDescribing(true);
    setVisionError(null);
    try {
      const { visual_description } = await describeImage(file);
      set("visual_description", visual_description);
    } catch (err) {
      setVisionError(err instanceof Error ? err.message : "Vision model failed");
    } finally {
      setDescribing(false);
    }
  }

  const canSubmit = value.caption.trim() && value.views > 0;

  return (
    <div
      className="rounded-xl border p-5"
      style={{
        borderColor: "var(--color-ql-border)",
        background: "var(--color-ql-card)",
      }}
    >
      <h3
        className="text-base mb-1"
        style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
      >
        Why Engine
      </h3>
      <p className="text-xs mb-5" style={{ color: "var(--color-ql-muted)" }}>
        Diagnose any post — why it succeeded or underperformed against brand patterns.
      </p>

      <div className="flex flex-col gap-4">
        <Field label="Caption">
          <textarea
            value={value.caption}
            onChange={(e) => set("caption", e.target.value)}
            placeholder="Paste the caption you posted…"
            rows={3}
            className={`${inputClass} resize-none`}
            style={inputStyle}
            onFocus={onFocus}
            onBlur={onBlur}
          />
        </Field>

        <Field label="Post Image / Reel — optional (lets the model see it)">
          <input
            type="file"
            accept="image/*,video/*"
            onChange={onImagePicked}
            disabled={describing}
            className="block w-full text-xs file:mr-3 file:rounded-md file:border-0 file:px-3 file:py-2 file:text-xs file:font-medium disabled:opacity-40"
            style={{ color: "var(--color-ql-muted)" }}
          />
          {describing && (
            <p className="text-xs mt-1.5 animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
              Looking at your post…
            </p>
          )}
          {visionError && (
            <p className="text-xs mt-1.5" style={{ color: "var(--color-cluster-4)" }}>
              {visionError}
            </p>
          )}
          {value.visual_description && !describing && (
            <p className="text-xs mt-1.5 whitespace-pre-wrap rounded-md p-2"
               style={{ color: "var(--color-ql-text)", background: "var(--color-ql-gap)" }}>
              {value.visual_description}
            </p>
          )}
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label="Post Type">
            <select
              value={value.post_type}
              onChange={(e) => set("post_type", e.target.value as WhyEngineRequest["post_type"])}
              className={inputClass}
              style={inputStyle}
              onFocus={onFocus}
              onBlur={onBlur}
            >
              <option>Reel</option>
              <option>Carousel</option>
              <option>Static</option>
            </select>
          </Field>

          <Field label="Brand Voice (Cluster)">
            <select
              value={value.cluster_id}
              onChange={(e) => set("cluster_id", Number(e.target.value))}
              className={inputClass}
              style={inputStyle}
              onFocus={onFocus}
              onBlur={onBlur}
            >
              {clusterList.map((c) => (
                <option key={c.cluster_id} value={c.cluster_id}>
                  C{c.cluster_id} · {c.pillar}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div
          className="rounded-lg p-3"
          style={{ background: "var(--color-ql-gap)" }}
        >
          <p
            className="text-[10px] uppercase tracking-[0.12em] font-medium mb-3"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Performance Metrics
          </p>
          <div className="grid grid-cols-3 gap-3">
            {(
              [
                ["Views", "views"],
                ["Reach", "reach"],
                ["Likes", "likes"],
                ["Comments", "comments"],
                ["Shares", "shares"],
                ["Saves", "saves"],
              ] as const
            ).map(([label, key]) => (
              <div key={key}>
                <label
                  className="block text-[10px] mb-1"
                  style={{ color: "var(--color-ql-muted)" }}
                >
                  {label}
                </label>
                <input
                  type="number"
                  min={0}
                  value={value[key] || ""}
                  onChange={(e) => set(key, Number(e.target.value))}
                  className="w-full text-sm rounded-lg border px-2.5 py-2 outline-none"
                  style={{
                    borderColor: "var(--color-ql-border)",
                    color: "var(--color-ql-text)",
                    background: "var(--color-ql-card)",
                  }}
                  onFocus={onFocus}
                  onBlur={onBlur}
                />
              </div>
            ))}
          </div>

          {value.post_type === "Reel" && (
            <div className="mt-3">
              <label
                className="block text-[10px] mb-1"
                style={{ color: "var(--color-ql-muted)" }}
              >
                Avg Watch Time (secs) — optional
              </label>
              <input
                type="number"
                min={0}
                value={value.avg_watch_time_secs ?? ""}
                onChange={(e) =>
                  set(
                    "avg_watch_time_secs",
                    e.target.value ? Number(e.target.value) : undefined
                  )
                }
                className="w-40 text-sm rounded-lg border px-2.5 py-2 outline-none"
                style={{
                  borderColor: "var(--color-ql-border)",
                  color: "var(--color-ql-text)",
                  background: "var(--color-ql-card)",
                }}
                onFocus={onFocus}
                onBlur={onBlur}
              />
            </div>
          )}
        </div>

        <button
          onClick={onSubmit}
          disabled={!canSubmit || loading}
          className="w-full py-3 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
          style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}
        >
          {loading ? (
            <span className="animate-pulse">Diagnosing…</span>
          ) : (
            "Run Diagnosis"
          )}
        </button>
      </div>
    </div>
  );
}
