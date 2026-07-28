"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import TriageBatchInput from "@/components/triage/TriageBatchInput";
import InboxInput from "@/components/triage/InboxInput";
import TriageResultsList from "@/components/triage/TriageResultsList";
import { runTriage, saveAsset, getInboxComments, sendCommentReply, connectInstagramUrl } from "@/lib/api";
import type { TriageResult, TriageBatchResponse, InboxComment } from "@/lib/types";

type Mode = "instagram" | "paste";

export default function TriagePage() {
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<Mode>("instagram");
  const [text, setText] = useState("");
  const [clusterId, setClusterId] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reconnect, setReconnect] = useState(false);
  const [result, setResult] = useState<TriageBatchResponse | null>(null);
  const [comments, setComments] = useState<InboxComment[] | undefined>(undefined);

  function reset() {
    setError("");
    setReconnect(false);
    setResult(null);
    setComments(undefined);
  }

  async function handlePasteSubmit() {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return;
    reset();
    setLoading(true);
    try {
      setResult(await runTriage(lines, clusterId));
    } catch {
      setError("Something went wrong triaging these messages — try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadComments() {
    reset();
    setLoading(true);
    try {
      const { comments: fetched } = await getInboxComments();
      if (fetched.length === 0) {
        setError("No recent comments found on your latest posts.");
        return;
      }
      const res = await runTriage(fetched.map((c) => c.text), clusterId);
      setComments(fetched);
      setResult(res);
    } catch (e) {
      // apiFetch throws "<status> <body>" — a 403 means the token lacks the comments scope.
      if (e instanceof Error && e.message.startsWith("403")) setReconnect(true);
      else setError("Couldn't load your comments — is the server running and the account connected?");
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(commentId: string, reply: string) {
    await sendCommentReply(commentId, reply); // ResultCard handles its own success/error UI
  }

  async function handleSaveReply(item: TriageResult, reply: string) {
    try {
      await saveAsset({
        asset_type: "triage_reply",
        content: { original_message: item.original_message, category: item.category, drafted_reply: reply },
        cluster_id: clusterId,
        source_tab: "triage",
      });
      queryClient.invalidateQueries({ queryKey: ["workbench"] });
    } catch {
      // silent
    }
  }

  const tabStyle = (active: boolean) => ({
    color: active ? "var(--color-ql-bg)" : "var(--color-ql-muted)",
    background: active ? "var(--color-ql-dark)" : "transparent",
    border: `1px solid ${active ? "var(--color-ql-dark)" : "var(--color-ql-border)"}`,
  });

  return (
    <motion.div
      className="max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="mb-4">
        <p className="text-[10px] font-medium uppercase tracking-[0.18em] mb-1" style={{ color: "var(--color-ql-accent)" }}>
          Inbox Triage
        </p>
        <h1 className="text-2xl" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
          Classify &amp; reply
        </h1>
      </div>

      {/* Source toggle */}
      <div className="flex gap-1.5 mb-4">
        <button onClick={() => { setMode("instagram"); reset(); }} className="text-xs px-3 py-1.5 rounded-full transition-colors" style={tabStyle(mode === "instagram")}>
          From Instagram
        </button>
        <button onClick={() => { setMode("paste"); reset(); }} className="text-xs px-3 py-1.5 rounded-full transition-colors" style={tabStyle(mode === "paste")}>
          Paste
        </button>
      </div>

      {mode === "instagram" ? (
        <InboxInput clusterId={clusterId} onClusterChange={setClusterId} onLoad={handleLoadComments} loading={loading} />
      ) : (
        <TriageBatchInput text={text} onTextChange={setText} clusterId={clusterId} onClusterChange={setClusterId} onSubmit={handlePasteSubmit} loading={loading} />
      )}

      {reconnect && (
        <div
          className="rounded-xl border p-4 mt-3"
          style={{ borderColor: "var(--color-ql-accent)", background: "color-mix(in oklch, var(--color-ql-accent) 6%, transparent)" }}
        >
          <p className="text-xs mb-2" style={{ color: "var(--color-ql-dark)" }}>
            Your Instagram connection doesn&apos;t have comment access yet. Add the
            <span className="font-medium"> instagram_business_manage_comments </span>
            permission in your Meta app, then reconnect to grant it.
          </p>
          <a
            href={connectInstagramUrl()}
            className="inline-block text-[11px] font-medium px-3 py-1.5 rounded-lg"
            style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
          >
            Reconnect Instagram
          </a>
        </div>
      )}

      {error && (
        <p className="text-xs mt-3" style={{ color: "var(--color-verdict-failed)" }}>
          {error}
        </p>
      )}

      {result && (
        <TriageResultsList
          results={result.results}
          comments={comments}
          onSaveReply={handleSaveReply}
          onSend={mode === "instagram" ? handleSend : undefined}
        />
      )}
    </motion.div>
  );
}
