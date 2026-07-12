"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import TriageBatchInput from "@/components/triage/TriageBatchInput";
import TriageResultsList from "@/components/triage/TriageResultsList";
import { runTriage, saveAsset } from "@/lib/api";
import type { TriageResult, TriageBatchResponse } from "@/lib/types";

export default function TriagePage() {
  const queryClient = useQueryClient();

  const [text, setText] = useState("");
  const [clusterId, setClusterId] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TriageBatchResponse | null>(null);

  async function handleSubmit() {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return;

    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await runTriage(lines, clusterId);
      setResult(res);
    } catch {
      setError("Something went wrong triaging these messages — try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveReply(item: TriageResult, reply: string) {
    try {
      await saveAsset({
        asset_type: "triage_reply",
        content: {
          original_message: item.original_message,
          category: item.category,
          drafted_reply: reply,
        },
        cluster_id: clusterId,
        source_tab: "triage",
      });
      queryClient.invalidateQueries({ queryKey: ["workbench"] });
    } catch {
      // silent
    }
  }

  return (
    <motion.div
      className="max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="mb-4">
        <p
          className="text-[10px] font-medium uppercase tracking-[0.18em] mb-1"
          style={{ color: "var(--color-ql-accent)" }}
        >
          Inbox Triage
        </p>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          Classify &amp; draft replies
        </h1>
      </div>

      <TriageBatchInput
        text={text}
        onTextChange={setText}
        clusterId={clusterId}
        onClusterChange={setClusterId}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error && (
        <p className="text-xs mt-3" style={{ color: "var(--color-verdict-failed)" }}>
          {error}
        </p>
      )}

      {result && <TriageResultsList results={result.results} onSaveReply={handleSaveReply} />}
    </motion.div>
  );
}
