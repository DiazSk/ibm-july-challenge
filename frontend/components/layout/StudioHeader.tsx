"use client";

import { useQuery } from "@tanstack/react-query";
import { getBrandProfile, getWorkbenchAssets } from "@/lib/api";
import WorkbenchDrawer from "@/components/workbench/WorkbenchDrawer";
import { useWorkbenchDrawer } from "@/lib/workbench-drawer-context";

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
