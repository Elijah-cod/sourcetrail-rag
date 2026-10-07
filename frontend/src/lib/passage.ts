// Turn a stored passage into something pleasant to read.
// The stored text is shaped for search, not people: spreadsheet rows are saved as
// "column: value; column: value", PDFs keep their line wraps, web pages keep Markdown symbols.

import type { Citation } from "./types";

export type Field = { label: string; value: string };
export type Block =
  | { kind: "heading"; level: number; text: string }      // level 1 = biggest
  | { kind: "text"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "record"; title: string | null; details: Field[]; body: Field[] };

export function formatPassage(c: Pick<Citation, "snippet" | "source_type">): Block[] {
  if (c.source_type === "csv") return c.snippet.split("\n").filter((l) => l.trim()).map(parseRow);
  return paragraphs(c.source_type === "pdf" ? unwrapPdf(c.snippet) : stripMarkdown(c.snippet));
}

/** A one- or two-line summary for collapsed passages. */
export function previewText(blocks: Block[]): string {
  const titles = blocks.flatMap((b) => (b.kind === "record" && b.title ? [b.title] : []));
  if (titles.length) return titles.join(" · ");
  return blocks.map(blockText).join(" ");
}

/** All the readable text of a block, as one string. */
export function blockText(b: Block): string {
  if (b.kind === "record") return [b.title ?? "", ...b.body.map((f) => f.value)].join(" ");
  if (b.kind === "list") return b.items.join(" ");
  return b.text;
}

// ---------- spreadsheet rows ----------

const HIDDEN = /^(id|uuid|guid|key)$|[_ -](id|uuid|guid|key)$|^(doc|document|row)_?id$/i;   // internal identifiers
const TITLE = /^(title|name|subject|heading|question|topic)$/i;
const BODY = /content|text|body|description|answer|summary|details|notes?/i;
const GENERIC_BODY = /^(content|text|body)$/i;   // no label needed above the main text

function parseRow(line: string): Block {
  // Split on "; " only when it's followed by another "column: " so values containing ";" survive.
  const fields = line.split(/;\s(?=[^:;\n]{1,40}:\s)/).map((part) => {
    const at = part.indexOf(": ");
    return at > 0 ? { key: part.slice(0, at).trim(), value: part.slice(at + 2).trim() } : { key: "", value: part.trim() };
  });

  let title: string | null = null;
  const details: Field[] = [];
  const body: Field[] = [];
  for (const { key, value } of fields) {
    if (!value || HIDDEN.test(key)) continue;
    if (!title && TITLE.test(key)) title = value;
    else if (!key || BODY.test(key) || value.length > 60) body.push({ label: GENERIC_BODY.test(key) || !key ? "" : prettyLabel(key), value });
    else details.push({ label: prettyLabel(key), value: prettyValue(value) });
  }
  return { kind: "record", title, details, body };
}

/** "effective_date" -> "Effective date" */
function prettyLabel(key: string): string {
  const words = key.replace(/[_-]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").trim().toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** "2026-01-20" -> "20 Jan 2026"; everything else unchanged. */
function prettyValue(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

// ---------- prose ----------

/** PDFs indexed before structure detection kept the page's line wraps ("closest in meaning\nusing"):
 *  join those back up. Newer PDFs are stored as Markdown, whose list and heading lines are kept. */
const unwrapPdf = (text: string) => text.replace(/([^\n])\n(?!\n|#|[-*•] |\d+\. )/g, "$1 ");

/** Drop Markdown symbols people don't need to see: ``` fences, `backticks`, **stars**. */
const stripMarkdown = (text: string) =>
  text
    .replace(/^[ \t]*```.*$/gm, "")
    .replace(/`([^`\n]+)`/g, "$1")
    .replace(/\*\*([^*\n]+)\*\*/g, "$1")
    .replace(/[ \t]+$/gm, "");

const HEADING = /^(#{1,6})\s+(.+)$/;
const LIST_ITEM = /^\s*(?:[-*•]|(\d+)\.)\s+(.*)$/;

/** Light Markdown -> blocks: "## Title" headings, "- item" / "1. item" lists, and paragraphs. */
function paragraphs(text: string): Block[] {
  const blocks: Block[] = [];
  for (const chunk of text.split(/\n\s*\n/)) {
    let lines: string[] = [];
    const flush = () => {
      if (lines.length) blocks.push({ kind: "text", text: lines.join("\n") });
      lines = [];
    };
    for (const line of chunk.split("\n").filter((l) => l.trim())) {
      const heading = line.match(HEADING);
      const item = line.match(LIST_ITEM);
      const last = blocks.at(-1);
      if (heading) {
        flush();
        blocks.push({ kind: "heading", level: heading[1].length, text: heading[2].trim() });
      } else if (item) {
        flush();
        if (last?.kind === "list" && last.ordered === Boolean(item[1])) last.items.push(item[2]);
        else blocks.push({ kind: "list", ordered: Boolean(item[1]), items: [item[2]] });
      } else {
        lines.push(line);
      }
    }
    flush();
  }
  return blocks;
}
