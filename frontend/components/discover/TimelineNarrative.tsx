"use client";

interface Props {
  narrative: string;
  keyShift: string;
}

export default function TimelineNarrative({ narrative, keyShift }: Props) {
  return (
    <div className="grid grid-cols-2 gap-4 mt-5">
      <div
        className="rounded-xl border p-4"
        style={{
          borderColor: "var(--color-ql-border)",
          background: "var(--color-ql-card)",
        }}
      >
        <p
          className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Voice Arc
        </p>
        <p
          className="text-sm leading-relaxed"
          style={{ color: "var(--color-ql-dark)" }}
        >
          {narrative}
        </p>
      </div>

      <div
        className="rounded-xl border p-4"
        style={{
          borderColor: "var(--color-ql-accent)",
          background: "var(--color-ql-gap)",
        }}
      >
        <p
          className="text-[10px] font-medium uppercase tracking-[0.12em] mb-2"
          style={{ color: "var(--color-ql-accent)" }}
        >
          Key Shift
        </p>
        <p
          className="text-sm leading-relaxed"
          style={{ color: "var(--color-ql-dark)", fontFamily: "Georgia, serif" }}
        >
          {keyShift}
        </p>
      </div>
    </div>
  );
}
