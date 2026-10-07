"use client";

import { ChevronDown, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { citationColor, documentKind, matchStrength, passageLocation, sourceFor } from "@/lib/citations";
import type { Citation, QueryResult } from "@/lib/types";
import { CopyButton } from "./CopyButton";
import { FileTypeIcon } from "./FileTypeIcon";

type Props = {
  result: QueryResult;
  selected: number;                  // the citation number being inspected
  flash: number;                     // changes on every click in the chat, to replay the highlight
  onSelect: (n: number) => void;
};

/**
 * Contents of the sources panel, organised the way people think about it:
 * which documents the answer used, and which passages of each one.
 * The selected passage (the [n] clicked in the chat) is expanded, highlighted and scrolled to.
 */
export function SourceInspector({ result, selected, flash, onSelect }: Props) {
  const items = useRef(new Map<number, HTMLElement>());

  // Bring the selected passage into view whenever a citation is clicked (even the same one again).
  useEffect(() => {
    items.current.get(selected)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [selected, flash]);

  if (result.citations.length === 0) {
    return <p className="mt-10 text-center text-[13px] text-slate-500">This answer has no citations to inspect.</p>;
  }

  // Group citations by document, in the order the answer first cites each one.
  const groups = new Map<string, Citation[]>();
  for (const c of result.citations) groups.set(c.document_id, [...(groups.get(c.document_id) ?? []), c]);
  const passages = result.citations.length;

  return (
    <>
      <p className="px-1 text-[12.5px] leading-relaxed text-slate-600">
        This answer uses <strong className="text-slate-900">{passages} passage{passages === 1 ? "" : "s"}</strong> from{" "}
        <strong className="text-slate-900">
          {groups.size} document{groups.size === 1 ? "" : "s"}
        </strong>
        . Click a number in the answer to jump to its passage.
      </p>

      {[...groups.values()].map((cites) => {
        const doc = cites[0];
        const link = safeHttpUrl(doc.source_uri);
        return (
          <section key={doc.document_id} className="rounded-xl border border-slate-200 bg-white shadow-2xs">
            {/* The document: what it is and where to find the original */}
            <header className="flex items-start gap-2.5 border-b border-slate-100 p-3">
              <FileTypeIcon type={doc.source_type} />
              <div className="min-w-0 flex-1">
                <h3 className="line-clamp-2 text-[13px] font-bold leading-snug text-slate-900">{doc.document_title}</h3>
                <p className="truncate text-[11.5px] text-slate-500">{documentKind(doc)}</p>
              </div>
              {link && (
                <a
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-[11.5px] font-semibold text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800"
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                  Open page
                </a>
              )}
            </header>

            {/* The passages quoted from it */}
            <ul className="flex flex-col gap-1.5 p-2">
              {cites.map((c) => (
                <Passage
                  key={c.n}
                  citation={c}
                  result={result}
                  active={c.n === selected}
                  flash={flash}
                  onSelect={() => onSelect(c.n)}
                  register={(el) => (el ? items.current.set(c.n, el) : items.current.delete(c.n))}
                />
              ))}
            </ul>
          </section>
        );
      })}
    </>
  );
}

type PassageProps = {
  citation: Citation;
  result: QueryResult;
  active: boolean;
  flash: number;
  onSelect: () => void;
  register: (el: HTMLLIElement | null) => void;
};

function Passage({ citation: c, result, active, flash, onSelect, register }: PassageProps) {
  const match = matchStrength(sourceFor(c, result.sources));
  const color = citationColor(c.n);
  return (
    <li
      ref={register}
      className={`relative scroll-mt-20 overflow-hidden rounded-lg border transition-colors ${
        active ? "border-indigo-300 bg-indigo-50/50 ring-2 ring-indigo-200" : "border-transparent hover:bg-slate-50"
      }`}
    >
      {/* A short flash each time this passage is picked from the chat. The key makes React
          re-create the element, which restarts the CSS animation. */}
      {active && <span key={flash} className="pointer-events-none absolute inset-0 animate-[flash_1.2s_ease-out_forwards] bg-indigo-200/60" aria-hidden />}

      <button type="button" onClick={onSelect} aria-expanded={active} className="relative flex w-full items-center gap-2 px-2.5 py-2 text-left">
        <span className={`font-mono text-xs font-bold ${color.num}`}>[{c.n}]</span>
        <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-slate-700" title={`Passage ID: ${c.chunk_id}`}>
          {passageLocation(c)}
        </span>
        {match && (
          <span title={match.hint} className={`shrink-0 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold ${match.tone}`}>
            {match.label}
          </span>
        )}
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${active ? "rotate-180" : ""}`} aria-hidden />
      </button>

      {active ? (
        <div className="relative px-2.5 pb-2.5">
          <PassageText text={readable(c)} />
          <div className="mt-1.5 flex justify-end">
            <CopyButton
              label="Copy passage"
              text={() => c.snippet}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11.5px] font-semibold text-indigo-600 hover:bg-indigo-50"
            >
              Copy passage
            </CopyButton>
          </div>
        </div>
      ) : (
        // Padding goes on the wrapper: inside a line-clamped element it would reveal part of line 3.
        <div className="relative px-2.5 pb-2">
          <p className="line-clamp-2 text-[11.5px] leading-relaxed text-slate-500">{readable(c)}</p>
        </div>
      )}
    </li>
  );
}

const PREVIEW_CHARS = 600;

/** The quoted passage. Long ones start shortened, with a button to show the rest. */
function PassageText({ text }: { text: string }) {
  const [full, setFull] = useState(false);
  const long = text.length > PREVIEW_CHARS;
  // Cut at the last space before the limit, so no word is split in half.
  const shown = !long || full ? text : `${text.slice(0, text.lastIndexOf(" ", PREVIEW_CHARS))}…`;
  return (
    <blockquote className="whitespace-pre-wrap break-words rounded-md border-l-2 border-indigo-500 bg-white p-2.5 text-[12.5px] leading-relaxed text-slate-700 shadow-2xs">
      {shown}
      {long && (
        <button type="button" onClick={() => setFull(!full)} className="mt-1 block text-[11.5px] font-semibold text-indigo-600 hover:text-indigo-800">
          {full ? "Show less" : "Show full passage"}
        </button>
      )}
    </blockquote>
  );
}

/** Make a passage pleasant to read for people who don't know Markdown.
 *  - PDFs keep the PDF's line wraps ("closest in meaning\nusing\ncosine…"): join them back into
 *    sentences, keeping blank-line paragraph breaks.
 *  - Markdown and web pages: drop ``` fence lines, `code` backticks and **bold** stars.
 *  - Everywhere: no more than one blank line in a row.
 *  "Copy passage" still copies the original text. */
function readable(c: Citation): string {
  let text = c.snippet;
  if (c.source_type === "pdf") {
    text = text.replace(/([^\n])\n(?!\n)/g, "$1 ");
  } else {
    text = text
      .replace(/^[ \t]*```.*$/gm, "")
      .replace(/`([^`\n]+)`/g, "$1")
      .replace(/\*\*([^*\n]+)\*\*/g, "$1");
  }
  return text.replace(/[ \t]+$/gm, "").replace(/\n{3,}/g, "\n\n").trim();
}

/** Only real web links become clickable — never "javascript:" or other schemes. */
function safeHttpUrl(uri: string | null): string | null {
  if (!uri) return null;
  try {
    const url = new URL(uri);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;    // a filename like "report.pdf", not a URL
  }
}
