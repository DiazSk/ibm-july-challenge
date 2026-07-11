"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { checkHasProfile } from "@/lib/api";

export default function StudioIndex() {
  const router = useRouter();

  useEffect(() => {
    checkHasProfile()
      .then(({ has_profile }) => {
        router.replace(has_profile ? "/app/dashboard" : "/app/onboard");
      })
      .catch(() => {
        // If backend is unreachable, fall back to onboard so user sees a UI
        router.replace("/app/onboard");
      });
  }, [router]);

  return (
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{ background: "var(--color-ql-bg)" }}
    >
      <p
        className="text-[11px] uppercase tracking-[0.18em]"
        style={{ color: "var(--color-ql-muted)" }}
      >
        StyleSync
      </p>
    </div>
  );
}
