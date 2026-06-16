"use client";

import { useState } from "react";
import type { ImagePromptResult } from "@/lib/types";

interface Props {
  result: ImagePromptResult;
}

export default function ImageDirectionCard({ result }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(result.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

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
        <span
          className="text-[10px] font-medium uppercase tracking-[0.15em]"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Image Direction
        </span>
        <button
          onClick={copy}
          className="text-[11px] transition-colors"
          style={{ color: "var(--color-ql-accent)" }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
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
    </div>
  );
}
