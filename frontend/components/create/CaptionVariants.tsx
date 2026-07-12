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
  onPin?: (caption: string) => void;
  onResonanceCheck?: () => void;
  resonanceLoading?: boolean;
  winnerIndex?: number | null;
  onGuardianReview?: (caption: string, idx: number) => void;
  guardianLoadingIdx?: number | null;
  usedRealOutcomes?: number;
}

export default function CaptionVariants({
  captions,
  product,
  onGenerateImage,
  onRegenerate,
  imageLoading,
  regenerateLoading,
  onPin,
  onResonanceCheck,
  resonanceLoading,
  winnerIndex,
  onGuardianReview,
  guardianLoadingIdx,
  usedRealOutcomes,
}: Props) {
  const [copied, setCopied] = useState<number | null>(null);
  const [pinnedSet, setPinnedSet] = useState<Set<number>>(new Set());

  function handlePin(idx: number, caption: string) {
    onPin?.(caption);
    setPinnedSet((prev) => new Set([...prev, idx]));
  }

  async function copy(text: string, idx: number) {
    await navigator.clipboard.writeText(text);
    setCopied(idx);
    setTimeout(() => setCopied(null), 1500);
  }

  if (captions.length === 0) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p
            className="text-[11px] font-medium uppercase tracking-[0.12em]"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Caption Variants
          </p>
          {!!usedRealOutcomes && usedRealOutcomes > 0 && (
            <span
              className="text-[9px] px-1.5 py-0.5 rounded-full"
              style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
              title="This generation factored in real reported outcomes from your Workbench"
            >
              Calibrated using {usedRealOutcomes} real outcome{usedRealOutcomes === 1 ? "" : "s"} so far
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {onResonanceCheck && (
            <button
              onClick={onResonanceCheck}
              disabled={resonanceLoading}
              title="Simulate how 3 audience personas would react before you post"
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg border transition-colors disabled:opacity-50"
              style={{
                borderColor: "var(--color-ql-accent)",
                color: "var(--color-ql-accent)",
              }}
            >
              {resonanceLoading ? (
                <span className="animate-pulse">Consulting three personas…</span>
              ) : (
                "Run Resonance Check"
              )}
            </button>
          )}
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
      </div>
      <div className="flex flex-col gap-3">
        {captions.map((c, i) => (
          <div
            key={i}
            className="rounded-xl border p-4"
            style={{
              borderColor: winnerIndex === i ? "var(--color-ql-accent)" : "var(--color-ql-border)",
              background: "var(--color-ql-card)",
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <span className="flex items-center gap-2 shrink-0 mt-0.5">
                <span
                  className="text-[10px] font-medium uppercase tracking-[0.1em]"
                  style={{ color: "var(--color-ql-accent)" }}
                >
                  V{i + 1}
                </span>
                {winnerIndex === i && (
                  <span
                    className="text-[9px] font-medium uppercase tracking-[0.08em] px-1.5 py-0.5 rounded-full"
                    style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
                  >
                    Panel&apos;s Pick
                  </span>
                )}
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
              {onPin && (
                <button
                  onClick={() => handlePin(i, c.caption)}
                  disabled={pinnedSet.has(i)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg border transition-colors disabled:opacity-60"
                  style={{
                    borderColor: pinnedSet.has(i)
                      ? "var(--color-ql-accent)"
                      : "var(--color-ql-border)",
                    color: pinnedSet.has(i)
                      ? "var(--color-ql-accent)"
                      : "var(--color-ql-muted)",
                  }}
                >
                  {pinnedSet.has(i) ? "Saved ✓" : "Save"}
                </button>
              )}
              <button
                onClick={() => onGenerateImage(c.caption)}
                disabled={imageLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg transition-colors disabled:opacity-50"
                style={{
                  background: "var(--color-ql-accent)",
                  color: "var(--color-ql-bg)",
                }}
              >
                {imageLoading ? "Generating…" : "→ Image Direction"}
              </button>
              {onGuardianReview && (
                <button
                  onClick={() => onGuardianReview(c.caption, i)}
                  disabled={guardianLoadingIdx !== null && guardianLoadingIdx !== undefined}
                  title="Put this caption through an adversarial brand-voice review"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg border transition-colors disabled:opacity-50"
                  style={{
                    borderColor: "var(--color-ql-border)",
                    color: "var(--color-ql-muted)",
                  }}
                >
                  {guardianLoadingIdx === i ? (
                    <span className="animate-pulse">On trial…</span>
                  ) : (
                    "Put on Trial"
                  )}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
