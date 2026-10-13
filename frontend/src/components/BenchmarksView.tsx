"use client";

import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { getBenchmarks } from "@/lib/api";
import type { Benchmarks, RegressionQuestion, RegressionResults, RetrievalResults } from "@/lib/types";
import { MODE_LABELS } from "./SettingsPopover";

/** The latest results of the two evaluation scripts in backend/eval, as the backend serves them. */
export function BenchmarksView() {
  const [data, setData] = useState<Benchmarks | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const fetchResults = async () => {
      try {
        const results = await getBenchmarks();
        if (!cancelled) {
          setData(results);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Couldn't load the benchmarks.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void fetchResults();
    return () => {
      cancelled = true;
    };
  }, [reloads]);

  const load = () => {
    setLoading(true);
    setReloads((n) => n + 1);
  };

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-8 md:py-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-heading text-xl font-bold text-ink-900">Benchmarks</h1>
          <p className="mt-1 max-w-2xl text-[13px] text-ink-600">
            How well retrieval and answers hold up on fixed test sets: the demo collection, and the documents and
            questions from the regression reports. Results are from the last run of the evaluation scripts.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="flex h-11 items-center gap-1.5 rounded-lg border border-ink-200 bg-raised px-3 text-[12.5px] font-semibold text-ink-700 shadow-2xs transition-colors hover:bg-ink-50 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden />}
          Reload
        </button>
      </div>

      {error && (
        <p className="flex items-start gap-2 rounded-xl border border-danger-200 bg-danger-50 px-4 py-3 text-[13px] text-danger-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {error}
        </p>
      )}

      {data && (
        <>
          <Regression results={data.regression} />
          <Retrieval results={data.retrieval} />
        </>
      )}
    </div>
  );
}

function when(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function NotRun({ command }: { command: string }) {
  return (
    <p className="rounded-xl border border-dashed border-ink-300 bg-raised px-4 py-5 text-[13px] text-ink-600">
      No results on this server yet. To produce them, the maintainer runs{" "}
      <code className="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-[12px] text-ink-800">{command}</code> in{" "}
      <code className="font-mono text-[12px]">backend/</code>.
    </p>
  );
}

function Tile({ label, value, note, good }: { label: string; value: string; note?: string; good?: boolean }) {
  const tone = good === undefined ? "text-ink-900" : good ? "text-success-700" : "text-warning-700";
  return (
    <div className="flex flex-col rounded-xl border border-ink-200 bg-raised p-3 shadow-2xs">
      <span className="text-[13px] font-medium text-ink-500">{label}</span>
      <span className={`font-heading text-xl font-bold ${tone}`}>{value}</span>
      {note && <span className="text-[13px] text-ink-500">{note}</span>}
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="font-heading text-[15px] font-bold text-ink-900">{title}</h2>
        {subtitle && <p className="text-[12.5px] text-ink-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

// ---------- regression benchmark ----------

function Regression({ results }: { results: RegressionResults | null }) {
  // null = not chosen yet: a run that needs attention opens on its problems, a clean one on everything.
  const [onlyProblems, setOnlyProblems] = useState<boolean | null>(null);
  if (!results) {
    return (
      <Section title="Regression benchmark">
        <NotRun command="uv run python -m eval.regression.run_regression --answers" />
      </Section>
    );
  }
  return (
    <RegressionResultsView
      results={results}
      onlyProblems={onlyProblems ?? results.questions.some(hasProblem)}
      setOnlyProblems={setOnlyProblems}
    />
  );
}

function hasProblem(q: RegressionQuestion) {
  return (q.answerable && (q.facets_covered < q.facets || q.uncovered.length > 0)) || (q.problems?.length ?? 0) > 0 || (q.unverified?.length ?? 0) > 0;
}

function RegressionResultsView({ results, onlyProblems, setOnlyProblems }: {
  results: RegressionResults;
  onlyProblems: boolean;
  setOnlyProblems: (v: boolean) => void;
}) {
  const stats = useMemo(() => {
    const qs = results.questions;
    const answerable = qs.filter((q) => q.answerable);
    const graded = qs.filter((q) => q.problems !== null && !q.problems[0]?.startsWith("LLM unavailable"));
    const latencies = qs.map((q) => q.latency_ms).sort((a, b) => a - b);
    return {
      facets: answerable.reduce((n, q) => n + q.facets, 0),
      found: answerable.reduce((n, q) => n + q.facets_covered, 0),
      complete: answerable.filter((q) => q.facets_covered === q.facets).length,
      answerable: answerable.length,
      uncovered: answerable.filter((q) => q.uncovered.length > 0).length,
      graded: graded.length,
      passed: graded.filter((q) => q.problems!.length === 0).length,
      unverified: graded.filter((q) => (q.unverified?.length ?? 0) > 0).length,
      ingestOk: results.ingestion.filter((i) => i.ok).length,
      median: latencies[Math.floor(latencies.length / 2)] ?? 0,
    };
  }, [results]);

  // Every way the run can fall short, in words, so a green tile can't hide a problem elsewhere.
  const issues = [
    stats.found < stats.facets && `${stats.facets - stats.found} question part${plural(stats.facets - stats.found)} found no supporting passage`,
    stats.uncovered > 0 &&
      `${stats.uncovered} question${plural(stats.uncovered)} would tell the reader a part isn't in the documents, though it is`,
    results.with_answers && stats.passed < stats.graded && `${stats.graded - stats.passed} answer${plural(stats.graded - stats.passed)} failed a check`,
    results.with_answers && stats.unverified > 0 && `${stats.unverified} answer${plural(stats.unverified)} contain a figure found in no source`,
    stats.ingestOk < results.ingestion.length && `${results.ingestion.length - stats.ingestOk} ingestion check${plural(results.ingestion.length - stats.ingestOk)} failed`,
  ].filter((issue): issue is string => Boolean(issue));

  const rows = onlyProblems ? results.questions.filter(hasProblem) : results.questions;

  return (
    <Section
      title="Regression benchmark"
      subtitle={`${results.questions.length} questions over ${new Set(results.questions.map((q) => q.fixture)).size} documents · run ${when(results.generated_at)}`}
    >
      <div
        className={`flex items-start gap-2 rounded-xl border px-4 py-3 text-[13px] ${
          issues.length ? "border-warning-200 bg-warning-50 text-warning-900" : "border-success-200 bg-success-50 text-success-900"
        }`}
      >
        {issues.length ? (
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning-600" aria-hidden />
        ) : (
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success-600" aria-hidden />
        )}
        <div>
          <p className="font-semibold">
            {issues.length ? "Needs attention" : "Every check in this run passed"}
          </p>
          {issues.length > 0 && (
            <ul className="mt-1 list-disc space-y-0.5 pl-4">
              {issues.map((issue) => (
                <li key={issue}>{issue}.</li>
              ))}
            </ul>
          )}
          {!results.with_answers && (
            <p className="mt-1 text-ink-600">
              This run only checked that the right passages are found. The answers written from them
              weren&apos;t generated or graded, so it says nothing yet about answer quality.
            </p>
          )}
        </div>
      </div>

      <TileGroup title="Finding the evidence">
        <Tile label="Question parts search found a passage for" value={`${stats.found}/${stats.facets}`} note={`every part found in ${stats.complete}/${stats.answerable} questions`} good={stats.found === stats.facets} />
        <Tile label="Questions that would wrongly say a part is missing" value={`${stats.uncovered}/${stats.answerable}`} note="the passage was found, but judged too weak a match" good={stats.uncovered === 0} />
        <Tile label="Ingestion checks" value={`${stats.ingestOk}/${results.ingestion.length}`} good={stats.ingestOk === results.ingestion.length} />
        <Tile label="Median retrieval time" value={`${(stats.median / 1000).toFixed(1)} s`} />
      </TileGroup>

      <TileGroup title="Using it in answers">
        {results.with_answers ? (
          <>
            <Tile label="Answers passing every check" value={`${stats.passed}/${stats.graded}`} good={stats.passed === stats.graded} />
            <Tile label="Answers with an unsourced figure" value={`${stats.unverified}`} note="found in no source" good={stats.unverified === 0} />
          </>
        ) : (
          <Tile label="Answers" value="Not graded" note="this run checked the passages found, not the answers" />
        )}
      </TileGroup>

      <label className="flex min-h-11 cursor-pointer items-center gap-2 self-start text-[13px] text-ink-600">
        <input type="checkbox" checked={onlyProblems} onChange={(e) => setOnlyProblems(e.target.checked)} className="h-4 w-4 accent-brand-600" />
        Only questions with a problem
      </label>

      {/* Phones: one card per question, so no column is hidden off-screen. */}
      <ul className="flex flex-col gap-2 sm:hidden">
        {rows.map((q) => (
          <QuestionCard key={q.id} q={q} />
        ))}
        {rows.length === 0 && <li className="rounded-xl border border-ink-200 bg-raised px-3 py-4 text-center text-[13px] text-ink-500">No problems in this run.</li>}
      </ul>

      <div className="hidden overflow-x-auto rounded-xl border border-ink-200 bg-raised sm:block" tabIndex={0} role="region" aria-label="Questions">
        <table className="w-full min-w-[640px] text-left text-[13px]">
          <thead className="border-b border-ink-200 bg-ink-50 text-[12px] font-semibold text-ink-500">
            <tr>
              <th className="px-3 py-2">Question</th>
              <th className="px-3 py-2">Retrieval</th>
              <th className="px-3 py-2">Answer</th>
              <th className="px-3 py-2 text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {rows.map((q) => (
              <QuestionRow key={q.id} q={q} />
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-ink-500">No problems in this run.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

const plural = (n: number) => (n === 1 ? "" : "s");

function TileGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-[13px] font-semibold text-ink-700">{title}</h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{children}</div>
    </div>
  );
}

function Verdict({ ok, children }: { ok: boolean; children: ReactNode }) {
  const Icon = ok ? CheckCircle2 : XCircle;
  return (
    <span className={`inline-flex items-start gap-1 ${ok ? "text-success-700" : "text-warning-700"}`}>
      <Icon className="mt-[1px] h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{children}</span>
    </span>
  );
}

/** The retrieval and answer verdicts for one question, shared by the table row and the phone card. */
function verdicts(q: RegressionQuestion) {
  // Unanswerable questions: retrieval passes when nothing is sent; otherwise the LLM must refuse.
  const retrieval = q.answerable ? (
    <Verdict ok={q.facets_covered === q.facets && q.uncovered.length === 0}>
      {q.facets_covered}/{q.facets} parts found
      {q.uncovered.length > 0 && <span className="block text-ink-500">reported missing: {q.uncovered.join("; ")}</span>}
    </Verdict>
  ) : q.sources_sent === 0 ? (
    <Verdict ok>refused before the LLM</Verdict>
  ) : (
    <span className="text-ink-500">sent to the LLM to refuse</span>
  );

  let answer: ReactNode = <span className="text-ink-500">not graded</span>;
  if (q.problems !== null) {
    answer = q.problems.length === 0 ? <Verdict ok>pass</Verdict> : <Verdict ok={false}>{q.problems.join("; ")}</Verdict>;
  }
  const unverified = q.unverified && q.unverified.length > 0 && (
    <span className="block text-[12px] text-warning-700">not in any source: {q.unverified.join(", ")}</span>
  );
  return { retrieval, answer, unverified, time: `${(q.latency_ms / 1000).toFixed(1)} s` };
}

function QuestionText({ q }: { q: RegressionQuestion }) {
  return (
    <>
      <span className="font-mono text-[12px] text-ink-500">{q.id}</span>
      <span className="block text-ink-800" title={q.question}>
        {q.question.length > 140 ? `${q.question.slice(0, 140)}…` : q.question}
      </span>
    </>
  );
}

function QuestionRow({ q }: { q: RegressionQuestion }) {
  const v = verdicts(q);
  return (
    <tr className="align-top">
      <td className="px-3 py-2">
        <QuestionText q={q} />
      </td>
      <td className="px-3 py-2">{v.retrieval}</td>
      <td className="px-3 py-2">
        {v.answer}
        {v.unverified}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-ink-500">{v.time}</td>
    </tr>
  );
}

function QuestionCard({ q }: { q: RegressionQuestion }) {
  const v = verdicts(q);
  return (
    <li className="rounded-xl border border-ink-200 bg-raised p-3 text-[13px]">
      <QuestionText q={q} />
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-[12px] font-semibold text-ink-500">Retrieval</dt>
        <dd>{v.retrieval}</dd>
        <dt className="text-[12px] font-semibold text-ink-500">Answer</dt>
        <dd>
          {v.answer}
          {v.unverified}
        </dd>
        <dt className="text-[12px] font-semibold text-ink-500">Time</dt>
        <dd className="tabular-nums text-ink-600">{v.time}</dd>
      </dl>
    </li>
  );
}

// ---------- retrieval evaluation ----------

function Retrieval({ results }: { results: RetrievalResults | null }) {
  if (!results) {
    return (
      <Section title="Retrieval modes">
        <NotRun command="uv run python -m eval.run_eval" />
      </Section>
    );
  }
  const best = Math.max(...results.modes.map((m) => m.mrr));
  return (
    <Section
      title="Retrieval modes"
      subtitle={`${results.answerable} questions over the demo collection (+${results.unanswerable} unanswerable) · run ${when(results.generated_at)}`}
    >
      <p className="text-[12px] text-ink-500 sm:hidden">Swipe the table sideways to see every column.</p>
      <div className="overflow-x-auto rounded-xl border border-ink-200 bg-raised" tabIndex={0} role="region" aria-label="Retrieval modes">
        <table className="w-full min-w-[560px] text-left text-[12.5px] tabular-nums">
          <thead className="border-b border-ink-200 bg-ink-50 text-[13px] font-semibold text-ink-500">
            <tr>
              <th className="px-3 py-2">Mode</th>
              <th className="px-3 py-2 text-right" title="Share of questions with a correct passage first">Recall@1</th>
              <th className="px-3 py-2 text-right" title="Share of questions with a correct passage in the top 5">Recall@5</th>
              <th className="px-3 py-2 text-right" title="Share of questions with a correct passage in the top 10">Recall@10</th>
              <th className="px-3 py-2 text-right" title="Average of 1/rank of the first correct passage">MRR</th>
              <th className="px-3 py-2 text-right">Avg time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {results.modes.map((m) => (
              <tr key={m.mode} className={m.mrr === best ? "bg-brand-50/50" : undefined}>
                <td className="px-3 py-2 font-medium text-ink-800">
                  {MODE_LABELS[m.mode] ?? m.mode}
                  {m.mode === "hybrid_rerank" && <span className="ml-1.5 text-[12px] font-normal text-ink-500">(used for answers)</span>}
                </td>
                <td className="px-3 py-2 text-right">{(m.recall_at_1 * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 text-right">{(m.recall_at_5 * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 text-right">{(m.recall_at_10 * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 text-right">{m.mrr.toFixed(3)}</td>
                <td className="px-3 py-2 text-right text-ink-500">{m.avg_ms.toLocaleString()} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {results.threshold && (
        <p className="text-[12.5px] text-ink-600">
          Relevance threshold {results.threshold.value}: refuses {results.threshold.unanswerable_refused}/{results.threshold.unanswerable}{" "}
          unanswerable questions and wrongly refuses {results.threshold.answerable_refused}/{results.threshold.answerable} answerable ones.
        </p>
      )}
    </Section>
  );
}
