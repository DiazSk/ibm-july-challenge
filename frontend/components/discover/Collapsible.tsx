"use client";

import { useState, type ReactNode } from "react";

/**
 * Progressive disclosure for the Strategy page. The detail panels aren't wrong,
 * there were just too many of them competing for first attention — so they stay
 * one click away instead of on the critical path.
 */
export default function Collapsible({
  label,
  hint,
  children,
  defaultOpen = false,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section
      className="rounded-xl border"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left"
      >
        <span>
          <span className="text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
            {label}
          </span>
          {hint && (
            <span className="block text-[11px] mt-0.5" style={{ color: "var(--color-ql-muted)" }}>
              {hint}
            </span>
          )}
        </span>
        <span
          className="shrink-0 text-[11px] transition-transform"
          style={{
            color: "var(--color-ql-muted)",
            transform: open ? "rotate(90deg)" : "none",
          }}
          aria-hidden
        >
          ▸
        </span>
      </button>

      {open && <div className="px-5 pb-5 flex flex-col gap-6">{children}</div>}
    </section>
  );
}
