"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import type { ImagePromptResult } from "@/lib/types";

interface Props {
  result: ImagePromptResult;
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      onClick={copy}
      className="text-[11px] transition-colors"
      style={{ color: "var(--color-ql-accent)" }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function ImageDirectionCard({ result }: Props) {
  return (
    <div
      className="mt-4 rounded-xl border overflow-hidden"
      style={{ borderColor: "var(--color-ql-border)" }}
    >
      <div
        className="px-4 py-2.5 flex items-center justify-between border-b"
        style={{
          background: "var(--color-ql-sidebar)",
          borderColor: "var(--color-ql-border)",
        }}
      >
        <div className="flex items-center gap-1.5">
          <span
            className="text-[10px] font-medium uppercase tracking-[0.15em]"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Visual Direction
          </span>
          <span title="Turns a caption into a ready-to-shoot image prompt, style notes, and video direction for Veo 3 or image-to-video tools — all grounded in your brand's visual language.">
            <Info size={14} style={{ color: "var(--color-ql-muted)" }} />
          </span>
        </div>
        <CopyBtn text={result.prompt} />
      </div>

      <div
        className="px-4 py-3"
        style={{ background: "var(--color-ql-bg)" }}
      >
        <p
          className="text-xs leading-relaxed"
          style={{
            color: "var(--color-ql-text)",
            fontFamily: "var(--font-family-mono)",
          }}
        >
          {result.prompt}
        </p>
      </div>

      {result.style_notes && (
        <div
          className="px-4 py-3 border-t"
          style={{
            background: "var(--color-ql-gap)",
            borderColor: "var(--color-ql-border)",
          }}
        >
          <p
            className="text-[10px] uppercase tracking-[0.1em] font-medium mb-1"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Style Notes
          </p>
          <p className="text-xs" style={{ color: "var(--color-ql-text)" }}>
            {result.style_notes}
          </p>
        </div>
      )}

      {result.video_prompt && (
        <div
          className="px-4 py-3 border-t"
          style={{
            background: "var(--color-ql-gap)",
            borderColor: "var(--color-ql-border)",
          }}
        >
          <div className="flex items-center justify-between mb-1">
            <p
              className="text-[10px] uppercase tracking-[0.1em] font-medium"
              style={{ color: "var(--color-ql-muted)" }}
            >
              Video Prompt · Veo 3
            </p>
            <CopyBtn text={result.video_prompt} />
          </div>
          <p
            className="text-xs leading-relaxed"
            style={{
              color: "var(--color-ql-text)",
              fontFamily: "var(--font-family-mono)",
            }}
          >
            {result.video_prompt}
          </p>
        </div>
      )}

      {result.motion_notes && (
        <div
          className="px-4 py-3 border-t"
          style={{
            background: "var(--color-ql-gap)",
            borderColor: "var(--color-ql-border)",
          }}
        >
          <div className="flex items-center justify-between mb-1">
            <p
              className="text-[10px] uppercase tracking-[0.1em] font-medium"
              style={{ color: "var(--color-ql-muted)" }}
            >
              Motion · Image-to-Video
            </p>
            <CopyBtn text={result.motion_notes} />
          </div>
          <p className="text-xs" style={{ color: "var(--color-ql-text)" }}>
            {result.motion_notes}
          </p>
        </div>
      )}
    </div>
  );
}
