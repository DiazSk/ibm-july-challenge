"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { PillarRing } from "@/components/pillar-ring";
import { demoBrand, demoPillars, demoCaptionSample, demoDiagnosisSample, graniteInvocations } from "@/lib/marketing-data";

export default function Landing() {
  return (
    <>
      <Hero />
      <Inversion />
      <HowItWorksTeaser />
      <WhatWeSee />
      <GraniteBand />
      <LocalFirst />
      <DemoCallout />
      <FinalCta />
    </>
  );
}

function Section({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section className={`border-b border-border/60 ${className}`}>
      <div className="mx-auto max-w-7xl px-6 py-24 md:py-32">{children}</div>
    </section>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="text-[11px] uppercase tracking-[0.35em] text-gold">{children}</p>;
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border/60 grain">
      <div className="mx-auto grid max-w-7xl gap-16 px-6 pb-24 pt-20 md:grid-cols-[1.15fr_1fr] md:gap-8 md:pb-32 md:pt-28">
        <div className="flex flex-col justify-center">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
            <Eyebrow>IBM Granite 3.1 &middot; Runs locally</Eyebrow>
            <h1 className="mt-6 text-balance font-display text-6xl leading-[0.95] tracking-tight md:text-7xl lg:text-[88px]">
              Art direction,
              <br />
              <em className="text-gold">derived from you.</em>
            </h1>
            <p className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground">
              StyleSync reads a hundred of your Instagram posts, listens for the voice that&apos;s
              already there, and gives it back to you as captions, image prompts, and
              post-mortems. No prompts to write. No cloud. Just more of what makes you, you.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Link
                href="/app"
                className="inline-flex items-center gap-2 rounded-sm bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition hover:opacity-90"
              >
                Analyze my Instagram
                <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 10 L16 10 M11 5 L16 10 L11 15" />
                </svg>
              </Link>
              <Link
                href="/how-it-works"
                className="text-sm text-foreground/80 underline decoration-gold underline-offset-8 transition hover:text-gold"
              >
                See the six stages
              </Link>
            </div>
            <div className="mt-14 grid max-w-lg grid-cols-3 gap-6 border-t border-border/60 pt-8 text-sm">
              <Stat kpi={String(demoBrand.postsAnalyzed)} label="posts read" />
              <Stat kpi={String(demoBrand.graniteInvocations)} label="Granite calls" />
              <Stat kpi="0" label="cloud at inference" />
            </div>
          </motion.div>
        </div>
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.1, delay: 0.2 }}
          className="flex items-center justify-center"
        >
          <PillarRing />
        </motion.div>
      </div>
    </section>
  );
}

function Stat({ kpi, label }: { kpi: string; label: string }) {
  return (
    <div>
      <p className="font-display text-3xl text-gold">{kpi}</p>
      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
    </div>
  );
}

function Inversion() {
  return (
    <Section>
      <div className="mx-auto max-w-4xl text-center">
        <Eyebrow>The inversion</Eyebrow>
        <p className="mt-8 text-balance font-display text-4xl leading-[1.15] md:text-6xl">
          Every other AI creative tool assumes you know what you want to make.
        </p>
        <div className="my-10 gold-rule mx-auto max-w-xs" />
        <p className="text-balance font-display text-4xl italic leading-[1.15] text-gold md:text-6xl">
          StyleSync starts from the opposite question.
        </p>
        <p className="mt-10 text-lg text-muted-foreground">
          Who are you already &mdash; and how do you make more of that?
        </p>
      </div>
    </Section>
  );
}

const stages = [
  { n: "01", name: "Ingest", body: "Scrape 100+ posts, captions, engagement, watch time." },
  { n: "02", name: "Embed", body: "Local embeddings map every post into a shared space." },
  { n: "03", name: "Cluster", body: "Content pillars emerge from behavior, not self-report." },
  { n: "04", name: "Profile", body: "Granite extracts tone, vocabulary, and rhythm." },
  { n: "05", name: "Generate", body: "On-brand captions and art direction, in your voice." },
  { n: "06", name: "Diagnose", body: "The Why Engine explains what worked and what didn't." },
];

function HowItWorksTeaser() {
  return (
    <Section className="bg-secondary/30">
      <div className="mb-16 flex flex-wrap items-end justify-between gap-6">
        <div>
          <Eyebrow>How it works</Eyebrow>
          <h2 className="mt-4 max-w-2xl font-display text-5xl md:text-6xl">Six stages, one voice.</h2>
        </div>
        <Link href="/how-it-works" className="text-sm text-gold underline underline-offset-4 hover:opacity-80">
          Read the full pipeline &rarr;
        </Link>
      </div>
      <div className="grid gap-px overflow-hidden rounded-md border border-border md:grid-cols-3">
        {stages.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: i * 0.05 }}
            className="relative bg-background p-8"
          >
            <p className="font-mono text-xs text-gold">{s.n}</p>
            <h3 className="mt-4 font-display text-3xl">{s.name}</h3>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}

function WhatWeSee() {
  return (
    <Section>
      <div className="mb-16">
        <Eyebrow>What StyleSync sees</Eyebrow>
        <h2 className="mt-4 max-w-3xl font-display text-5xl md:text-6xl">
          A living portrait of how you already speak.
        </h2>
      </div>

      <div className="grid gap-6 md:grid-cols-6">
        <Card className="md:col-span-3 md:row-span-2">
          <CardHeader label="Content pillars by engagement" tag="Granite #1" />
          <div className="mt-6 space-y-3">
            {demoPillars.map((p) => (
              <div key={p.id} className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
                <span className="flex-1 truncate text-sm">{p.name}</span>
                <span className="font-mono text-xs text-muted-foreground">{p.avgEngagement}%</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="md:col-span-3">
          <CardHeader label="Generated caption" tag="Granite #2" />
          <p className="mt-5 font-display text-xl italic leading-snug text-foreground/95">
            &ldquo;{demoCaptionSample.caption}&rdquo;
          </p>
          <p className="mt-4 text-xs text-muted-foreground">Pillar &middot; {demoCaptionSample.pillar}</p>
        </Card>

        <Card className="md:col-span-3">
          <CardHeader label="Brand" tag="@hot_cakesbakes" />
          <p className="mt-5 text-sm text-muted-foreground">{demoBrand.niche}</p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            {demoBrand.postsAnalyzed} posts &middot; {demoBrand.pillarCount} pillars
          </p>
        </Card>

        <Card className="md:col-span-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <CardHeader label="Why Engine" tag="Granite #4" />
            <span className="rounded-sm border border-destructive/40 bg-destructive/10 px-2.5 py-1 text-[10px] uppercase tracking-widest text-destructive">
              {demoDiagnosisSample.verdict}
            </span>
          </div>
          <p className="mt-5 font-display text-2xl leading-snug">&ldquo;{demoDiagnosisSample.postCaption}&rdquo;</p>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] text-gold">Diagnosis</p>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{demoDiagnosisSample.diagnosis}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] text-gold">Brand voice gap</p>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{demoDiagnosisSample.brandGap}</p>
            </div>
          </div>
        </Card>
      </div>
    </Section>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`hairline rounded-md bg-card p-6 md:p-8 ${className}`}>{children}</div>;
}

function CardHeader({ label, tag }: { label: string; tag: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <p className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground">{label}</p>
      <p className="font-mono text-[10px] text-gold">{tag}</p>
    </div>
  );
}

function GraniteBand() {
  return (
    <section className="relative overflow-hidden border-b border-border/60 bg-black grain">
      <div className="mx-auto max-w-7xl px-6 py-32">
        <div className="grid gap-16 md:grid-cols-[1fr_1.2fr]">
          <div>
            <Eyebrow>Powered by IBM Granite 3.1 8B</Eyebrow>
            <h2 className="mt-6 font-display text-5xl leading-tight text-white md:text-6xl">
              Granite is not
              <br />
              <em className="text-gold">decoration.</em>
            </h2>
            <p className="mt-8 max-w-md text-white/70">
              Fourteen coordinated Granite invocations sit at the core of the product &mdash; brand
              extraction, generation, diagnosis, strategy. Remove them and there is no StyleSync.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-px bg-border md:grid-cols-3">
            {graniteInvocations.map(([n, t]) => (
              <div key={n} className="bg-background p-5">
                <p className="font-mono text-[10px] text-gold">{n}</p>
                <p className="mt-2 text-sm">{t}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function LocalFirst() {
  return (
    <section className="border-b border-border/60">
      <div className="mx-auto max-w-5xl px-6 py-32 text-center">
        <Eyebrow>Local-first</Eyebrow>
        <p className="mt-6 text-balance font-display text-4xl leading-tight md:text-6xl">
          It works in a room with <em className="text-gold">no internet.</em>
        </p>
        <p className="mx-auto mt-6 max-w-xl text-muted-foreground">
          Audio stays on device. Data stays on device. Inference stays on device. Your voice never
          leaves the room it was made in.
        </p>
      </div>
    </section>
  );
}

function DemoCallout() {
  return (
    <Section className="bg-secondary/30">
      <div className="grid items-center gap-12 md:grid-cols-[1fr_1.3fr]">
        <div>
          <Eyebrow>Demo brand</Eyebrow>
          <h2 className="mt-4 font-display text-5xl leading-tight md:text-6xl">{demoBrand.handle}</h2>
          <p className="mt-6 text-muted-foreground">
            {demoBrand.niche}. {demoBrand.postsAnalyzed} posts, {demoBrand.pillarCount} pillars, and a
            Bomboloni pillar that pulls 11.1% average engagement &mdash; the highest of any content
            territory, on a fraction of the post volume.
          </p>
          <Link href="/app" className="mt-8 inline-flex items-center gap-2 text-sm text-gold underline underline-offset-4">
            Enter the studio &rarr;
          </Link>
        </div>
        <div className="hairline rounded-md bg-card p-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-display text-2xl">Bomboloni</p>
              <p className="mt-1 text-xs text-muted-foreground">Richness rank #1 &middot; 11.1% avg engagement</p>
            </div>
            <span className="rounded-sm bg-gold/15 px-2.5 py-1 text-[10px] uppercase tracking-widest text-gold">
              Underutilized
            </span>
          </div>
          <div className="my-6 gold-rule" />
          <p className="font-display text-xl italic leading-snug">
            &ldquo;{demoCaptionSample.caption}&rdquo;
          </p>
          <p className="mt-4 text-xs text-muted-foreground">Volume rank &middot; #4 of 5</p>
        </div>
      </div>
    </Section>
  );
}

function FinalCta() {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto max-w-5xl px-6 py-32 text-center">
        <h2 className="text-balance font-display text-5xl leading-[1.05] md:text-7xl">
          You&apos;ve already made
          <br />
          <em className="text-gold">a thousand decisions.</em>
        </h2>
        <p className="mx-auto mt-6 max-w-xl text-muted-foreground">
          StyleSync just remembers all of them, and helps you make the next one.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/app"
            className="inline-flex items-center gap-2 rounded-sm bg-primary px-7 py-3.5 text-sm font-medium text-primary-foreground transition hover:opacity-90"
          >
            Open the studio
          </Link>
          <Link href="/manifesto" className="text-sm text-foreground/80 underline decoration-gold underline-offset-8">
            Read the manifesto
          </Link>
        </div>
      </div>
    </section>
  );
}
