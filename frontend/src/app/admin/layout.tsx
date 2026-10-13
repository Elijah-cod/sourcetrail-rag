import type { Metadata } from "next";

// Kept out of search results here as well as by the server's X-Robots-Tag header.
export const metadata: Metadata = {
  title: "SourceTrail admin",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return children;
}
