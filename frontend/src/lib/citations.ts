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

/** How well a passage fits the question, in words instead of a percentage.
 *  Only the reranker gives real 0–1 scores; the cut-offs follow our evaluation (answerable
 *  questions scored ≥ 0.69, unanswerable ≤ 0.13, and 0.3 is where we stop answering).
 *  Other modes only rank results, so they get no label. */
export type Match = { label: string; tone: string; hint: string };

export function matchStrength(source: Source | undefined): Match | null {
  if (!source || !("rerank" in source.ranks)) return null;
  const pct = Math.round(source.score * 100);
  const hint = `The AI judged this passage a ${pct}% fit for your question.`;
  if (source.score >= 0.7) return { label: "Strong match", tone: "border-emerald-200 bg-emerald-50 text-emerald-700", hint };
  if (source.score >= 0.3) return { label: "Good match", tone: "border-sky-200 bg-sky-50 text-sky-700", hint };
  return { label: "Weak match", tone: "border-amber-200 bg-amber-50 text-amber-800", hint };
}

const KINDS: Record<string, string> = {
  pdf: "PDF document",
  docx: "Word document",
  md: "Markdown file",
  txt: "Text file",
  csv: "Spreadsheet (CSV)",
  url: "Web page",
};

/** "Web page · developer.mozilla.org", "PDF document". */
export function documentKind(c: Pick<Citation, "source_type" | "source_uri">): string {
  const kind = KINDS[c.source_type] ?? "Document";
  if (c.source_type === "url" && c.source_uri) {
    try {
      return `${kind} · ${new URL(c.source_uri).hostname.replace(/^www\./, "")}`;
    } catch {
      /* not a URL after all */
    }
  }
  return kind;
}

/** Where in the document a passage is: "Page 12", a section heading, or just "Passage". */
export function passageLocation(c: Pick<Citation, "page" | "section" | "document_title">): string {
  if (c.page !== null) return c.section && c.section !== c.document_title ? `Page ${c.page} · ${c.section}` : `Page ${c.page}`;
  if (c.section && c.section !== c.document_title) return c.section;
  return "Passage";
}
