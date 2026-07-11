"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import WhyEngineForm from "@/components/analyze/WhyEngineForm";
import DiagnosisPanel from "@/components/analyze/DiagnosisPanel";
import RecoveryBrief from "@/components/analyze/RecoveryBrief";
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

export default function AnalyzePage() {
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
      <div className="flex justify-end mb-2">
        <button
          onClick={handleClearForm}
          className="text-[11px] px-2 py-1 rounded border transition-colors"
          style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
        >
          Clear
        </button>
      </div>

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
    </motion.div>
  );
}
