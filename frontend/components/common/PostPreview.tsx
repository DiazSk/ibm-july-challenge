"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Shows the actual reel/post from its Instagram shortcode via Instagram's embed
 * iframe. No stored media — the shortcode alone identifies the post, and IG
 * serves it. The iframe mounts only when opened, so a list of posts doesn't
 * load N iframes at once. The "Open on Instagram" link is always present as a
 * fallback if the embed is blocked (private/deleted post, or offline).
 *
 * Height auto-sizes: the embed posts its real content height to the parent
 * (`{type:"MEASURE", details:{height}}`), which we listen for. A fixed height
 * clipped tall posts — a portrait photo plus header and caption needs ~900px,
 * far more than any sensible default. `height` is only the fallback used until
 * (or unless) that message arrives.
 */
export default function PostPreview({
  shortcode,
  defaultOpen = false,
  height = 480,
}: {
  shortcode: string;
  defaultOpen?: boolean;
  height?: number;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [measured, setMeasured] = useState<number | null>(null);
  const frameRef = useRef<HTMLIFrameElement | null>(null);

  useEffect(() => {
    if (!open) return;

    function onMessage(e: MessageEvent) {
      // Only trust Instagram, and only this component's own iframe — several
      // previews can be open at once, each needing its own height.
      if (!e.origin.endsWith("instagram.com")) return;
      if (!frameRef.current || e.source !== frameRef.current.contentWindow) return;

      let data: unknown = e.data;
      if (typeof data === "string") {
        try {
          data = JSON.parse(data);
        } catch {
          return;
        }
      }
      const d = data as { type?: string; details?: { height?: number } };
      const h = d?.type === "MEASURE" ? d.details?.height : undefined;
      if (typeof h === "number" && h > 0) setMeasured(Math.ceil(h));
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [open]);

  if (!shortcode) return null;

  const permalink = `https://www.instagram.com/p/${shortcode}/`;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-[11px] font-medium transition-colors"
          style={{ color: "var(--color-ql-accent)" }}
        >
          {open ? "Hide preview" : "▶ View post"}
        </button>
        <a
          href={permalink}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] transition-colors"
          style={{ color: "var(--color-ql-muted)" }}
        >
          Open on Instagram ↗
        </a>
      </div>

      {open && (
        <iframe
          ref={frameRef}
          src={`${permalink}embed`}
          title={`Instagram post ${shortcode}`}
          loading="lazy"
          scrolling="no"
          className="w-full rounded-lg border"
          style={{
            height: measured ?? height,
            borderColor: "var(--color-ql-border)",
            background: "var(--color-ql-card)",
          }}
        />
      )}
    </div>
  );
}
