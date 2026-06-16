"use client";

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
};

function contentPreview(asset: WorkbenchAsset): string {
  if (typeof asset.content === "string") {
    return asset.content.length > 120
      ? asset.content.slice(0, 120) + "…"
      : asset.content;
  }
  const obj = asset.content as Record<string, unknown>;
  const raw = String(
    obj.hook ?? obj.caption ?? obj.recovery_script ?? JSON.stringify(obj)
  );
  return raw.length > 120 ? raw.slice(0, 120) + "…" : raw;
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
              style={{
                fontFamily: "Georgia, serif",
                color: "var(--color-ql-dark)",
              }}
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
            <div
              key={asset.id}
              className="rounded-xl border p-3.5"
              style={{
                borderColor: asset.pinned
                  ? "var(--color-ql-accent)"
                  : "var(--color-ql-border)",
                background: "var(--color-ql-card)",
                transition: "border-color 0.15s",
              }}
            >
              {/* Type badge + controls */}
              <div className="flex items-center justify-between mb-2">
                <span
                  className="text-[10px] font-medium uppercase tracking-[0.08em] px-2 py-0.5 rounded-md"
                  style={{
                    background: "var(--color-ql-border)",
                    color: "var(--color-ql-muted)",
                  }}
                >
                  {ASSET_LABELS[asset.asset_type] ?? asset.asset_type}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() =>
                      pinMutation.mutate({ id: asset.id, pinned: !asset.pinned })
                    }
                    className="w-6 h-6 flex items-center justify-center text-sm"
                    style={{
                      color: asset.pinned
                        ? "var(--color-ql-accent)"
                        : "var(--color-ql-muted)",
                      opacity: asset.pinned ? 1 : 0.35,
                      transition: "opacity 0.15s, color 0.15s",
                    }}
                    title={asset.pinned ? "Unstar" : "Star"}
                  >
                    ★
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(asset.id)}
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
                <p
                  className="text-[10px] mb-1.5"
                  style={{ color: "var(--color-ql-accent)" }}
                >
                  {asset.cluster_label}
                </p>
              )}

              {/* Content preview */}
              <p
                className="text-xs leading-relaxed"
                style={{ color: "var(--color-ql-dark)" }}
              >
                {contentPreview(asset)}
              </p>

              {/* Outcome badge */}
              {asset.actual_outcome && (
                <p
                  className="text-[10px] mt-2 uppercase tracking-[0.08em]"
                  style={{ color: "var(--color-ql-muted)", opacity: 0.5 }}
                >
                  Outcome: {asset.actual_outcome}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
