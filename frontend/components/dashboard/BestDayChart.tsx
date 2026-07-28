"use client";

import type { BestTimeCell } from "@/lib/types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const PLURALS: Record<string, string> = {
  Mon: "Mondays", Tue: "Tuesdays", Wed: "Wednesdays", Thu: "Thursdays",
  Fri: "Fridays", Sat: "Saturdays", Sun: "Sundays",
};

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtTime(minOfDay: number): string {
  const h = Math.floor(minOfDay / 60);
  const m = minOfDay % 60;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const suffix = h < 12 ? "AM" : "PM";
  return m === 0 ? `${h12} ${suffix}` : `${h12}:${String(m).padStart(2, "0")} ${suffix}`;
}

export interface DayRow {
  label: string;
  posts: number;
  avgReach: number;   // median, not mean — see medianOf
}

/**
 * Median, not mean. One 5.2M-reach viral reel is enough to make its weekday look
 * 4x better than every other day on a mean, which would send the creator chasing
 * a single outlier. The median answers the question actually being asked: on a
 * normal day, when is a post likely to do well?
 */
function medianOf(values: number[]): number {
  if (values.length === 0) return 0;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : Math.round((s[mid - 1] + s[mid]) / 2);
}

/**
 * Roll the (weekday x hour, UTC) grid up to one row per weekday, shifted into
 * the brand's timezone. Pools the raw per-post reach values and takes a median,
 * so a single viral post can't crown its weekday.
 *
 * The timezone shift can move a post to a different weekday, which is why this
 * rollup can't be precomputed server-side.
 *
 * ponytail: applies today's UTC offset to every cell, so posts from the other
 * side of a DST boundary land an hour off. Carry full timestamps if that matters.
 */
export function rollupByDay(
  cells: BestTimeCell[],
  offsetMin: number,
): { days: DayRow[]; typicalMin: number | null } {
  const shifted = cells.map((c) => {
    const total = c.hour * 60 + offsetMin;
    const dayShift = Math.floor(total / 1440);
    return {
      weekday: (((c.weekday + dayShift) % 7) + 7) % 7,
      minOfDay: ((total % 1440) + 1440) % 1440,
      // Older cached payloads predate `reaches`; fall back to the cell average.
      reaches: c.reaches ?? Array(c.count).fill(c.avg_reach),
      count: c.count,
    };
  });

  const days = DAYS.map((label, wd) => {
    const rows = shifted.filter((c) => c.weekday === wd);
    const posts = rows.reduce((s, c) => s + c.count, 0);
    const pooled = rows.flatMap((c) => c.reaches);
    return { label, posts, avgReach: medianOf(pooled) };
  })
    .filter((d) => d.posts > 0)
    .sort((a, b) => b.avgReach - a.avgReach);

  // This account posts inside one narrow window, so the modal slot says more
  // than a 168-cell grid ever did.
  const byTime = new Map<number, number>();
  for (const c of shifted) byTime.set(c.minOfDay, (byTime.get(c.minOfDay) ?? 0) + c.count);
  const top = [...byTime.entries()].sort((a, b) => b[1] - a[1])[0];

  return { days, typicalMin: top ? top[0] : null };
}

/**
 * How concentrated the account's reach is: the fewest posts that together
 * account for `share` of total reach.
 *
 * This account's median post does ~1.6K reach against a ~42K mean — nearly all
 * of it comes from a handful of breakouts. Ranking days by median keeps one
 * viral post from dictating strategy, but hiding the concentration entirely
 * would misrepresent where the reach actually came from.
 */
export function breakoutConcentration(
  reaches: number[],
  share = 0.7,
): { posts: number; pct: number; total: number } | null {
  const total = reaches.reduce((s, r) => s + r, 0);
  if (total <= 0 || reaches.length < 3) return null;

  const desc = [...reaches].sort((a, b) => b - a);
  let running = 0;
  for (let i = 0; i < desc.length; i++) {
    running += desc[i];
    if (running / total >= share) {
      // Only interesting when a small minority carries the account.
      if (i + 1 > desc.length / 4) return null;
      return { posts: i + 1, pct: Math.round((running / total) * 100), total };
    }
  }
  return null;
}

/**
 * Minutes that `timeZone` is ahead of UTC right now. Falls back to UTC on an
 * unrecognised zone rather than silently using the viewer's, which would make
 * the answer depend on who's looking.
 */
export function offsetMinutesFor(timeZone: string): number {
  try {
    const now = new Date();
    const there = new Date(now.toLocaleString("en-US", { timeZone }));
    const utc = new Date(now.toLocaleString("en-US", { timeZone: "UTC" }));
    return Math.round((there.getTime() - utc.getTime()) / 60_000);
  } catch {
    return 0;
  }
}

export default function BestDayChart({
  cells,
  timeZone,
}: {
  cells: BestTimeCell[];
  timeZone: string;
}) {
  const { days, typicalMin } = rollupByDay(cells, offsetMinutesFor(timeZone));

  if (days.length === 0) {
    return (
      <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
        Not enough posts with timing data yet.
      </p>
    );
  }

  const best = days[0];

  const allReaches = cells.flatMap((c) => c.reaches ?? []);
  const typicalReach = medianOf(allReaches);
  const breakout = breakoutConcentration(allReaches);

  return (
    <div>
      {breakout && (
        <p className="text-[11px] mb-3" style={{ color: "var(--color-ql-muted)" }}>
          A typical post reaches{" "}
          <span style={{ color: "var(--color-ql-dark)" }}>{typicalReach.toLocaleString()}</span> —
          but{" "}
          <span style={{ color: "var(--color-ql-dark)" }}>
            {breakout.posts} breakout post{breakout.posts === 1 ? "" : "s"}
          </span>{" "}
          drove {breakout.pct}% of your {compact(breakout.total)} total.
        </p>
      )}

      {typicalMin !== null && (
        <p className="text-[11px] mb-4" style={{ color: "var(--color-ql-muted)" }}>
          You usually post around{" "}
          <span style={{ color: "var(--color-ql-dark)" }}>{fmtTime(typicalMin)}</span> — so the day
          matters more than the hour.
        </p>
      )}

      <div className="flex flex-col gap-2.5">
        {days.map((d, i) => (
          <div key={d.label} className="flex items-center gap-3">
            <span className="w-8 shrink-0 text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
              {d.label}
            </span>
            <div
              className="flex-1 h-2 rounded-full overflow-hidden"
              style={{ background: "var(--color-ql-gap)" }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(d.avgReach / best.avgReach) * 100}%`,
                  background: "var(--color-ql-accent)",
                  opacity: i === 0 ? 1 : 0.5,
                }}
              />
            </div>
            <span
              className="w-[5.5rem] shrink-0 text-right text-[11px] tabular-nums"
              style={{ color: "var(--color-ql-dark)" }}
            >
              {compact(d.avgReach)}
              <span style={{ color: "var(--color-ql-muted)" }}> · {d.posts}</span>
            </span>
          </div>
        ))}
      </div>

      <div className="flex items-baseline justify-between gap-3 flex-wrap mt-4">
        <p className="text-[11px]" style={{ color: "var(--color-ql-dark)" }}>
          {PLURALS[best.label]} are your most reliable day.
        </p>
        <p className="text-[10px]" style={{ color: "var(--color-ql-muted)" }}>
          typical reach · posts
        </p>
      </div>
    </div>
  );
}
