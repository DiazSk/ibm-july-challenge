import Link from "next/link";

export function BrandMark({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2.5 ${className}`}>
      <span className="grid h-8 w-8 place-items-center rounded-sm bg-gold text-ink">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 20 L12 4 L20 20" />
          <path d="M8 14 L16 14" />
        </svg>
      </span>
      <span className="font-display text-xl leading-none text-foreground">StyleSync</span>
    </Link>
  );
}

export function SiteNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <BrandMark />
        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
          <Link href="/how-it-works" className="transition hover:text-foreground">
            How it works
          </Link>
          <Link href="/manifesto" className="transition hover:text-foreground">
            Manifesto
          </Link>
          <Link href="/pricing" className="transition hover:text-foreground">
            Pricing
          </Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link
            href="/app"
            className="inline-flex items-center gap-2 rounded-sm bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
          >
            Open studio
            <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 10 L16 10 M11 5 L16 10 L11 15" />
            </svg>
          </Link>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
          <div>
            <BrandMark />
            <p className="mt-4 max-w-sm text-sm text-muted-foreground">
              Creative intelligence for Instagram creators. Built on IBM Granite 3.1. Runs locally.
            </p>
          </div>
          <FooterCol title="Product" links={[
            { href: "/how-it-works", label: "How it works" },
            { href: "/manifesto", label: "Manifesto" },
            { href: "/pricing", label: "Pricing" },
          ]} />
          <FooterCol title="Studio" links={[
            { href: "/app/dashboard", label: "Dashboard" },
            { href: "/app/brand", label: "Brand voice" },
            { href: "/app/create", label: "Generate" },
            { href: "/app/analyze", label: "Diagnose" },
            { href: "/app/discover", label: "Strategy" },
          ]} />
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Built for</p>
            <p className="mt-3 font-display text-lg text-foreground">
              IBM &laquo; Reimagine Creative Industries with AI &raquo;
            </p>
            <p className="mt-2 text-xs text-muted-foreground">July 2026 · Solo submission</p>
          </div>
        </div>
        <div className="mt-14 flex flex-col items-start justify-between gap-3 border-t border-border/60 pt-6 text-xs text-muted-foreground md:flex-row md:items-center">
          <p>&copy; 2026 StyleSync. Every voice belongs to its maker.</p>
          <p className="font-mono">v0.7 · @hot_cakesbakes</p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: { href: string; label: string }[] }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{title}</p>
      <ul className="mt-3 space-y-2 text-sm">
        {links.map((l) => (
          <li key={l.href}>
            <Link href={l.href} className="text-foreground/80 transition hover:text-gold">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
