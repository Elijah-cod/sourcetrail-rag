import { citationColor, citationLabel } from "@/lib/citations";
import type { Citation } from "@/lib/types";

/** The inline [n] button inside an answer. Clicking it opens the passage in the sources panel. */
export function CitationChip({ citation, onClick }: { citation: Citation; onClick: () => void }) {
  const color = citationColor(citation.n);
  return (
    <button
      type="button"
      onClick={onClick}
      title={`Source ${citation.n}: ${citation.document_title}`}
      className={`group mx-0.5 inline-flex max-w-full items-center gap-1 rounded-md border px-1.5 py-0.5 align-baseline text-[12px] font-medium shadow-2xs transition-all ${color.chip}`}
    >
      <span className={`font-bold ${color.num}`}>[{citation.n}]</span>
      <span className="hidden truncate text-slate-700 sm:inline">{citationLabel(citation)}</span>
    </button>
  );
}
