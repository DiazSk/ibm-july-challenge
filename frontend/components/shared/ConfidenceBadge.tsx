"use client";

interface Props {
  score: number;
  rationale: string;
}

function tone(score: number): { color: string; label: string } {
  if (score >= 75) return { color: "var(--color-verdict-succeeded)", label: "Likely accurate" };
  if (score >= 50) return { color: "var(--color-verdict-underperformed)", label: "Worth a second look" };
  return { color: "var(--color-verdict-failed)", label: "Verify before publishing" };
}

export default function ConfidenceBadge({ score, rationale }: Props) {
  const { color, label } = tone(score);

  return (
    <span
      title={rationale}
      className="inline-flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.08em] px-2 py-0.5 rounded-full border"
      style={{
        borderColor: color,
        color,
        background: `color-mix(in oklch, ${color} 8%, transparent)`,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
