"use client";

import { ChevronDown, ExternalLink } from "lucide-react";
import { Fragment, useEffect, useRef } from "react";
import { citationColor, documentKind, matchStrength, passageLocation, sourceFor } from "@/lib/citations";
import { splitSentences, supportingSentences } from "@/lib/highlight";
import { scrollBehavior } from "@/lib/motion";
import { formatPassage, previewText, type Block } from "@/lib/passage";
import type { Citation, QueryResult } from "@/lib/types";
import { CopyButton } from "./CopyButton";
import { FileTypeIcon } from "./FileTypeIcon";

type Props = {
  result: QueryResult;
  selected: number;                  // the citation number being inspected
  flash: number;                     // changes on every click in the chat, to replay the highlight
  claim?: string;                    // the answer sentence that was clicked, to highlight its support
  onSelect: (n: number) => void;
};

/**
 * Contents of the sources panel, organised the way people think about it:
 * which documents the answer used, and which passages of each one.
 * The selected passage (the [n] clicked in the chat) is expanded, highlighted and scrolled to.
 */
export function SourceInspector({ result, selected, flash, claim, onSelect }: Props) {
  const items = useRef(new Map<number, HTMLElement>());

  // Whenever a citation is clicked (even the same one again), bring its highlighted sentence
  // into view, or the top of the passage if nothing is highlighted.
  useEffect(() => {
    const item = items.current.get(selected);
    const mark = item?.querySelector("mark[data-support]");
    if (mark) mark.scrollIntoView({ behavior: scrollBehavior(), block: "center" });
    else item?.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  }, [selected, flash]);

  if (result.citations.length === 0) {
    return <p className="mt-10 text-center text-[13px] text-slate-500">This answer has no citations to inspect.</p>;
  }

  // Group citations by document, in the order the answer first cites each one.
  const groups = new Map<string, Citation[]>();
  for (const c of result.citations) groups.set(c.document_id, [...(groups.get(c.document_id) ?? []), c]);

  return (
    <>
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
                <p className="truncate text-[13px] text-slate-500">{documentKind(doc)}</p>
              </div>
              {link && (
                <a
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-[13px] font-semibold text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800"
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
                  claim={c.n === selected ? claim : undefined}
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
  claim?: string;
  onSelect: () => void;
  register: (el: HTMLLIElement | null) => void;
};

function Passage({ citation: c, result, active, flash, claim, onSelect, register }: PassageProps) {
  const match = matchStrength(sourceFor(c, result.sources));
  const color = citationColor(c.n);
  const blocks = formatPassage(c);
  // Only the open passage highlights, and only when we know which answer sentence was clicked.
  const marks = active && claim ? supportingSentences(claim, blocks.flatMap(blockSentences)) : new Set<string>();

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

      <button type="button" onClick={onSelect} aria-expanded={active} className="relative flex min-h-11 w-full items-center gap-2 px-2.5 py-2 text-left">
        <span className={`font-mono text-xs font-bold ${color.num}`}>[{c.n}]</span>
        <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-slate-700">{passageLocation(c)}</span>
        {match && (
          <span title={match.hint} className={`shrink-0 rounded-full border px-2 py-0.5 text-[12px] font-semibold ${match.tone}`}>
            {match.label}
          </span>
        )}
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${active ? "rotate-180" : ""}`} aria-hidden />
      </button>

      {active ? (
        <div className="relative px-2.5 pb-2.5">
          <div className="space-y-2.5 rounded-md border-l-2 border-indigo-500 bg-white p-3 text-[12.5px] leading-relaxed text-slate-700 shadow-2xs">
            {blocks.map((block, i) => (
              <BlockView key={i} block={block} marks={marks} />
            ))}
          </div>
          <div className="mt-1.5 flex justify-end">
            <CopyButton
              label="Copy passage"
              text={() => c.snippet}
              className="inline-flex min-h-10 items-center gap-1 rounded-lg px-2.5 text-[13px] font-semibold text-indigo-600 hover:bg-indigo-50"
            >
              Copy passage
            </CopyButton>
          </div>
        </div>
      ) : (
        // Padding goes on the wrapper: inside a line-clamped element it would reveal part of line 3.
        <div className="relative px-2.5 pb-2">
          <p className="line-clamp-2 text-[13px] leading-relaxed text-slate-500">{previewText(blocks)}</p>
        </div>
      )}
    </li>
  );
}

/** One readable piece of a passage: a heading, a paragraph, or a spreadsheet record. */
function BlockView({ block, marks }: { block: Block; marks: Set<string> }) {
  if (block.kind === "heading") {
    // The PDF's own heading levels, scaled down to fit the panel.
    const size = block.level === 1 ? "text-[15px] font-bold" : block.level === 2 ? "text-[14px] font-bold" : "text-[13px] font-semibold";
    return <p className={`${size} pt-1 leading-snug text-slate-900 first:pt-0`}><Marked text={block.text} marks={marks} /></p>;
  }
  if (block.kind === "list") {
    const List = block.ordered ? "ol" : "ul";
    return (
      <List className={`space-y-1 pl-5 ${block.ordered ? "list-decimal" : "list-disc"} marker:text-slate-400`}>
        {block.items.map((item, i) => (
          <li key={i}><Marked text={item} marks={marks} /></li>
        ))}
      </List>
    );
  }
  if (block.kind === "text") return <p className="whitespace-pre-line break-words"><Marked text={block.text} marks={marks} /></p>;
  return (
    <div className="space-y-1.5 border-b border-slate-100 pb-2.5 last:border-0 last:pb-0">
      {block.title && <p className="text-[13px] font-semibold text-slate-900"><Marked text={block.title} marks={marks} /></p>}
      {block.details.length > 0 && (
        <dl className="flex flex-wrap gap-1.5">
          {block.details.map((f) => (
            <div key={f.label} className="flex gap-1 rounded-md bg-slate-100 px-1.5 py-0.5 text-[12px]">
              <dt className="text-slate-500">{f.label}:</dt>
              <dd className="font-medium text-slate-700">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {block.body.map((f, i) => (
        <div key={i}>
          {f.label && <p className="text-[12px] font-semibold uppercase tracking-wide text-slate-400">{f.label}</p>}
          <p className="break-words"><Marked text={f.value} marks={marks} /></p>
        </div>
      ))}
    </div>
  );
}

/** Text with the supporting sentences wrapped in <mark>. (React escapes everything: no HTML.) */
function Marked({ text, marks }: { text: string; marks: Set<string> }) {
  if (marks.size === 0) return <>{text}</>;
  return (
    <>
      {splitSentences(text).map((piece, i) =>
        marks.has(piece.trim()) ? (
          <mark key={i} data-support className="rounded bg-yellow-200 px-0.5 text-slate-900 [box-decoration-break:clone]">
            {piece}
          </mark>
        ) : (
          <Fragment key={i}>{piece}</Fragment>
        ),
      )}
    </>
  );
}

/** Every sentence a block shows, for choosing which ones to highlight. */
function blockSentences(block: Block): string[] {
  const texts =
    block.kind === "record" ? [block.title ?? "", ...block.body.map((f) => f.value)]
    : block.kind === "list" ? block.items
    : [block.text];
  return texts.flatMap(splitSentences);
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
