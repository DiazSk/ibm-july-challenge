"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import WhyEngineForm from "@/components/analyze/WhyEngineForm";
import DiagnosisPanel from "@/components/analyze/DiagnosisPanel";
import RecoveryBrief from "@/components/analyze/RecoveryBrief";
import PostDiagnosisList from "@/components/analyze/PostDiagnosisList";
import { runWhyEngine } from "@/lib/api";
import { useLocalStorage } from "@/lib/useLocalStorage";
import type { WhyEngineRequest, WhyEngineResult } from "@/lib/types";

const DEFAULT_FORM: WhyEngineRequest = {
  caption: "",
  post_type: "Reel",
  views: 0,
  reach: 0,
  likes: 0,
  comments: 0,
  shares: 0,
  saves: 0,
  cluster_id: 0,
};

type View = "posts" | "manual";

export default function AnalyzePage() {
  const [view, setView] = useState<View>("posts");
  const [form, setForm, clearForm] = useLocalStorage<WhyEngineRequest>("ss_analyze_form", DEFAULT_FORM);
  const [result, setResult] = useState<WhyEngineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleClearForm() {
    clearForm();
    setResult(null);
    setError(null);
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await runWhyEngine(form);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Diagnosis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      className="max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center gap-2 mb-4">
        {([["posts", "My posts"], ["manual", "Manual"]] as const).map(([key, label]) => {
          const active = view === key;
          return (
            <button
              key={key}
              onClick={() => setView(key)}
              className="text-xs px-3 py-1.5 rounded-lg border transition-colors"
              style={{
                borderColor: active ? "var(--color-ql-dark)" : "var(--color-ql-border)",
                background: active ? "var(--color-ql-dark)" : "transparent",
                color: active ? "var(--color-ql-bg)" : "var(--color-ql-muted)",
              }}
            >
              {label}
            </button>
          );
        })}
        {view === "manual" && (
          <button
            onClick={handleClearForm}
            className="text-[11px] px-2 py-1 rounded border transition-colors ml-auto"
            style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
          >
            Clear
          </button>
        )}
      </div>

      {view === "posts" && <PostDiagnosisList />}

      {view === "manual" && (
      <>
      <WhyEngineForm
        value={form}
        onChange={setForm}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error && (
        <p
          className="mt-4 text-sm"
          style={{ color: "var(--color-verdict-failed)" }}
        >
          {error}
        </p>
      )}

      {result && <DiagnosisPanel result={result} />}
      {result && <RecoveryBrief result={result} clusterId={form.cluster_id} />}
      </>
      )}
    </motion.div>
  );
}
