"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getBrandProfile } from "@/lib/api";
import { BrandMark } from "@/components/site-chrome";

const NAV = [
  { href: "/app/dashboard", label: "Dashboard",   exact: true,  icon: DashboardIcon },
  { href: "/app/brand",     label: "Brand voice",  exact: false, icon: VoiceIcon },
  { href: "/app/create",    label: "Generate",     exact: false, icon: SparkIcon },
  { href: "/app/analyze",   label: "Diagnose",     exact: false, icon: PulseIcon },
  { href: "/app/discover",  label: "Strategy",     exact: false, icon: MapIcon },
  { href: "/app/agents",    label: "Agents",       exact: false, icon: AgentsIcon },
  { href: "/app/triage",    label: "Inbox Triage", exact: false, icon: InboxIcon },
] as const;

export default function StudioSidebar() {
  return (
    <aside
      className="hidden w-64 shrink-0 flex-col border-r md:flex"
      style={{ background: "var(--color-ql-sidebar)", borderColor: "var(--color-ql-border)" }}
    >
      <SidebarBody />
    </aside>
  );
}

/**
 * The sidebar's contents (brand mark, nav, profile footer) — shared by the
 * desktop `aside` and the mobile slide-over drawer. `onNavigate` lets the
 * mobile drawer close itself when a link is tapped.
 */
export function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { data: profile } = useQuery({
    queryKey: ["brand-profile"],
    queryFn: getBrandProfile,
  });

  const displayName = profile?.brand_name ?? "HotCakes Bakes";
  const handle = profile?.handle ?? "@hot_cakesbakes";
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <>
      <div className="flex h-16 items-center border-b px-6" style={{ borderColor: "var(--color-ql-border)" }}>
        <BrandMark />
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-6">
        <p className="px-3 text-[10px] uppercase tracking-[0.25em]" style={{ color: "var(--color-ql-muted)" }}>
          Studio
        </p>
        <ul className="mt-3 space-y-1">
          {NAV.map((n) => {
            const active = n.exact ? pathname === n.href : pathname.startsWith(n.href);
            const Icon = n.icon;
            return (
              <li key={n.href}>
                <Link
                  href={n.href}
                  onClick={onNavigate}
                  className="flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors"
                  style={{
                    background: active ? "var(--color-ql-card)" : "transparent",
                    color: active ? "var(--color-ql-dark)" : "var(--color-ql-muted)",
                  }}
                >
                  <Icon
                    className="h-4 w-4 shrink-0"
                    style={{ color: active ? "var(--color-ql-accent)" : "currentColor" }}
                  />
                  {n.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="border-t p-4" style={{ borderColor: "var(--color-ql-border)" }}>
        <div className="flex items-center gap-3">
          <div
            className="grid h-9 w-9 place-items-center rounded-full font-display"
            style={{ background: "var(--gradient-gold)", color: "var(--color-ink)" }}
          >
            {initial}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm" style={{ color: "var(--color-ql-dark)" }}>
              {displayName}
            </p>
            <p className="truncate text-xs" style={{ color: "var(--color-ql-muted)" }}>
              {handle}
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function DashboardIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="3" width="6" height="8" rx="1" />
      <rect x="3" y="13" width="6" height="4" rx="1" />
      <rect x="11" y="3" width="6" height="4" rx="1" />
      <rect x="11" y="9" width="6" height="8" rx="1" />
    </svg>
  );
}
function VoiceIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M10 3v14M6 6v8M14 6v8M2 9v2M18 9v2" strokeLinecap="round" />
    </svg>
  );
}
function SparkIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path
        d="M10 2v4M10 14v4M2 10h4M14 10h4M4.5 4.5l2.8 2.8M12.7 12.7l2.8 2.8M4.5 15.5l2.8-2.8M12.7 7.3l2.8-2.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
function PulseIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2 10h4l2-5 4 10 2-5h4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function MapIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2 5l5-2 6 2 5-2v12l-5 2-6-2-5 2z M7 3v14 M13 5v14" />
    </svg>
  );
}
function InboxIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M2 11l3-7h10l3 7v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5z" strokeLinejoin="round" />
      <path d="M2 11h4.5l1 2h5l1-2H18" strokeLinejoin="round" />
    </svg>
  );
}
function AgentsIcon({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 20 20" className={className} style={style} fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="7" cy="7" r="3" />
      <circle cx="13" cy="7" r="3" />
      <circle cx="10" cy="14" r="3" />
      <path d="M7 10v1M13 10v1M10 10v1" strokeLinecap="round" />
    </svg>
  );
}
