import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

// Where the FastAPI backend runs during development.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/**
 * Two modes:
 * - `npm run dev`: a dev server on :3000 that forwards /api/* to FastAPI, so the browser
 *   sees one origin and the workspace cookie just works.
 * - `npm run build`: a static export (plain HTML/CSS/JS in `out/`) that FastAPI serves.
 *   Static exports can't use rewrites, so they are only configured for development.
 */
export default function config(phase: string): NextConfig {
  if (phase === PHASE_DEVELOPMENT_SERVER) {
    return {
      async rewrites() {
        return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
      },
    };
  }
  return { output: "export" };
}
