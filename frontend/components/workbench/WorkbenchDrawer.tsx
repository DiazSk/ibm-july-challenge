"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWorkbenchAssets, deleteAsset, updateAsset } from "@/lib/api";
import type { WorkbenchAsset } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
}

const ASSET_LABELS: Record<string, string> = {
  caption: "Caption",
  image_prompt: "Image Direction",
  reel_script: "Reel Script",
  carousel: "Carousel",
  static_script: "Static Post",
  recovery_brief: "Recovery Brief",
  weekly_brief_draft: "Weekly Brief Draft",
  guardian_refined_caption: "Guardian-Refined Caption",
  triage_reply: "Drafted Reply",
};

const _OUTCOME_ELIGIBLE_TYPES = new Set([
  "caption",
  "reel_script",
  "carousel",
  "static_script",
  "guardian_refined_caption",
  "weekly_brief_draft",
]);

const _OUTCOME_VALUES = ["succeeded", "underperformed", "failed"] as const;

function getPreviewText(asset: WorkbenchAsset): string {
  if (typeof asset.content === "string") return asset.content;
  const obj = asset.content as Record<string, unknown>;
  return String(obj.hook ?? obj.caption ?? obj.recovery_script ?? obj.drafted_reply ?? JSON.stringify(obj));
}

function getFullText(asset: WorkbenchAsset): string {
  if (typeof asset.content === "string") return asset.content;

  const obj = asset.content as Record<string, unknown>;

  if (asset.asset_type === "reel_script") {
    const parts: string[] = [];
    if (obj.hook) parts.push(`Hook:\n${obj.hook}`);
    if (obj.opening_line) parts.push(`Opening Line:\n${obj.opening_line}`);
    if (obj.voiceover_script) parts.push(`Voiceover:\n${obj.voiceover_script}`);
    const shots = obj.shot_suggestions as string[] | undefined;
    if (shots?.length) parts.push(`Shot Suggestions:\n${shots.map((s, i) => `${i + 1}. ${s}`).join("\n")}`);
    if (obj.caption) parts.push(`Caption:\n${obj.caption}`);
    const tags = obj.hashtags as string[] | undefined;
    if (tags?.length) parts.push(tags.join(" "));
    return parts.join("\n\n");
  }

  if (asset.asset_type === "carousel") {
    const parts: string[] = [];
    if (obj.hook) parts.push(`Cover Slide:\n${obj.hook}`);
    const slides = obj.slides as Array<{ slide: number; headline: string; body: string }> | undefined;
    if (slides?.length) {
      parts.push(slides.map((s) => `Slide ${s.slide}: ${s.headline}\n${s.body}`).join("\n\n"));
    }
    if (obj.cta_slide) parts.push(`CTA: ${obj.cta_slide}`);
    if (obj.caption) parts.push(`Caption:\n${obj.caption}`);
    const tags = obj.hashtags as string[] | undefined;
    if (tags?.length) parts.push(tags.join(" "));
    return parts.join("\n\n");
  }

  if (asset.asset_type === "static_script") {
    const parts: string[] = [];
    if (obj.headline) parts.push(`Headline:\n${obj.headline}`);
    if (obj.caption) parts.push(`Caption:\n${obj.caption}`);
    if (obj.visual_direction) parts.push(`Visual Direction:\n${obj.visual_direction}`);
    const tags = obj.hashtags as string[] | undefined;
    if (tags?.length) parts.push(tags.join(" "));
    return parts.join("\n\n");
  }

  if (asset.asset_type === "recovery_brief") {
    const parts: string[] = [];
    if (obj.new_hook) parts.push(`Hook:\n${obj.new_hook}`);
    if (obj.recommended_format) parts.push(`Format: ${obj.recommended_format}`);
    if (obj.recovery_script) parts.push(`Script:\n${obj.recovery_script}`);
    if (obj.reasoning) parts.push(`Reasoning:\n${obj.reasoning}`);
    return parts.join("\n\n");
  }

  if (asset.asset_type === "guardian_refined_caption") {
    const parts: string[] = [];
    if (obj.caption) parts.push(`Caption:\n${obj.caption}`);
    if (obj.converged) {
      parts.push(`Approved after ${obj.rounds_used} round(s)`);
    } else if (obj.best_so_far) {
      parts.push(`Best of ${obj.rounds_used} rounds (not fully approved)`);
    }
    return parts.join("\n\n");
  }

  if (asset.asset_type === "triage_reply") {
    const parts: string[] = [];
    if (obj.original_message) parts.push(`Original:\n${obj.original_message}`);
    if (obj.category) parts.push(`Category: ${obj.category}`);
    if (obj.drafted_reply) parts.push(`Reply:\n${obj.drafted_reply}`);
    return parts.join("\n\n");
  }

  if (asset.asset_type === "weekly_brief_draft") {
    const parts: string[] = [];
    if (obj.scenario_text) parts.push(`Idea:\n${obj.scenario_text}`);
    if (obj.rationale) parts.push(`Why this works:\n${obj.rationale}`);
    if (obj.caption) parts.push(`Caption:\n${obj.caption}`);
    if (obj.image_prompt) parts.push(`Image Direction:\n${obj.image_prompt}`);
    if (obj.style_notes) parts.push(`Style Notes:\n${obj.style_notes}`);
    return parts.join("\n\n");
  }

  return String(obj.hook ?? obj.caption ?? obj.recovery_script ?? JSON.stringify(obj, null, 2));
}

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
      className="text-[10px] px-2 py-0.5 rounded border transition-colors"
      style={{
        borderColor: copied ? "var(--color-ql-accent)" : "var(--color-ql-border)",
        color: copied ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
      }}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function AssetCard({
  asset,
  onPin,
  onDelete,
  onSetOutcome,
}: {
  asset: WorkbenchAsset;
  onPin: () => void;
  onDelete: () => void;
  onSetOutcome: (outcome: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const fullText = getFullText(asset);
  const preview = getPreviewText(asset);
  const isLong = preview.length > 120;
  const displayText = expanded ? fullText : (isLong ? preview.slice(0, 120) + "…" : preview);

  return (
    <div
      className="rounded-xl border p-3.5"
      style={{
        borderColor: asset.pinned ? "var(--color-ql-accent)" : "var(--color-ql-border)",
        background: "var(--color-ql-card)",
        transition: "border-color 0.15s",
      }}
    >
      {/* Type badge + controls */}
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-[10px] font-medium uppercase tracking-[0.08em] px-2 py-0.5 rounded-md"
          style={{ background: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
        >
          {ASSET_LABELS[asset.asset_type] ?? asset.asset_type}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={onPin}
            className="w-6 h-6 flex items-center justify-center text-sm"
            style={{
              color: asset.pinned ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
              opacity: asset.pinned ? 1 : 0.35,
              transition: "opacity 0.15s, color 0.15s",
            }}
            title={asset.pinned ? "Unstar" : "Star"}
          >
            ★
          </button>
          <button
            onClick={onDelete}
            className="w-6 h-6 flex items-center justify-center text-xs"
            style={{ color: "var(--color-ql-muted)", opacity: 0.3 }}
            title="Remove"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Cluster label */}
      {asset.cluster_label && (
        <p className="text-[10px] mb-1.5" style={{ color: "var(--color-ql-accent)" }}>
          {asset.cluster_label}
        </p>
      )}

      {/* Content */}
      <p
        className="text-xs leading-relaxed whitespace-pre-wrap"
        style={{ color: "var(--color-ql-dark)" }}
      >
        {displayText}
      </p>

      {/* Show more / less + Copy */}
      <div className="flex items-center justify-between mt-2.5">
        {isLong ? (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-[10px]"
            style={{ color: "var(--color-ql-muted)", textDecoration: "underline", textUnderlineOffset: "2px" }}
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        ) : (
          <span />
        )}
        <CopyButton text={fullText} />
      </div>

      {/* Outcome pills — real performance feedback the Create tab learns from */}
      {_OUTCOME_ELIGIBLE_TYPES.has(asset.asset_type) && (
        <div className="mt-2.5 pt-2.5 flex items-center gap-1.5" style={{ borderTop: "1px solid var(--color-ql-border)" }}>
          <span className="text-[9px] uppercase tracking-[0.08em]" style={{ color: "var(--color-ql-muted)", opacity: 0.5 }}>
            Outcome:
          </span>
          {_OUTCOME_VALUES.map((v) => {
            const active = asset.actual_outcome === v;
            return (
              <button
                key={v}
                onClick={() => onSetOutcome(active ? "" : v)}
                className="text-[9px] px-1.5 py-0.5 rounded-full border transition-colors"
                style={{
                  borderColor: active ? "var(--color-ql-accent)" : "var(--color-ql-border)",
                  background: active ? "var(--color-ql-accent)" : "transparent",
                  color: active ? "var(--color-ql-bg)" : "var(--color-ql-muted)",
                }}
              >
                {v}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function WorkbenchDrawer({ open, onClose }: Props) {
  const queryClient = useQueryClient();

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["workbench"],
    queryFn: () => getWorkbenchAssets(),
    staleTime: 0,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAsset(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workbench"] }),
  });

  const pinMutation = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) =>
      updateAsset(id, { pinned }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workbench"] }),
  });

  const outcomeMutation = useMutation({
    mutationFn: ({ id, actual_outcome }: { id: string; actual_outcome: string }) =>
      updateAsset(id, { actual_outcome }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workbench"] }),
  });

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40"
          style={{ background: "rgba(0,0,0,0.08)" }}
          onClick={onClose}
        />
      )}

      <div
        className={`fixed right-0 top-0 h-full w-80 z-50 flex flex-col transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        style={{
          background: "var(--color-ql-bg)",
          borderLeft: "1px solid var(--color-ql-border)",
          boxShadow: open ? "-4px 0 32px rgba(0,0,0,0.07)" : "none",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: "1px solid var(--color-ql-border)" }}
        >
          <div>
            <p
              className="text-[10px] font-medium uppercase tracking-[0.12em]"
              style={{ color: "var(--color-ql-muted)" }}
            >
              Workbench
            </p>
            <p
              className="text-sm mt-0.5"
              style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
            >
              {assets.length} saved {assets.length === 1 ? "asset" : "assets"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center text-xs rounded-lg"
            style={{ color: "var(--color-ql-muted)", opacity: 0.5 }}
          >
            ✕
          </button>
        </div>

        {/* Asset list */}
        <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
          {isLoading && (
            <p
              className="text-xs text-center py-10 animate-pulse"
              style={{ color: "var(--color-ql-muted)" }}
            >
              Loading…
            </p>
          )}

          {!isLoading && assets.length === 0 && (
            <div className="text-center py-14">
              <p
                className="text-xs uppercase tracking-[0.1em]"
                style={{ color: "var(--color-ql-muted)" }}
              >
                Empty workbench
              </p>
              <p
                className="text-[11px] mt-2 leading-relaxed max-w-[180px] mx-auto"
                style={{ color: "var(--color-ql-muted)", opacity: 0.5 }}
              >
                Save captions and scripts from the Create and Analyze tabs
              </p>
            </div>
          )}

          {assets.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onPin={() => pinMutation.mutate({ id: asset.id, pinned: !asset.pinned })}
              onDelete={() => deleteMutation.mutate(asset.id)}
              onSetOutcome={(outcome) => outcomeMutation.mutate({ id: asset.id, actual_outcome: outcome })}
            />
          ))}
        </div>
      </div>
    </>
  );
}
