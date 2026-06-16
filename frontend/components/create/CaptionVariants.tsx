"use client";

import { useState } from "react";
import type { Caption } from "@/lib/types";

interface Props {
  captions: Caption[];
  product: string;
  onGenerateImage: (caption: string) => void;
  onRegenerate: () => void;
  imageLoading: boolean;
  regenerateLoading: boolean;
}

export default function CaptionVariants({
  captions,
  product,
  onGenerateImage,
  onRegenerate,
  imageLoading,
  regenerateLoading,
}: Props) {
  const [copied, setCopied] = useState<number | null>(null);

  async function copy(text: string, idx: number) {
    await navigator.clipboard.writeText(text);
    setCopied(idx);
    setTimeout(() => setCopied(null), 1500);
  }

  if (captions.length === 0) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <p
          className="text-[11px] font-medium uppercase tracking-[0.12em]"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Caption Variants
        </p>
        <button
          onClick={onRegenerate}
          disabled={regenerateLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg border transition-colors disabled:opacity-50"
          style={{
            borderColor: "var(--color-ql-border)",
            color: "var(--color-ql-muted)",
          }}
        >
          {regenerateLoading ? (
            <span className="animate-pulse">Generating…</span>
          ) : (
            "Regenerate"
          )}
        </button>
      </div>
      <div className="flex flex-col gap-3">
        {captions.map((c, i) => (
          <div
            key={i}
            className="rounded-xl border p-4"
            style={{
              borderColor: "var(--color-ql-border)",
              background: "var(--color-ql-card)",
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <span
                className="text-[10px] font-medium uppercase tracking-[0.1em] shrink-0 mt-0.5"
                style={{ color: "var(--color-ql-accent)" }}
              >
                V{i + 1}
              </span>
              <p
                className="flex-1 text-sm leading-relaxed whitespace-pre-wrap"
                style={{ color: "var(--color-ql-dark)" }}
              >
                {c.caption}
              </p>
            </div>

            {c.reasoning && (
              <p
                className="text-[11px] mt-2 leading-snug border-t pt-2"
                style={{
                  color: "var(--color-ql-muted)",
                  borderColor: "var(--color-ql-border)",
                }}
              >
                {c.reasoning}
              </p>
            )}

            <div className="mt-3 flex gap-2">
              <button
                onClick={() => copy(c.caption, i)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg border transition-colors"
                style={{
                  borderColor: "var(--color-ql-border)",
                  color: "var(--color-ql-muted)",
                }}
              >
                {copied === i ? "Copied" : "Copy"}
              </button>
              <button
                onClick={() => onGenerateImage(c.caption)}
                disabled={imageLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg transition-colors disabled:opacity-50"
                style={{
                  background: "var(--color-ql-accent)",
                  color: "#fff",
                }}
              >
                {imageLoading ? "Generating…" : "→ Image Direction"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
