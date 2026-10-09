import { citationColor, citationLabel } from "@/lib/citations";
import type { Citation } from "@/lib/types";

/** The inline [n] button inside an answer. Clicking it opens the passage in the sources panel;
 *  while that passage is open there, the chip gets a ring so you can see which one it is. */
type Props = { citation: Citation; active?: boolean; onClick: () => void };

export function CitationChip({ citation, active = false, onClick }: Props) {
  const color = citationColor(citation.n);
  return (
    <button
      type="button"
      onClick={onClick}
      title={`Source ${citation.n}: ${citation.document_title}${citation.section && citation.section !== citation.document_title ? ` — ${citation.section}` : ""}${citation.page !== null ? `, page ${citation.page}` : ""}`}
      aria-pressed={active}
      className={`tap-target group mx-0.5 inline-flex max-w-full items-center gap-1 rounded-md border px-1.5 py-0.5 align-baseline text-[12px] font-medium shadow-2xs transition-all ${color.chip} ${active ? "ring-2 ring-brand-400 ring-offset-1" : ""}`}
    >
      <span className={`font-bold ${color.num}`}>[{citation.n}]</span>
      <span className="hidden truncate text-ink-700 sm:inline">{citationLabel(citation)}</span>
    </button>
  );
}
