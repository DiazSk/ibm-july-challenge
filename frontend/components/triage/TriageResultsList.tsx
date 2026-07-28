"use client";

import { useState } from "react";
import type { TriageResult, InboxComment } from "@/lib/types";

const CATEGORY_COLOR: Record<string, string> = {
  order_inquiry: "var(--color-ql-accent)",
  compliment: "var(--color-verdict-succeeded)",
  complaint: "var(--color-verdict-failed)",
  uncertain: "var(--color-verdict-underperformed)",
};

const CATEGORY_LABEL: Record<string, string> = {
  order_inquiry: "Order Inquiry",
  compliment: "Compliment",
  complaint: "Complaint",
  uncertain: "Uncertain",
};

function ResultCard({
  result,
  meta,
  onSave,
  onSend,
}: {
  result: TriageResult;
  meta?: InboxComment;
  onSave: (reply: string) => void;
  onSend?: (commentId: string, reply: string) => Promise<void>;
}) {
  const [reply, setReply] = useState(result.drafted_reply);
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);
  const [sendState, setSendState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [sendError, setSendError] = useState("");

  async function copy() {
    await navigator.clipboard.writeText(reply);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function save() {
    onSave(reply);
    setSaved(true);
  }

  async function send() {
    if (!onSend || !meta || !reply.trim()) return;
    setSendState("sending");
    setSendError("");
    try {
      await onSend(meta.id, reply);
      setSendState("sent");
    } catch (e) {
      setSendState("error");
      setSendError(e instanceof Error ? e.message : "Failed to send");
    }
  }

  return (
    <div
      className="rounded-xl border p-3.5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span
          className="text-[10px] uppercase tracking-[0.06em] font-medium px-2 py-0.5 rounded-full"
          style={{
            background: CATEGORY_COLOR[result.category] ?? "var(--color-ql-muted)",
            color: "var(--color-ql-bg)",
          }}
        >
          {CATEGORY_LABEL[result.category] ?? result.category}
        </span>
        {meta && (
          <>
            <span className="text-[11px] font-medium" style={{ color: "var(--color-ql-dark)" }}>
              @{meta.username}
            </span>
            {meta.media_permalink && (
              <a
                href={meta.media_permalink}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[10px]"
                style={{ color: "var(--color-ql-muted)" }}
              >
                on this post ↗
              </a>
            )}
          </>
        )}
      </div>
      <p
        className="text-xs italic leading-relaxed mb-2"
        style={{ color: "var(--color-ql-muted)" }}
      >
        &ldquo;{result.original_message}&rdquo;
      </p>
      <textarea
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        rows={3}
        disabled={sendState === "sent"}
        className="w-full text-xs rounded-lg px-2.5 py-2 outline-none resize-y disabled:opacity-60"
        style={{
          background: "var(--color-ql-gap)",
          border: "1px solid var(--color-ql-border)",
          color: "var(--color-ql-dark)",
        }}
      />
      <div className="flex gap-2 mt-2 flex-wrap">
        {onSend && meta && (
          <button
            onClick={send}
            disabled={sendState === "sending" || sendState === "sent" || !reply.trim()}
            className="text-[11px] px-3 py-1.5 rounded-lg font-medium transition-colors disabled:opacity-60"
            style={{
              background: sendState === "sent" ? "var(--color-verdict-succeeded)" : "var(--color-ql-accent)",
              color: "var(--color-ql-bg)",
            }}
          >
            {sendState === "sending" ? "Sending…" : sendState === "sent" ? "Replied ✓" : "Send reply"}
          </button>
        )}
        <button
          onClick={copy}
          className="text-[11px] px-3 py-1.5 rounded-lg border transition-colors"
          style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
        <button
          onClick={save}
          disabled={saved}
          className="text-[11px] px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-60"
          style={{
            borderColor: saved ? "var(--color-ql-accent)" : "var(--color-ql-border)",
            color: saved ? "var(--color-ql-accent)" : "var(--color-ql-muted)",
          }}
        >
          {saved ? "Saved to Workbench ✓" : "Save to Workbench"}
        </button>
      </div>
      {sendState === "error" && (
        <p className="text-[11px] mt-1.5" style={{ color: "var(--color-verdict-failed)" }}>
          {sendError}
        </p>
      )}
    </div>
  );
}

export default function TriageResultsList({
  results,
  comments,
  onSaveReply,
  onSend,
}: {
  results: TriageResult[];
  comments?: InboxComment[];
  onSaveReply: (result: TriageResult, reply: string) => void;
  onSend?: (commentId: string, reply: string) => Promise<void>;
}) {
  const [spamExpanded, setSpamExpanded] = useState(false);

  const active = results.filter((r) => r.category !== "spam");
  const spam = results.filter((r) => r.category === "spam");

  return (
    <div className="mt-6 flex flex-col gap-3">
      <p
        className="text-[11px] font-medium uppercase tracking-[0.12em]"
        style={{ color: "var(--color-ql-muted)" }}
      >
        {active.length} message{active.length === 1 ? "" : "s"} to review
      </p>

      {active.map((r) => (
        <ResultCard
          key={r.message_index}
          result={r}
          meta={comments?.[r.message_index]}
          onSave={(reply) => onSaveReply(r, reply)}
          onSend={onSend}
        />
      ))}

      {spam.length > 0 && (
        <div>
          <button
            onClick={() => setSpamExpanded((v) => !v)}
            className="text-[11px]"
            style={{ color: "var(--color-ql-muted)", textDecoration: "underline", textUnderlineOffset: "2px" }}
          >
            {spamExpanded ? "Hide" : "Show"} Spam ({spam.length})
          </button>
          {spamExpanded && (
            <div className="flex flex-col gap-2 mt-2">
              {spam.map((r) => (
                <p
                  key={r.message_index}
                  className="text-[11px] italic px-3 py-2 rounded-lg"
                  style={{ color: "var(--color-ql-muted)", background: "var(--color-ql-gap)" }}
                >
                  &ldquo;{r.original_message}&rdquo;
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
