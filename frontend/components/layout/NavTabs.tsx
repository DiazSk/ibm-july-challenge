"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/create", label: "Create" },
  { href: "/analyze", label: "Analyze" },
  { href: "/discover", label: "Discover" },
] as const;

export default function NavTabs() {
  const pathname = usePathname();

  return (
    <nav
      className="flex items-center gap-0 border-b px-6"
      style={{
        background: "var(--color-ql-card)",
        borderColor: "var(--color-ql-border)",
      }}
    >
      {TABS.map(({ href, label }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "px-5 py-3.5 text-sm border-b-2 transition-colors -mb-px",
              active
                ? "border-ql-dark font-medium"
                : "border-transparent hover:border-ql-border"
            )}
            style={{
              color: active
                ? "var(--color-ql-dark)"
                : "var(--color-ql-muted)",
              borderBottomColor: active
                ? "var(--color-ql-dark)"
                : "transparent",
              fontFamily: "var(--font-family-sans)",
            }}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
