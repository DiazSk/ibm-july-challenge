"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { voiceRefineCaption } from "@/lib/api";
import type { VoiceRefineResult } from "@/lib/types";

interface Props {
  clusterId: number;
  onCaption: (caption: string) => void;
}

type Phase = "idle" | "listening" | "processing" | "result" | "error" | "unsupported";

// Tiny SVG icons — inline so no icon library needed
function MicIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function StopIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}

function SpeakerIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    </svg>
  );
}

export default function VoiceCapture({ clusterId, onCaption }: Props) {
  const [phase, setPhase]       = useState<Phase>("idle");
  const [interim, setInterim]   = useState("");
  const [transcript, setTranscript] = useState("");
  const [result, setResult]     = useState<VoiceRefineResult | null>(null);
  const [error, setError]       = useState("");
  const [ttsPlayed, setTtsPlayed] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const srRef = useRef<{ stop: () => void } | null>(null);

  // Check browser support once on mount
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SR = w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
    if (!SR) setPhase("unsupported");
  }, []);

  const stopListening = useCallback(() => {
    srRef.current?.stop();
  }, []);

  const startListening = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SR = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!SR) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sr: any = new SR();
    sr.continuous     = false;
    sr.interimResults = true;
    sr.lang           = "en-US";
    srRef.current     = sr;

    let finalBuffer = "";

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    sr.onresult = (event: any) => {
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalBuffer += event.results[i][0].transcript + " ";
        } else {
          interimText += event.results[i][0].transcript;
        }
      }
      setInterim(interimText);
      if (finalBuffer) setTranscript(finalBuffer);
    };

    sr.onend = () => {
      setInterim("");
      const captured = finalBuffer.trim();
      if (captured) {
        setTranscript(captured);
        submitToGranite(captured);
      } else {
        setPhase("idle");
      }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    sr.onerror = (event: any) => {
      setError(`Speech recognition error: ${event.error}`);
      setPhase("error");
    };

    setPhase("listening");
    setTranscript("");
    setInterim("");
    setResult(null);
    setTtsPlayed(false);
    sr.start();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function submitToGranite(text: string) {
    setPhase("processing");
    try {
      const res = await voiceRefineCaption(text, clusterId);
      setResult(res);
      setPhase("result");
      // Auto-play TTS
      if (typeof window !== "undefined" && window.speechSynthesis) {
        const utt = new SpeechSynthesisUtterance(res.refined_caption);
        utt.rate  = 0.92;
        utt.pitch = 1;
        window.speechSynthesis.speak(utt);
        setTtsPlayed(true);
      }
    } catch {
      setError("Granite couldn't refine the caption. Try again.");
      setPhase("error");
    }
  }

  function handleReplay() {
    if (!result) return;
    window.speechSynthesis?.cancel();
    const utt = new SpeechSynthesisUtterance(result.refined_caption);
    utt.rate  = 0.92;
    utt.pitch = 1;
    window.speechSynthesis.speak(utt);
  }

  function handleUseCaption() {
    if (result) {
      onCaption(result.refined_caption);
      setPhase("idle");
      setResult(null);
      setTranscript("");
    }
  }

  function handleReset() {
    window.speechSynthesis?.cancel();
    setPhase("idle");
    setResult(null);
    setTranscript("");
    setInterim("");
    setError("");
    setTtsPlayed(false);
  }

  if (phase === "unsupported") return null;

  const isListening   = phase === "listening";
  const isProcessing  = phase === "processing";
  const showResult    = phase === "result" && result !== null;

  return (
    <div
      className="rounded-xl border mb-6 p-5"
      style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p
            className="text-[10px] uppercase tracking-[0.12em] font-medium"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Granite #12 · Voice Caption
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-ql-dark)" }}>
            Speak a caption idea — Granite refines it in your brand voice
          </p>
        </div>

        {/* Mic button */}
        {!showResult && phase !== "processing" && (
          <button
            onClick={isListening ? stopListening : startListening}
            aria-label={isListening ? "Stop recording" : "Start recording"}
            className="relative flex items-center justify-center rounded-full transition-colors"
            style={{
              width: 48,
              height: 48,
              background: isListening ? "var(--color-ql-dark)" : "var(--color-ql-accent)",
              color: "var(--color-ql-bg)",
              flexShrink: 0,
            }}
          >
            {isListening ? <StopIcon size={16} /> : <MicIcon size={18} />}
            {isListening && (
              <>
                <span
                  className="absolute inset-0 rounded-full animate-ping"
                  style={{ background: "var(--color-ql-dark)", opacity: 0.25 }}
                />
              </>
            )}
          </button>
        )}
      </div>

      {/* Listening state */}
      {isListening && (
        <div
          className="rounded-lg px-3 py-2.5 min-h-[40px]"
          style={{ background: "var(--color-ql-gap)" }}
        >
          <p className="text-xs leading-relaxed" style={{ color: "var(--color-ql-dark)" }}>
            {transcript || interim || (
              <span className="animate-pulse" style={{ color: "var(--color-ql-muted)" }}>
                Listening…
              </span>
            )}
            {interim && !transcript && (
              <span style={{ color: "var(--color-ql-muted)" }}> {interim}</span>
            )}
          </p>
        </div>
      )}

      {/* Processing */}
      {isProcessing && (
        <div className="flex items-center gap-2">
          <span
            className="text-xs animate-pulse"
            style={{ color: "var(--color-ql-muted)" }}
          >
            Granite is refining your caption…
          </span>
        </div>
      )}

      {/* Result */}
      {showResult && (
        <div className="flex flex-col gap-3">
          {/* Spoken idea */}
          {transcript && (
            <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
              You said: &ldquo;{transcript}&rdquo;
            </p>
          )}

          {/* Refined caption */}
          <div
            className="rounded-lg px-4 py-3"
            style={{ background: "var(--color-ql-gap)" }}
          >
            <p
              className="text-sm leading-relaxed"
              style={{ fontFamily: "var(--font-display)", color: "var(--color-ql-dark)" }}
            >
              {result!.refined_caption}
            </p>
          </div>

          {/* Reasoning */}
          <p className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
            {result!.reasoning}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={handleUseCaption}
              className="text-xs px-4 py-2 rounded-lg font-medium transition-opacity hover:opacity-80"
              style={{
                background: "var(--color-ql-dark)",
                color: "var(--color-ql-bg)",
              }}
            >
              Use This Caption
            </button>

            {ttsPlayed && (
              <button
                onClick={handleReplay}
                className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg transition-opacity hover:opacity-70"
                style={{
                  border: "1px solid var(--color-ql-border)",
                  color: "var(--color-ql-muted)",
                }}
              >
                <SpeakerIcon size={12} />
                Replay
              </button>
            )}

            <button
              onClick={handleReset}
              className="text-xs px-3 py-2 rounded-lg transition-opacity hover:opacity-70"
              style={{
                border: "1px solid var(--color-ql-border)",
                color: "var(--color-ql-muted)",
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {phase === "error" && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs" style={{ color: "var(--color-verdict-failed)" }}>
            {error}
          </p>
          <button
            onClick={handleReset}
            className="text-xs px-3 py-1.5 rounded-lg"
            style={{
              border: "1px solid var(--color-ql-border)",
              color: "var(--color-ql-muted)",
            }}
          >
            Try Again
          </button>
        </div>
      )}

      {/* Idle hint */}
      {phase === "idle" && (
        <p className="text-[11px]" style={{ color: "var(--color-ql-muted)" }}>
          Chrome only · your audio never leaves this machine
        </p>
      )}
    </div>
  );
}
