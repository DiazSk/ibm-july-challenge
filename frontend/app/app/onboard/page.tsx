"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { startOnboard, uploadExport, getOnboardStatus } from "@/lib/api";
import type { OnboardStatus } from "@/lib/types";

type Screen = "choice" | "progress";

const inputClass =
  "w-full text-sm rounded-lg border px-3 py-2.5 outline-none transition-colors";
const inputStyle = {
  borderColor: "var(--color-ql-border)",
  color: "var(--color-ql-text)",
  background: "var(--color-ql-bg)",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label
        className="block text-[11px] font-medium uppercase tracking-[0.12em] mb-1.5"
        style={{ color: "var(--color-ql-muted)" }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

export default function OnboardPage() {
  const router = useRouter();
  const [screen, setScreen] = useState<Screen>("choice");

  // Handle form state
  const [handle, setHandle] = useState("");
  const [brandName, setBrandName] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Progress state
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<OnboardStatus>({
    status: "queued",
    progress: 0,
    message: "Starting...",
  });
  const [submitError, setSubmitError] = useState("");
  const [loading, setLoading] = useState(false);

  // Poll for job status
  useEffect(() => {
    if (!jobId || screen !== "progress") return;
    if (status.status === "done" || status.status === "error") return;

    const id = setInterval(async () => {
      try {
        const s = await getOnboardStatus(jobId);
        setStatus(s);
        if (s.status === "done") {
          clearInterval(id);
          setTimeout(() => router.push("/create"), 800);
        } else if (s.status === "error") {
          clearInterval(id);
        }
      } catch {
        // network hiccup — keep polling
      }
    }, 3000);

    return () => clearInterval(id);
  }, [jobId, screen, status.status, router]);

  async function handleStartHandle() {
    const h = handle.trim().lstrip_at();
    if (!h) { setSubmitError("Please enter your Instagram username."); return; }
    setSubmitError("");
    setLoading(true);
    try {
      const name = brandName.trim() || h.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      const { job_id } = await startOnboard(h, name);
      setJobId(job_id);
      setStatus({ status: "running", progress: 5, message: "Connecting to Instagram..." });
      setScreen("progress");
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : "Failed to start. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartUpload() {
    if (!uploadFile) { setSubmitError("Please select your Instagram data export ZIP."); return; }
    const h = handle.trim().lstrip_at() || "my_account";
    setSubmitError("");
    setLoading(true);
    try {
      const name = brandName.trim() || h.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      const { job_id } = await uploadExport(uploadFile, h, name);
      setJobId(job_id);
      setStatus({ status: "running", progress: 5, message: "Reading your export..." });
      setScreen("progress");
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : "Upload failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith(".zip")) setUploadFile(file);
    else setSubmitError("Please drop a .zip file.");
  }, []);

  if (screen === "progress") {
    return (
      <FullScreen>
        <div className="w-full max-w-md mx-auto">
          <p
            className="text-[10px] font-medium uppercase tracking-[0.18em] mb-2"
            style={{ color: "var(--color-ql-accent)" }}
          >
            StyleSync
          </p>
          <h1
            className="text-2xl mb-1"
            style={{ fontFamily: "Georgia, serif", color: "var(--color-ql-dark)" }}
          >
            {status.status === "done"
              ? "Brand voice ready"
              : status.status === "error"
              ? "Something went wrong"
              : `Analyzing ${status.handle ?? "your account"}`}
          </h1>

          {status.status === "error" ? (
            <div className="mt-6">
              <p
                className="text-sm leading-relaxed mb-4"
                style={{ color: "var(--color-ql-muted)" }}
              >
                {status.message}
              </p>
              <p className="text-sm mb-5" style={{ color: "var(--color-ql-muted)" }}>
                Try uploading your Instagram data export instead — it works for any account.
              </p>
              <button
                onClick={() => { setScreen("choice"); setShowUpload(true); setSubmitError(""); }}
                className="px-4 py-2.5 text-sm rounded-lg border transition-colors"
                style={{ borderColor: "var(--color-ql-border)", color: "var(--color-ql-muted)" }}
              >
                Use data export instead
              </button>
            </div>
          ) : (
            <>
              {/* Progress bar */}
              <div
                className="mt-8 h-1.5 rounded-full overflow-hidden"
                style={{ background: "var(--color-ql-border)" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${status.progress}%`,
                    background:
                      status.status === "done"
                        ? "var(--color-ql-accent)"
                        : "var(--color-ql-dark)",
                  }}
                />
              </div>

              <p
                className="mt-3 text-sm"
                style={{ color: "var(--color-ql-muted)" }}
              >
                {status.message}
              </p>

              <p
                className="mt-6 text-[11px]"
                style={{ color: "var(--color-ql-muted)" }}
              >
                {status.status === "done"
                  ? "Redirecting you now..."
                  : "This usually takes about 10 minutes. You can leave this tab open."}
              </p>

              <p
                className="mt-8 text-[10px] uppercase tracking-[0.12em]"
                style={{ color: "var(--color-ql-muted)", opacity: 0.5 }}
              >
                Powered by IBM Granite 3.1
              </p>
            </>
          )}
        </div>
      </FullScreen>
    );
  }

  // choice screen
  return (
    <FullScreen>
      <div className="w-full max-w-md mx-auto">
        <p
          className="text-[10px] font-medium uppercase tracking-[0.18em] mb-2"
          style={{ color: "var(--color-ql-accent)" }}
        >
          StyleSync
        </p>
        <h1
          className="text-2xl mb-1"
          style={{ fontFamily: "Georgia, serif", color: "var(--color-ql-dark)" }}
        >
          AI Art Direction
        </h1>
        <p className="text-sm mb-8" style={{ color: "var(--color-ql-muted)" }}>
          For Instagram creators who want their captions, scripts, and strategy
          to feel unmistakably them.
        </p>

        {/* Demo account button */}
        <button
          onClick={() => router.push("/create")}
          className="w-full py-3.5 text-sm font-medium rounded-xl transition-colors mb-6"
          style={{ background: "var(--color-ql-dark)", color: "#fff" }}
        >
          Use Demo Account (@hot_cakesbakes)
        </button>

        <div
          className="flex items-center gap-3 mb-6"
          style={{ color: "var(--color-ql-muted)" }}
        >
          <div className="flex-1 h-px" style={{ background: "var(--color-ql-border)" }} />
          <span className="text-[11px] uppercase tracking-[0.1em]">or analyze your own</span>
          <div className="flex-1 h-px" style={{ background: "var(--color-ql-border)" }} />
        </div>

        {/* Handle + brand name form */}
        <div
          className="rounded-xl border p-5 flex flex-col gap-4"
          style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
        >
          <div className="grid grid-cols-2 gap-3">
            <Field label="Instagram Username">
              <input
                type="text"
                value={handle}
                onChange={e => setHandle(e.target.value)}
                placeholder="hot_cakesbakes"
                className={inputClass}
                style={inputStyle}
                onFocus={e => (e.target.style.borderColor = "var(--color-ql-accent)")}
                onBlur={e => (e.target.style.borderColor = "var(--color-ql-border)")}
                onKeyDown={e => { if (e.key === "Enter") handleStartHandle(); }}
              />
            </Field>
            <Field label="Brand Name">
              <input
                type="text"
                value={brandName}
                onChange={e => setBrandName(e.target.value)}
                placeholder="HotCakes Bakes"
                className={inputClass}
                style={inputStyle}
                onFocus={e => (e.target.style.borderColor = "var(--color-ql-accent)")}
                onBlur={e => (e.target.style.borderColor = "var(--color-ql-border)")}
                onKeyDown={e => { if (e.key === "Enter") handleStartHandle(); }}
              />
            </Field>
          </div>

          {submitError && !showUpload && (
            <p className="text-[11px]" style={{ color: "#B45309" }}>{submitError}</p>
          )}

          <button
            onClick={handleStartHandle}
            disabled={loading || !handle.trim()}
            className="w-full py-3 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
            style={{ background: "var(--color-ql-accent)", color: "#fff" }}
          >
            {loading && !showUpload ? (
              <span className="animate-pulse">Starting analysis…</span>
            ) : (
              "Analyze My Brand →"
            )}
          </button>
        </div>

        {/* Data export toggle */}
        <button
          onClick={() => setShowUpload(v => !v)}
          className="mt-4 text-[11px] w-full text-center transition-colors"
          style={{ color: "var(--color-ql-muted)" }}
        >
          {showUpload ? "▲ Hide" : "▼ Having trouble? Use your Instagram data export instead"}
        </button>

        {showUpload && (
          <div
            className="mt-3 rounded-xl border p-5 flex flex-col gap-4"
            style={{ borderColor: "var(--color-ql-border)", background: "var(--color-ql-card)" }}
          >
            <p className="text-[11px] leading-relaxed" style={{ color: "var(--color-ql-muted)" }}>
              Go to Instagram → Settings → Your activity → Download your information →
              Select Posts &amp; Reels in JSON format. Upload the ZIP here when it arrives.
            </p>

            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              className="rounded-lg border-2 border-dashed p-6 text-center cursor-pointer transition-colors"
              style={{
                borderColor: dragOver ? "var(--color-ql-accent)" : "var(--color-ql-border)",
                background: dragOver ? "var(--color-ql-gap)" : "transparent",
              }}
            >
              <p className="text-sm" style={{ color: "var(--color-ql-muted)" }}>
                {uploadFile ? uploadFile.name : "Drop your instagram-export.zip here"}
              </p>
              <p className="text-[11px] mt-1" style={{ color: "var(--color-ql-muted)", opacity: 0.6 }}>
                or click to browse
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
              />
            </div>

            {submitError && showUpload && (
              <p className="text-[11px]" style={{ color: "#B45309" }}>{submitError}</p>
            )}

            <button
              onClick={handleStartUpload}
              disabled={loading || !uploadFile}
              className="w-full py-3 text-sm font-medium rounded-lg transition-colors disabled:opacity-40"
              style={{ background: "var(--color-ql-accent)", color: "#fff" }}
            >
              {loading && showUpload ? (
                <span className="animate-pulse">Uploading…</span>
              ) : (
                "Upload & Analyze"
              )}
            </button>
          </div>
        )}
      </div>
    </FullScreen>
  );
}

function FullScreen({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto flex flex-col items-center justify-center p-6"
      style={{ background: "var(--color-ql-bg)" }}
    >
      {children}
    </div>
  );
}

// TS helper — String.prototype doesn't have lstrip_at
declare global {
  interface String {
    lstrip_at(): string;
  }
}
String.prototype.lstrip_at = function () {
  return this.replace(/^@+/, "");
};
