import type { Metadata } from "next";
import { Instrument_Serif, Work_Sans } from "next/font/google";
import "./globals.css";
import Providers from "@/components/layout/Providers";

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument-serif",
  display: "swap",
});

const workSans = Work_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-work-sans",
  display: "swap",
});

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
    <html lang="en" className={`h-full ${instrumentSerif.variable} ${workSans.variable}`}>
      <body className="h-full" style={{ background: "var(--color-ql-bg)" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
