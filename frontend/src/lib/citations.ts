import type { Citation, Source } from "./types";

// A colour per citation number, cycling, so [1] [2] [3] are easy to tell apart (as in the design).
const PALETTE = [
  { chip: "bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border-indigo-200", num: "text-indigo-600", dot: "bg-indigo-500" },
  { chip: "bg-violet-50 hover:bg-violet-100 text-violet-700 border-violet-200", num: "text-violet-600", dot: "bg-violet-500" },
  { chip: "bg-amber-50 hover:bg-amber-100 text-amber-800 border-amber-200", num: "text-amber-700", dot: "bg-amber-500" },
  { chip: "bg-teal-50 hover:bg-teal-100 text-teal-800 border-teal-200", num: "text-teal-700", dot: "bg-teal-500" },
  { chip: "bg-rose-50 hover:bg-rose-100 text-rose-700 border-rose-200", num: "text-rose-600", dot: "bg-rose-500" },
  { chip: "bg-sky-50 hover:bg-sky-100 text-sky-800 border-sky-200", num: "text-sky-700", dot: "bg-sky-500" },
];

export const citationColor = (n: number) => PALETTE[(n - 1) % PALETTE.length];

/** "Annual Report · p. 2" or "Guide · Installation" */
export function citationLabel(c: Pick<Citation, "document_title" | "page" | "section">, maxTitle = 28): string {
  const title = c.document_title.length > maxTitle ? `${c.document_title.slice(0, maxTitle - 1)}…` : c.document_title;
  if (c.page !== null) return `${title} · p. ${c.page}`;
  if (c.section && c.section !== c.document_title) return `${title} · ${c.section}`;
  return title;
}

/** The retrieved source behind a citation (it carries the relevance score and ranks). */
export const sourceFor = (c: Citation, sources: Source[]) =>
  sources.find((s) => s.chunk_id === c.chunk_id && s.document_id === c.document_id);

/** Reranker scores are probabilities (0–1); other modes only have rank-based scores. */
export function relevanceLabel(source: Source | undefined): string | null {
  if (!source) return null;
  if ("rerank" in source.ranks) return `${Math.round(source.score * 100)}% relevance`;
  return `rank #${Math.min(...Object.values(source.ranks))}`;
}
