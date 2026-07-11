"use client";

import { motion } from "framer-motion";
import { demoPillars, demoBrand } from "@/lib/marketing-data";

// Rotating pillar ring — the signature hero animation.
export function PillarRing() {
  const size = 460;
  const r = 180;
  const cx = size / 2;
  const cy = size / 2;
  const maxEngagement = Math.max(...demoPillars.map((p) => p.avgEngagement));

  return (
    <div className="relative mx-auto" style={{ width: size, height: size, maxWidth: "100%" }}>
      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
      >
        <svg viewBox={`0 0 ${size} ${size}`} className="h-full w-full">
          <defs>
            <radialGradient id="ring-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--color-gold)" stopOpacity="0.15" />
              <stop offset="70%" stopColor="var(--color-gold)" stopOpacity="0" />
            </radialGradient>
          </defs>
          <circle cx={cx} cy={cy} r={r + 40} fill="url(#ring-glow)" />
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="var(--color-gold)"
            strokeOpacity="0.25"
            strokeDasharray="1 6"
          />
          <circle cx={cx} cy={cy} r={r - 40} fill="none" stroke="var(--color-gold)" strokeOpacity="0.1" />
          {demoPillars.map((p, i) => {
            const angle = (i / demoPillars.length) * Math.PI * 2 - Math.PI / 2;
            const x = cx + Math.cos(angle) * r;
            const y = cy + Math.sin(angle) * r;
            const rr = 8 + (p.avgEngagement / maxEngagement) * 14;
            return (
              <g key={p.id}>
                <circle cx={x} cy={y} r={rr + 10} fill={p.color} opacity="0.08" />
                <circle cx={x} cy={y} r={rr} fill={p.color} />
              </g>
            );
          })}
        </svg>
      </motion.div>

      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-[0.35em] text-muted-foreground">Brand voice</p>
          <p className="mt-2 font-display text-5xl text-gold">{demoBrand.pillarCount}</p>
          <p className="mt-1 text-xs text-muted-foreground">content pillars · {demoBrand.postsAnalyzed} posts</p>
        </div>
      </div>

      {/* Static labels around the ring */}
      {demoPillars.map((p, i) => {
        const angle = (i / demoPillars.length) * Math.PI * 2 - Math.PI / 2;
        const lx = 50 + ((Math.cos(angle) * (r + 30)) / size) * 100;
        const ly = 50 + ((Math.sin(angle) * (r + 30)) / size) * 100;
        return (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.08, duration: 0.6 }}
            className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap text-[10px] uppercase tracking-[0.25em] text-muted-foreground"
            style={{ left: `${lx}%`, top: `${ly}%` }}
          >
            {p.name}
          </motion.div>
        );
      })}
    </div>
  );
}
