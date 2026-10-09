import { Fragment, type ReactNode } from "react";
import { claimBefore } from "@/lib/highlight";
import type { Citation } from "@/lib/types";
import { CitationChip } from "./CitationChip";

/*
 * Renders an LLM answer SAFELY.
 *
 * The text comes from an AI reading documents that strangers upload, so it must never be
 * inserted as HTML (that would allow XSS: scripts running in other visitors' browsers).
 * Instead we parse a tiny, known subset — paragraphs, bullet/numbered lists, **bold**,
 * `code` and [n] citations — into React elements. Everything else stays plain text,
 * which React escapes automatically.
 */

// onCite also gets the answer sentence the [n] belongs to, so the passage can highlight it.
type Props = {
  text: string;
  citations: Citation[];
  onCite: (n: number, claim?: string) => void;
  activeN?: number | null;       // the citation open in the panel…
  activeClaim?: string;          // …and which sentence it was clicked from, so only that chip is ringed
};

const LIST_ITEM = /^\s*(?:[-*•]|\d+[.)])\s+/;
const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[\d+\])/g;   // the pieces we know how to style

export function AnswerText({ text, citations, onCite, activeN = null, activeClaim }: Props) {
  const byNumber = new Map(citations.map((c) => [c.n, c]));

  const inline = (line: string, keyPrefix: string): ReactNode[] =>
    line.split(INLINE).map((part, i, parts) => {
      const key = `${keyPrefix}-${i}`;
      const cite = part.match(/^\[(\d+)\]$/);
      if (cite) {
        const citation = byNumber.get(Number(cite[1]));
        if (!citation) return part;
        const claim = claimBefore(parts.slice(0, i).join(""));
        const active = citation.n === activeN && (activeClaim === undefined || activeClaim === claim);
        return <CitationChip key={key} citation={citation} active={active} onClick={() => onCite(citation.n, claim)} />;
      }
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return <strong key={key} className="font-semibold text-ink-900">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
        return (
          <code key={key} className="rounded border border-brand-100 bg-brand-50/70 px-1.5 py-0.5 font-mono text-[12.5px] font-medium text-brand-700">
            {part.slice(1, -1)}
          </code>
        );
      }
      return <Fragment key={key}>{part}</Fragment>;   // plain text: React escapes it
    });

  const blocks = text.trim().split(/\n\s*\n/);   // blank line = new paragraph/list
  return (
    <div className="space-y-3">
      {blocks.map((block, b) => {
        const lines = block.split("\n").filter((l) => l.trim());
        if (lines.length && lines.every((l) => LIST_ITEM.test(l))) {
          const ordered = /^\s*\d/.test(lines[0]);
          const ListTag = ordered ? "ol" : "ul";
          return (
            <ListTag key={b} className={`space-y-1.5 pl-5 ${ordered ? "list-decimal" : "list-disc"} marker:text-ink-400`}>
              {lines.map((l, i) => (
                <li key={i}>{inline(l.replace(LIST_ITEM, ""), `${b}-${i}`)}</li>
              ))}
            </ListTag>
          );
        }
        return (
          <p key={b}>
            {lines.map((l, i) => (
              <Fragment key={i}>
                {i > 0 && " "}
                {inline(l.replace(/^#+\s*/, ""), `${b}-${i}`)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
