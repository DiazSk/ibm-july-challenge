"use client";

import { useQuery } from "@tanstack/react-query";
import { getClusters } from "@/lib/api";

interface Props {
  product: string;
  occasion: string;
  desiredFeel: string;
  clusterId: number;
  onProductChange: (v: string) => void;
  onOccasionChange: (v: string) => void;
  onDesiredFeelChange: (v: string) => void;
  onClusterChange: (v: number) => void;
  onGenerate: () => void;
  onClear: () => void;
  loading: boolean;
}

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
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

export default function CaptionBrief({
  product,
  occasion,
  desiredFeel,
  clusterId,
  onProductChange,
  onOccasionChange,
  onDesiredFeelChange,
  onClusterChange,
  onGenerate,
  onClear,
  loading,
}: Props) {
  const { data: clusters } = useQuery({
    queryKey: ["clusters"],
    queryFn: getClusters,
  });

  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  const canGenerate = product.trim() && occasion.trim() && desiredFeel.trim();

  return (
    <div
      className="rounded-xl border p-5"
      style={{
        borderColor: "var(--color-ql-border)",
        background: "var(--color-ql-card)",
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3
          className="text-base"
          style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
        >
          Caption Brief
        </h3>
        <button
          onClick={onClear}
          className="text-[11px] px-2 py-1 rounded border transition-colors"
          style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
        >
          Clear
        </button>
      </div>

      <div className="flex flex-col gap-4">
        <Field label="Product">
          <input
            type="text"
            value={product}
            onChange={(e) => onProductChange(e.target.value)}
            placeholder="e.g. Pistachio Rose Bomboloni"
            className={inputClass}
            style={inputStyle}
            onFocus={(e) =>
              (e.target.style.borderColor = "var(--color-ql-accent)")
            }
            onBlur={(e) =>
              (e.target.style.borderColor = "var(--color-ql-border)")
            }
          />
        </Field>

        <Field label="Occasion">
          <input
            type="text"
            value={occasion}
            onChange={(e) => onOccasionChange(e.target.value)}
            placeholder="e.g. Friday evening drop"
            className={inputClass}
            style={inputStyle}
            onFocus={(e) =>
              (e.target.style.borderColor = "var(--color-ql-accent)")
            }
            onBlur={(e) =>
              (e.target.style.borderColor = "var(--color-ql-border)")
            }
          />
        </Field>

        <Field label="Desired Feel">
          <input
            type="text"
            value={desiredFeel}
            onChange={(e) => onDesiredFeelChange(e.target.value)}
            placeholder="e.g. indulgent and intimate"
            className={inputClass}
            style={inputStyle}
            onFocus={(e) =>
              (e.target.style.borderColor = "var(--color-ql-accent)")
            }
            onBlur={(e) =>
              (e.target.style.borderColor = "var(--color-ql-border)")
            }
          />
        </Field>

        {clusterList.length > 0 && (
          <Field label="Brand Voice">
            <div className="flex flex-col gap-1.5">
              {clusterList.map((c) => (
                <button
                  key={c.cluster_id}
                  onClick={() => onClusterChange(c.cluster_id)}
                  className="flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all"
                  style={{
                    borderColor:
                      clusterId === c.cluster_id
                        ? "var(--color-ql-dark)"
                        : "var(--color-ql-border)",
                    background:
                      clusterId === c.cluster_id
                        ? "var(--color-ql-gap)"
                        : "transparent",
                  }}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{
                      background: CLUSTER_COLORS[c.cluster_id] ?? "var(--color-cluster-1)",
                    }}
                  />
                  <span
                    className="text-xs"
                    style={{ color: "var(--color-ql-dark)" }}
                  >
                    {c.pillar}
                  </span>
                  <span
                    className="text-[11px] ml-auto"
                    style={{ color: "var(--color-ql-muted)" }}
                  >
                    {c.post_count}p
                  </span>
                </button>
              ))}
            </div>
          </Field>
        )}

        <button
          onClick={onGenerate}
          disabled={!canGenerate || loading}
          className="w-full py-3 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
          style={{
            background: "var(--color-ql-dark)",
            color: "var(--color-ql-bg)",
          }}
        >
          {loading ? (
            <span className="animate-pulse">Generating captions…</span>
          ) : (
            "Generate Captions"
          )}
        </button>
      </div>
    </div>
  );
}
