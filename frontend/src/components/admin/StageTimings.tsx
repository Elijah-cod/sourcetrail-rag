"use client";

/** Stages in the order they run. Several can be absent: each question only goes through some. */
export const STAGES: { label: string; key: string; note: string }[] = [
  { label: "Embed", key: "embed_ms", note: "turning the question into a vector" },
  { label: "Search", key: "search_ms", note: "vector + keyword search in the database" },
  { label: "Rerank", key: "rerank_ms", note: "cross-encoder reranking of the top results" },
  { label: "Codes", key: "lookup_ms", note: "exact lookup of codes such as SEC-014" },
  { label: "Parts", key: "facets_ms", note: "a separate search for each part of a multi-part question" },
  { label: "Answer", key: "generation_ms", note: "the LLM writing the answer" },
  { label: "Follow-up search", key: "gap_search_ms", note: "searching again for a part the first answer said was missing" },
  { label: "Second answer", key: "gap_answer_ms", note: "the LLM answering again with what the follow-up search found" },
  { label: "Recheck", key: "recheck_ms", note: "asking the LLM to re-read the sources for a part it called missing" },
];

export const formatMs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`);

/** The time of each stage one question went through (admin only: visitors never receive these). */
export function StageTimings({ timings }: { timings: Record<string, number> }) {
  const stages = STAGES.filter((s) => timings[s.key] !== undefined);
  if (stages.length === 0) return <p className="text-[13px] text-ink-500">No stage timings recorded.</p>;
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 text-[13px]">
      {stages.map((s) => (
        <div key={s.key} className="flex items-baseline gap-1.5" title={s.note}>
          <dt className="text-ink-500">{s.label}</dt>
          <dd className="font-mono font-semibold tabular-nums text-ink-800">{formatMs(timings[s.key])}</dd>
        </div>
      ))}
    </dl>
  );
}
