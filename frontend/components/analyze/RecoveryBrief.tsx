"use client";

import { useState } from "react";
import { saveAsset } from "@/lib/api";
import type { WhyEngineResult } from "@/lib/types";

interface Props {
  result: WhyEngineResult;
  clusterId: number;
  onSaved?: () => void;
}

const FORMAT_BG: Record<string, string> = {
  Reel: "var(--color-gold)",
  Carousel: "var(--sky)",
  Static: "var(--color-verdict-succeeded)",
};

export default function RecoveryBrief({ result, clusterId, onSaved }: Props) {
  const brief = result.recovery_brief;
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  if (!brief) return null;

  const formatBg = FORMAT_BG[brief.recommended_format] ?? "var(--color-gold)";

  async function handleSave() {
    if (!brief || saved) return;
    setSaving(true);
    try {
      await saveAsset({
        asset_type:
          brief.recommended_format === "Reel"
            ? "reel_script"
            : brief.recommended_format === "Carousel"
            ? "carousel"
            : "static_script",
        content: {
          hook: brief.new_hook,
          recovery_script: brief.recovery_script,
          reasoning: brief.reasoning,
          format: brief.recommended_format,
        },
        cluster_id: clusterId,
        source_tab: "recovery_brief",
      });
      setSaved(true);
      onSaved?.();
    } catch {
      // silent — save failures shouldn't block the UI
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="mt-4 rounded-xl border overflow-hidden"
      style={{ borderColor: "var(--color-ql-border)" }}
    >
      {/* Header */}
      <div
        className="px-5 py-3 flex items-center justify-between"
        style={{
          background: "color-mix(in oklch, var(--color-ql-accent) 7%, transparent)",
          borderBottom: "1px solid var(--color-ql-border)",
        }}
      >
        <div>
          <p
            className="text-[10px] font-medium uppercase tracking-[0.12em]"
            style={{ color: "var(--color-ql-accent)" }}
          >
            Recovery Brief
          </p>
          <p
            className="text-[11px] mt-0.5"
            style={{ color: "var(--color-ql-muted)" }}
          >
            IBM Granite — addresses the identified failure
          </p>
        </div>
        <span
          className="text-[10px] font-medium px-2.5 py-1 rounded-lg"
          style={{ background: formatBg, color: "var(--color-ql-bg)" }}
        >
          {brief.recommended_format}
        </span>
      </div>

      <div
        className="p-5 flex flex-col gap-4"
        style={{ background: "var(--color-ql-card)" }}
      >
        {/* New hook */}
        <div>
          <p
            className="text-[10px] uppercase tracking-[0.12em] mb-1.5"
            style={{ color: "var(--color-ql-muted)" }}
          >
            New Hook
          </p>
          <p
            className="text-base leading-snug"
            style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
          >
            &ldquo;{brief.new_hook}&rdquo;
          </p>
        </div>

        {/* Recovery script */}
        <div>
          <p
            className="text-[10px] uppercase tracking-[0.12em] mb-1.5"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Recovery Script
          </p>
          <p
            className="text-sm leading-relaxed whitespace-pre-wrap"
            style={{ color: "var(--color-ql-dark)" }}
          >
            {brief.recovery_script}
          </p>
        </div>

        {/* Reasoning */}
        <div
          className="rounded-lg border p-3"
          style={{
            borderColor: "var(--color-ql-border)",
            background: "var(--color-ql-bg)",
          }}
        >
          <p
            className="text-[10px] uppercase tracking-[0.12em] mb-1"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Why This Works
          </p>
          <p
            className="text-xs leading-relaxed"
            style={{ color: "var(--color-ql-muted)" }}
          >
            {brief.reasoning}
          </p>
        </div>

        {/* Save to Workbench */}
        <button
          onClick={handleSave}
          disabled={saving || saved}
          className="w-full py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-60"
          style={{
            background: saved ? "transparent" : "var(--color-ql-dark)",
            color: saved ? "var(--color-ql-accent)" : "var(--color-ql-bg)",
            border: saved ? "1px solid var(--color-ql-border)" : "none",
          }}
        >
          {saving ? "Saving…" : saved ? "Saved to Workbench ✓" : "Save to Workbench"}
        </button>
      </div>
    </div>
  );
}
