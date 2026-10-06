import type { Metadata, Viewport } from "next";

// Self-hosted fonts: bundled with the site, so no request ever goes to Google.
import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource-variable/hanken-grotesk";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "SourceTrail — Chat with your documents",
  description:
    "Multi-source RAG: hybrid vector + keyword search, cross-encoder reranking and answers with verifiable citations.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#4f46e5",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-surface font-sans text-slate-800 antialiased selection:bg-indigo-100 selection:text-indigo-900">
        {children}
      </body>
    </html>
  );
}
