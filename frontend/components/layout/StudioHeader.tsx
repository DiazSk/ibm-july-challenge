"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getBrandProfile, getWorkbenchAssets } from "@/lib/api";
import WorkbenchDrawer from "@/components/workbench/WorkbenchDrawer";
import { SidebarBody } from "@/components/layout/StudioSidebar";
import { useWorkbenchDrawer } from "@/lib/workbench-drawer-context";

/** Mobile-only nav: the desktop sidebar is `hidden md:flex`, so on small
 *  screens the hamburger opens a slide-over with the same navigation. */
function MobileNav() {
  const [open, setOpen] = useState(false);
  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(true)}
        aria-label="Open menu"
        className="grid h-9 w-9 place-items-center rounded-lg border"
        style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-dark)" }}
      >
        <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M3 5h14M3 10h14M3 15h14" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div className="fixed inset-0 z-50">
          <div
            className="absolute inset-0"
            style={{ background: "color-mix(in oklch, var(--color-ink) 45%, transparent)" }}
            onClick={() => setOpen(false)}
          />
          <aside
            className="absolute left-0 top-0 flex h-full w-64 max-w-[80vw] flex-col border-r"
            style={{ background: "var(--color-ql-sidebar)", borderColor: "var(--color-ql-border)" }}
            onClick={() => setOpen(false)}
          >
            <SidebarBody onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
    </div>
  );
}

export default function StudioHeader() {
  const { open: drawerOpen, setOpen: setDrawerOpen } = useWorkbenchDrawer();

  const { data: profile } = useQuery({
    queryKey: ["brand-profile"],
    queryFn: getBrandProfile,
  });
  const { data: assets = [] } = useQuery({
    queryKey: ["workbench"],
    queryFn: () => getWorkbenchAssets(),
    staleTime: 30_000,
  });
  const count = assets.length;

  return (
    <>
      <header
        className="flex h-16 shrink-0 items-center justify-between border-b px-6 md:px-10"
        style={{ background: "var(--color-ql-card)", borderColor: "var(--color-ql-border)" }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <MobileNav />
          <div className="min-w-0">
            <p
              className="truncate text-[10px] uppercase tracking-[0.25em]"
              style={{ color: "var(--color-ql-muted)" }}
            >
              Active brand
            </p>
            <p className="truncate text-lg" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
              {profile?.handle ?? "@hot_cakesbakes"}
            </p>
          </div>
        </div>
        <button
          onClick={() => setDrawerOpen(true)}
          className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[11px] transition-all"
          style={{
            borderColor: count > 0 ? "var(--color-ql-accent)" : "var(--color-ql-border)",
            color: count > 0 ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
          }}
        >
          {count > 0 ? `Saved (${count})` : "Saved"}
        </button>
      </header>

      <WorkbenchDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
