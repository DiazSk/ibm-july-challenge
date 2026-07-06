import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/layout/Providers";
import Sidebar from "@/components/layout/Sidebar";
import NavTabs from "@/components/layout/NavTabs";
import JarvisWidget from "@/components/agent/JarvisWidget";

export const metadata: Metadata = {
  title: "StyleSync — Creative Intelligence Platform",
  description: "AI-powered art direction assistant for HotCakes Bakes, powered by IBM Granite",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex" style={{ background: "var(--color-ql-bg)" }}>
        <Providers>
          <Sidebar />
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <header
              className="shrink-0"
              style={{ background: "var(--color-ql-card)" }}
            >
              <div
                className="px-6 pt-5 pb-0 border-b"
                style={{ borderColor: "var(--color-ql-border)" }}
              >
                <p
                  className="text-[10px] font-medium uppercase tracking-[0.18em] mb-1"
                  style={{ color: "var(--color-ql-accent)" }}
                >
                  StyleSync
                </p>
                <h1
                  className="text-xl mb-3"
                  style={{
                    fontFamily: "Georgia, serif",
                    color: "var(--color-ql-dark)",
                  }}
                >
                  Creative Intelligence Platform
                </h1>
                <NavTabs />
              </div>
            </header>
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
          <JarvisWidget />
        </Providers>
      </body>
    </html>
  );
}
