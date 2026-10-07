import { citationLabel } from "./citations";
import type { QueryResult } from "./types";

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;   // e.g. the page isn't focused, or the browser blocks clipboard access
  }
}

/** The answer plus a numbered source list, ready to paste anywhere. */
export function answerWithSources(result: QueryResult): string {
  const sources = result.citations.map((c) => `[${c.n}] ${citationLabel(c, 80)}${c.source_uri ? ` — ${c.source_uri}` : ""}`);
  return sources.length ? `${result.answer}\n\nSources:\n${sources.join("\n")}` : result.answer;
}

/** A Markdown file listing every citation with its full excerpt. */
export function citationsMarkdown(question: string, result: QueryResult): string {
  const lines = [`# SourceTrail citations`, "", `**Question:** ${question}`, "", `**Answer:** ${result.answer}`, "", "## Sources", ""];
  for (const c of result.citations) {
    lines.push(`### [${c.n}] ${citationLabel(c, 120)}`);
    if (c.source_uri) lines.push(`Source: ${c.source_uri}`);
    lines.push(`Chunk: \`${c.chunk_id}\``, "", ...c.snippet.split("\n").map((l) => `> ${l}`), "");
  }
  return lines.join("\n");
}

/** Start a browser download of `text` as a file — no server involved. */
export function downloadText(filename: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);   // free the memory
}
