"use client";

import { useState } from "react";
import WhyEngineForm from "@/components/analyze/WhyEngineForm";
import DiagnosisPanel from "@/components/analyze/DiagnosisPanel";
import { runWhyEngine } from "@/lib/api";
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
  const [form, setForm] = useState<WhyEngineRequest>(DEFAULT_FORM);
  const [result, setResult] = useState<WhyEngineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    <div className="max-w-2xl mx-auto">
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
    </div>
  );
}
