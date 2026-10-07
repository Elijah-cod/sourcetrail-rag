import { Copy, ExternalLink } from "lucide-react";
import { citationColor, citationLabel, relevanceLabel, sourceFor } from "@/lib/citations";
import type { Citation, QueryResult } from "@/lib/types";
import { FileTypeIcon } from "./FileTypeIcon";

type Props = {
  result: QueryResult;
  selected: number;                  // the citation number being inspected
  onSelect: (n: number) => void;
  onCopyPassage: (text: string) => void;
};

/** Contents of the sources panel: the inspected citation, then the other sources of the answer. */
export function SourceInspector({ result, selected, onSelect, onCopyPassage }: Props) {
  const current = result.citations.find((c) => c.n === selected) ?? result.citations[0];
  if (!current) {
    return <p className="mt-10 text-center text-[13px] text-slate-500">This answer has no citations to inspect.</p>;
  }
  const relevance = relevanceLabel(sourceFor(current, result.sources));
  const others = result.citations.filter((c) => c.n !== current.n);

  return (
    <>
      <div className="flex flex-col gap-3 rounded-xl border border-indigo-200/90 bg-white p-4 shadow-xs">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <FileTypeIcon type={current.source_type} />
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-[13px] font-bold text-slate-900">{current.document_title}</span>
              <span className="truncate text-[11px] font-medium text-slate-500">
                {[current.page !== null ? `Page ${current.page}` : null, current.section].filter(Boolean).join(" • ") ||
                  current.source_uri}
              </span>
            </div>
          </div>
          {relevance && (
            <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
              {relevance}
            </span>
          )}
        </div>
        <div className="border-l-2 border-indigo-500 pl-3">
          <span className="mb-1 block font-mono text-[10px] font-bold uppercase tracking-wider text-indigo-800">
            Source [{current.n}] · Grounded excerpt
          </span>
          <p className="whitespace-pre-wrap break-words rounded-lg border border-amber-200/60 bg-amber-50/60 p-2.5 text-[12.5px] leading-relaxed text-slate-700">
            {readable(current)}
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          {safeHttpUrl(current.source_uri) ? (
            <a
              href={safeHttpUrl(current.source_uri)!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-indigo-600 transition-colors hover:bg-indigo-50 hover:text-indigo-800"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              Open original page
            </a>
          ) : (
            <button
              type="button"
              onClick={() => onCopyPassage(current.snippet)}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-indigo-600 transition-colors hover:bg-indigo-50 hover:text-indigo-800"
            >
              <Copy className="h-3.5 w-3.5" aria-hidden />
              Copy passage
            </button>
          )}
          <span className="max-w-full truncate rounded border border-slate-200/50 bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-500">
            {current.chunk_id}
          </span>
        </div>
      </div>

      {others.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="px-1 font-mono text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Other sources in this answer</span>
          {others.map((c) => {
            const rel = relevanceLabel(sourceFor(c, result.sources));
            return (
              <button
                key={c.n}
                type="button"
                onClick={() => onSelect(c.n)}
                className="flex w-full flex-col gap-1.5 rounded-xl border border-slate-200 bg-white p-3 text-left shadow-2xs transition-all hover:border-indigo-300 hover:bg-indigo-50/40"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className={`font-mono text-xs font-bold ${citationColor(c.n).num}`}>[{c.n}]</span>
                    <span className="truncate text-[12.5px] font-semibold text-slate-800">{citationLabel(c, 34)}</span>
                  </div>
                  {rel && <span className="shrink-0 text-[11px] font-semibold text-emerald-600">{rel}</span>}
                </div>
                <p className="line-clamp-2 text-[11.5px] leading-relaxed text-slate-500">{c.snippet}</p>
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}

/** PDF text keeps the PDF's line wraps ("closest in meaning\nusing\ncosine…"); join them back
 *  into flowing sentences, keeping blank-line paragraph breaks. Other formats keep their newlines
 *  (Markdown chunks can contain code examples). */
function readable(c: Citation): string {
  if (c.source_type !== "pdf") return c.snippet;
  return c.snippet.replace(/([^\n])\n(?!\n)/g, "$1 ");
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
