"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { getWorkbenchAssets } from "@/lib/api";
import WorkbenchDrawer from "@/components/workbench/WorkbenchDrawer";

const TABS = [
  { href: "/create", label: "Create" },
  { href: "/analyze", label: "Analyze" },
  { href: "/discover", label: "Discover" },
] as const;

export default function NavTabs() {
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { data: assets = [] } = useQuery({
    queryKey: ["workbench"],
    queryFn: () => getWorkbenchAssets(),
    staleTime: 30_000,
  });
  const count = assets.length;

  return (
    <>
      <nav
        className="flex items-center justify-between border-b px-6"
        style={{
          background: "var(--color-ql-card)",
          borderColor: "var(--color-ql-border)",
        }}
      >
        <div className="flex items-center gap-0">
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
        </div>

        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] rounded-lg border transition-all"
          style={{
            borderColor:
              count > 0 ? "var(--color-ql-accent)" : "var(--color-ql-border)",
            color:
              count > 0 ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
          }}
        >
          {count > 0 ? `Saved (${count})` : "Saved"}
        </button>
      </nav>

      <WorkbenchDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
