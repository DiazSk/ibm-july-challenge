"use client";

import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { getBrandProfile, getClusters } from "@/lib/api";

const CLUSTER_COLORS = [
  "var(--color-cluster-0)",
  "var(--color-cluster-1)",
  "var(--color-cluster-2)",
  "var(--color-cluster-3)",
  "var(--color-cluster-4)",
] as const;

function Tag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "warn" }) {
  return (
    <span
      className="text-[11px] px-2.5 py-1 rounded-full border"
      style={{
        borderColor: tone === "warn" ? "var(--color-verdict-failed)" : "var(--color-ql-border)",
        color: tone === "warn" ? "var(--color-verdict-failed)" : "var(--color-ql-dark)",
        background: tone === "warn"
          ? "color-mix(in oklch, var(--color-verdict-failed) 6%, transparent)"
          : "var(--color-ql-card)",
      }}
    >
      {children}
    </span>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      className="rounded-xl border p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <p
        className="text-[10px] font-medium uppercase tracking-[0.12em] mb-4"
        style={{ color: "var(--color-ql-muted)" }}
      >
        {title}
      </p>
      {children}
    </section>
  );
}

export default function BrandVoicePage() {
  const { data: profile } = useQuery({ queryKey: ["brand-profile"], queryFn: getBrandProfile });
  const { data: clusters } = useQuery({ queryKey: ["clusters"], queryFn: getClusters });

  const clusterList = clusters
    ? Object.values(clusters).sort((a, b) => a.cluster_id - b.cluster_id)
    : [];

  const vocabulary = Array.from(new Set(profile?.recurring_words ?? []));
  const phrases = Array.from(new Set(profile?.signature_phrases ?? []));

  return (
    <motion.div
      className="max-w-4xl mx-auto flex flex-col gap-8"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div>
        <p
          className="text-[10px] font-medium uppercase tracking-[0.18em] mb-1"
          style={{ color: "var(--color-ql-accent)" }}
        >
          Brand Voice
        </p>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          {profile?.brand_name ?? "Your brand"}
        </h1>
        {profile?.target_audience && (
          <p className="text-sm mt-2 max-w-lg" style={{ color: "var(--color-ql-muted)" }}>
            {profile.target_audience}
          </p>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Tone descriptors — real adjectives from Granite, no fabricated axis positions */}
        <SectionCard title="Tone">
          {!profile?.tone_descriptors?.length && (
            <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
              No tone descriptors yet.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {profile?.tone_descriptors.map((t) => (
              <Tag key={t}>{t}</Tag>
            ))}
          </div>
        </SectionCard>

        {/* Vocabulary — single recurring words, real tag cloud */}
        <SectionCard title="Signature Vocabulary">
          {vocabulary.length === 0 && (
            <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
              No signature vocabulary yet.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {vocabulary.map((w) => (
              <Tag key={w}>{w}</Tag>
            ))}
          </div>
        </SectionCard>

        {/* Avoid — real avoided_terms, a genuine "Don't" list */}
        <SectionCard title="Avoid">
          {!profile?.avoided_terms?.length && (
            <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
              No avoided terms recorded.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {profile?.avoided_terms.map((t) => (
              <Tag key={t} tone="warn">
                {t}
              </Tag>
            ))}
          </div>
        </SectionCard>
      </div>

      {/* Signature phrases — full sentences, rendered as a quoted list, not tiny pills */}
      <SectionCard title="Signature Phrases">
        {phrases.length === 0 && (
          <p className="text-xs" style={{ color: "var(--color-ql-muted)" }}>
            No signature phrases yet.
          </p>
        )}
        <ul className="flex flex-col gap-2">
          {phrases.map((p) => (
            <li
              key={p}
              className="text-sm italic leading-relaxed"
              style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
            >
              &ldquo;{p}&rdquo;
            </li>
          ))}
        </ul>
      </SectionCard>

      {/* Pillar signature cards */}
      <div>
        <p
          className="text-[10px] font-medium uppercase tracking-[0.12em] mb-4"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Pillar Signatures
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          {clusterList.map((c) => (
            <div
              key={c.cluster_id}
              className="rounded-xl border p-4"
              style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ background: CLUSTER_COLORS[c.cluster_id % CLUSTER_COLORS.length] }}
                />
                <span className="text-sm font-medium" style={{ color: "var(--color-ql-dark)" }}>
                  {c.pillar}
                </span>
                <span className="text-[11px] ml-auto" style={{ color: "var(--color-ql-muted)" }}>
                  {c.post_count} posts
                </span>
              </div>
              {c.sample_captions?.[0] && (
                <p
                  className="text-xs italic leading-relaxed"
                  style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-muted)" }}
                >
                  &ldquo;{c.sample_captions[0]}&rdquo;
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
