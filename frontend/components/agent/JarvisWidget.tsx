"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { agentChat, clearAgentSession, saveAsset } from "@/lib/api";
import type { ActionResult, InspirationIdea } from "@/lib/types";

// ── Types ─────────────────────────────────────────────────────────────────────

type Phase = "idle" | "listening" | "thinking" | "speaking" | "ready";

interface LocalMessage {
  id         : string;
  role       : "user" | "assistant";
  content    : string;
  actionResult?: ActionResult | null;
}

// ── Inline SVG icons ──────────────────────────────────────────────────────────

function MicIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  );
}

function StopIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2"/>
    </svg>
  );
}

function CloseIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

function TrashIcon({ size = 13 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6l-1 14H6L5 6"/>
      <path d="M10 11v6M14 11v6"/>
      <path d="M9 6V4h6v2"/>
    </svg>
  );
}

// ── Action cards ──────────────────────────────────────────────────────────────

function CaptionCard({
  data, onUse, onSave,
}: {
  data       : ActionResult["data"];
  onUse      : (caption: string) => void;
  onSave     : (caption: string) => void;
}) {
  const caption = data.caption ?? "";
  return (
    <div className="rounded-xl border mt-2 p-3 flex flex-col gap-2"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}>
      <p className="text-xs leading-relaxed"
        style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
        &ldquo;{caption}&rdquo;
      </p>
      <div className="flex gap-2">
        <button onClick={() => onUse(caption)}
          className="text-[11px] px-3 py-1.5 rounded-lg font-medium hover:opacity-80 transition-opacity"
          style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}>
          Use in Caption Brief
        </button>
        <button onClick={() => onSave(caption)}
          className="text-[11px] px-3 py-1.5 rounded-lg hover:opacity-70 transition-opacity"
          style={{ border: "1px solid var(--color-ql-border)", color: "var(--color-ql-muted)" }}>
          Save
        </button>
      </div>
    </div>
  );
}

function InspirationCards({ data }: { data: ActionResult["data"] }) {
  const ideas = (data.ideas ?? []) as InspirationIdea[];
  return (
    <div className="flex flex-col gap-2 mt-2">
      {ideas.map((idea, i) => (
        <div key={i} className="rounded-xl border p-3"
          style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] uppercase tracking-[0.1em] font-medium px-2 py-0.5 rounded"
              style={{ background: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}>
              {idea.angle}
            </span>
            <span className="text-[11px] font-medium"
              style={{ color: "var(--color-ql-dark)" }}>
              {idea.title}
            </span>
          </div>
          <p className="text-[11px] leading-relaxed mb-1"
            style={{ color: "var(--color-ql-dark)" }}>
            {idea.what_to_post}
          </p>
          {idea.caption_hook && (
            <p className="text-[11px] italic"
              style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-muted)" }}>
              &ldquo;{idea.caption_hook}&rdquo;
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function PostMortemCard({ data }: { data: ActionResult["data"] }) {
  const verdict = data.verdict_label ?? "";
  const verdictColor = verdict === "Succeeded"
    ? "var(--color-verdict-succeeded)"
    : verdict === "Failed"
    ? "var(--color-verdict-failed)"
    : "var(--color-verdict-underperformed)";

  return (
    <div className="rounded-xl border mt-2 p-3 flex flex-col gap-1.5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-gap)" }}>
      {verdict && (
        <span className="text-[11px] font-medium uppercase tracking-wider"
          style={{ color: verdictColor }}>
          {verdict}
        </span>
      )}
      {data.diagnosis && (
        <p className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
          {String(data.diagnosis)}
        </p>
      )}
      {data.change_next_time && (
        <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
          Next time: {String(data.change_next_time)}
        </p>
      )}
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────

function MessageBubble({
  msg, onUseCaption, onSaveCaption,
}: {
  msg          : LocalMessage;
  onUseCaption : (c: string) => void;
  onSaveCaption: (c: string) => void;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      <div
        className="max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed"
        style={{
          background: isUser
            ? "var(--color-ql-dark)"
            : "var(--color-ql-card)",
          color: isUser ? "var(--color-ql-bg)" : "var(--color-ql-dark)",
          border: isUser ? "none" : "1px solid var(--color-ql-border)",
          fontFamily: isUser ? "inherit" : "var(--font-display)",
        }}
      >
        {msg.content}
      </div>

      {/* Action cards */}
      {msg.actionResult?.type === "caption" && (
        <CaptionCard
          data={msg.actionResult.data}
          onUse={onUseCaption}
          onSave={onSaveCaption}
        />
      )}
      {msg.actionResult?.type === "inspiration" && (
        <InspirationCards data={msg.actionResult.data} />
      )}
      {msg.actionResult?.type === "post_mortem" && (
        <PostMortemCard data={msg.actionResult.data} />
      )}
    </div>
  );
}

// ── Main widget ───────────────────────────────────────────────────────────────

export default function JarvisWidget() {
  const router      = useRouter();
  const qc          = useQueryClient();

  const [isOpen,    setIsOpen]    = useState(false);
  const [phase,     setPhase]     = useState<Phase>("idle");
  const [messages,  setMessages]  = useState<LocalMessage[]>([]);
  const [supported, setSupported] = useState(true);

  const bottomRef        = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);
  const currentAudioRef  = useRef<HTMLAudioElement | null>(null);

  const sessionId   = useState(() => {
    if (typeof window === "undefined") return crypto.randomUUID();
    const k = "jarvis_session_id";
    const existing = sessionStorage.getItem(k);
    if (existing) return existing;
    const id = crypto.randomUUID();
    sessionStorage.setItem(k, id);
    return id;
  })[0];

  // Check MediaRecorder support
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaDevices" in navigator)) {
      setSupported(false);
    }
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, phase]);

  // ── History helpers ─────────────────────────────────────────────────────
  function historyForApi() {
    return messages.map(m => ({ role: m.role, content: m.content }));
  }

  function addMessage(msg: Omit<LocalMessage, "id">) {
    setMessages(prev => [...prev, { ...msg, id: crypto.randomUUID() }]);
  }

  // ── Send to JARVIS ──────────────────────────────────────────────────────
  async function sendToJarvis(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    addMessage({ role: "user", content: trimmed });
    setPhase("thinking");

    try {
      const res = await agentChat(trimmed, sessionId, historyForApi());

      // Fetch audio before showing text so both arrive simultaneously.
      setPhase("speaking");
      currentAudioRef.current?.pause();

      let audio: HTMLAudioElement | null = null;
      let audioUrl: string | null = null;
      try {
        const audioRes = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/voice/synthesize`,
          {
            method : "POST",
            headers: { "Content-Type": "application/json" },
            body   : JSON.stringify({ text: res.response }),
          }
        );
        if (!audioRes.ok) throw new Error(`TTS ${audioRes.status}`);
        const audioBlob = await audioRes.blob();
        audioUrl = URL.createObjectURL(audioBlob);
        audio = new Audio(audioUrl);
        currentAudioRef.current = audio;
      } catch {
        // TTS failed — text still shows, phase resets below
      }

      // Show text and start playback at the same moment
      addMessage({
        role        : "assistant",
        content     : res.response,
        actionResult: res.action_result ?? null,
      });

      if (audio && audioUrl) {
        audio.onended = () => { setPhase("ready"); URL.revokeObjectURL(audioUrl!); };
        try {
          await audio.play();
        } catch {
          setPhase("ready");
        }
      } else {
        setPhase("ready");
      }
    } catch {
      addMessage({ role: "assistant", content: "Something went wrong. Is the server running?" });
      setPhase("ready");
    }
  }

  // ── Push-to-talk (MediaRecorder) ────────────────────────────────────────
  const handleRecordingStop = useCallback(async () => {
    setPhase("thinking");
    const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    if (blob.size < 500) { setPhase("ready"); return; }
    try {
      const fd = new FormData();
      fd.append("audio", blob, "recording.webm");
      const data = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/voice/transcribe`,
        { method: "POST", body: fd }
      ).then(r => r.json());
      if (!data.transcript?.trim()) { setPhase("ready"); return; }
      await sendToJarvis(data.transcript);
    } catch {
      addMessage({ role: "assistant", content: "Transcription failed — try again." });
      setPhase("ready");
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
  }, []);

  const startListening = useCallback(async () => {
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = handleRecordingStop;
      mediaRecorderRef.current = recorder;
      recorder.start();
      setPhase("listening");
    } catch {
      addMessage({ role: "assistant", content: "Mic access denied — check browser permissions." });
      setPhase("ready");
    }
  }, [handleRecordingStop]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Caption injection ───────────────────────────────────────────────────
  function handleUseCaption(caption: string) {
    localStorage.setItem("ss_create_product", caption);
    router.push("/app/create");
    setIsOpen(false);
  }

  async function handleSaveCaption(caption: string) {
    try {
      await saveAsset({ asset_type: "caption", content: caption, source_tab: "jarvis" });
      qc.invalidateQueries({ queryKey: ["workbench"] });
    } catch { /* silent */ }
  }

  // ── Clear conversation ──────────────────────────────────────────────────
  async function handleClear() {
    currentAudioRef.current?.pause();
    setMessages([]);
    setPhase("idle");
    try { await clearAgentSession(sessionId); } catch { /* silent */ }
  }

  // ── Text fallback (non-Chrome) ──────────────────────────────────────────
  const [textInput, setTextInput] = useState("");

  function handleTextSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!textInput.trim()) return;
    sendToJarvis(textInput);
    setTextInput("");
  }

  const isListening  = phase === "listening";
  const isThinking   = phase === "thinking";

  // ── Render: collapsed ───────────────────────────────────────────────────
  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={() => setIsOpen(true)}
          title="Open JARVIS"
          className="relative flex items-center justify-center rounded-full shadow-xl transition-transform hover:scale-105"
          style={{
            width    : 60,
            height   : 60,
            background: "var(--color-ql-dark)",
            color    : "var(--color-ql-bg)",
          }}
        >
          <MicIcon size={22} />
          {messages.length > 0 && (
            <span
              className="absolute -top-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold"
              style={{ background: "var(--color-ql-accent)", color: "var(--color-ql-bg)" }}
            >
              {messages.filter(m => m.role === "assistant").length}
            </span>
          )}
        </button>
      </div>
    );
  }

  // ── Render: expanded panel ──────────────────────────────────────────────
  return (
    <div className="fixed bottom-6 right-6 z-40 flex flex-col" style={{ width: 380 }}>
      {/* Panel */}
      <div
        className="flex flex-col rounded-2xl border shadow-2xl overflow-hidden"
        style={{
          height          : 540,
          borderColor     : "var(--color-ql-border)",
          background      : "var(--color-ql-card)",
        }}
      >
        {/* Header */}
        <div
          className="shrink-0 flex items-center justify-between px-4 py-3 border-b"
          style={{ borderColor: "var(--color-ql-border)" }}
        >
          <div>
            <p className="text-sm font-medium" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
              JARVIS
            </p>
            <p className="text-[10px] uppercase tracking-[0.12em]" style={{ color: "var(--color-ql-muted)" }}>
              Granite #13 · StyleSync Agent
            </p>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleClear}
                title="Clear conversation"
                className="p-1.5 rounded-lg hover:opacity-70 transition-opacity"
                style={{ color: "var(--color-ql-muted)" }}
              >
                <TrashIcon size={13} />
              </button>
            )}
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-lg hover:opacity-70 transition-opacity"
              style={{ color: "var(--color-ql-muted)" }}
            >
              <CloseIcon size={14} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center">
              <p className="text-sm" style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}>
                Ask me anything about your brand.
              </p>
              <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
                &ldquo;What&apos;s my best performing cluster?&rdquo;<br/>
                &ldquo;Write a caption for fresh bomboloni&rdquo;<br/>
                &ldquo;Research trending bakery content&rdquo;
              </p>
            </div>
          )}

          {messages.map(msg => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              onUseCaption={handleUseCaption}
              onSaveCaption={handleSaveCaption}
            />
          ))}

          {/* Recording indicator */}
          {isListening && (
            <div className="flex items-start gap-2">
              <div className="max-w-[85%] ml-auto rounded-2xl px-3.5 py-2.5 text-[12px]"
                style={{ background: "var(--color-ql-gap)", color: "var(--color-ql-muted)" }}>
                <span className="animate-pulse">Recording…</span>
              </div>
            </div>
          )}

          {/* Thinking indicator */}
          {isThinking && (
            <div className="flex items-center gap-1.5 px-1">
              {[0, 1, 2].map(i => (
                <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
                  style={{
                    background    : "var(--color-ql-muted)",
                    animationDelay: `${i * 0.15}s`,
                  }}
                />
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div
          className="shrink-0 border-t px-4 py-3"
          style={{ borderColor: "var(--color-ql-border)" }}
        >
          {supported ? (
            <div className="flex items-center gap-3">
              <p className="flex-1 text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
                {isListening
                  ? "Listening… click to stop"
                  : isThinking
                  ? "Thinking…"
                  : phase === "speaking"
                  ? "Speaking…"
                  : "Click mic to speak"}
              </p>
              <button
                onClick={isListening ? stopListening : startListening}
                disabled={isThinking || phase === "speaking"}
                className="relative flex items-center justify-center rounded-full transition-colors disabled:opacity-40"
                style={{
                  width     : 44,
                  height    : 44,
                  background: isListening ? "var(--color-verdict-failed)" : "var(--color-ql-dark)",
                  color     : "var(--color-ql-bg)",
                  flexShrink: 0,
                }}
              >
                {isListening ? <StopIcon size={14} /> : <MicIcon size={18} />}
                {isListening && (
                  <span className="absolute inset-0 rounded-full animate-ping"
                    style={{ background: "var(--color-verdict-failed)", opacity: 0.2 }} />
                )}
              </button>
            </div>
          ) : (
            /* Text fallback for non-Chrome browsers */
            <form onSubmit={handleTextSubmit} className="flex gap-2">
              <input
                type="text"
                value={textInput}
                onChange={e => setTextInput(e.target.value)}
                placeholder="Type a message…"
                className="flex-1 text-xs rounded-lg px-3 py-2 outline-none"
                style={{
                  background  : "var(--color-ql-gap)",
                  border      : "1px solid var(--color-ql-border)",
                  color       : "var(--color-ql-dark)",
                }}
              />
              <button type="submit"
                className="px-3 py-2 rounded-lg text-xs font-medium"
                style={{ background: "var(--color-ql-dark)", color: "var(--color-ql-bg)" }}>
                Send
              </button>
            </form>
          )}

        </div>
      </div>
    </div>
  );
}
