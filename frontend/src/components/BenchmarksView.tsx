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
          <h1 className="font-heading text-xl font-bold text-slate-900">Benchmarks</h1>
          <p className="mt-1 max-w-2xl text-[13px] text-slate-600">
            How well retrieval and answers hold up on fixed test sets: the demo collection, and the documents and
            questions from the regression reports. Results are from the last run of the evaluation scripts.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="flex h-10 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-[12.5px] font-semibold text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden />}
          Reload
        </button>
      </div>

      {error && (
        <p className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] text-rose-700">
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
    <p className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-5 text-[13px] text-slate-600">
      Not run yet. From <code className="font-mono text-[12px]">backend/</code>, run{" "}
      <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[12px] text-slate-800">{command}</code>
    </p>
  );
}

function Tile({ label, value, note, good }: { label: string; value: string; note?: string; good?: boolean }) {
  const tone = good === undefined ? "text-slate-900" : good ? "text-emerald-700" : "text-amber-700";
  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-3 shadow-2xs">
      <span className="text-[11.5px] font-medium text-slate-500">{label}</span>
      <span className={`font-heading text-xl font-bold ${tone}`}>{value}</span>
      {note && <span className="text-[11.5px] text-slate-500">{note}</span>}
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h2 className="font-heading text-[15px] font-bold text-slate-900">{title}</h2>
        {subtitle && <p className="text-[12.5px] text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

// ---------- regression benchmark ----------

function Regression({ results }: { results: RegressionResults | null }) {
  const [onlyProblems, setOnlyProblems] = useState(false);
  if (!results) {
    return (
      <Section title="Regression benchmark">
        <NotRun command="uv run python -m eval.regression.run_regression --answers" />
      </Section>
    );
  }
  return <RegressionResultsView results={results} onlyProblems={onlyProblems} setOnlyProblems={setOnlyProblems} />;
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

  const rows = onlyProblems ? results.questions.filter(hasProblem) : results.questions;

  return (
    <Section
      title="Regression benchmark"
      subtitle={`${results.questions.length} questions over ${new Set(results.questions.map((q) => q.fixture)).size} documents · run ${when(results.generated_at)}${results.with_answers ? "" : " · retrieval only (answers not graded)"}`}
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {results.with_answers && (
          <Tile label="Answers passing every check" value={`${stats.passed}/${stats.graded}`} good={stats.passed === stats.graded} />
        )}
        <Tile label="Question parts with a passage" value={`${stats.found}/${stats.facets}`} note={`${stats.complete}/${stats.answerable} questions complete`} good={stats.found === stats.facets} />
        <Tile label="Parts wrongly reported missing" value={`${stats.uncovered}`} note={`of ${stats.answerable} questions`} good={stats.uncovered === 0} />
        {results.with_answers && (
          <Tile label="Answers with an unsourced figure" value={`${stats.unverified}`} note="found in no source" good={stats.unverified === 0} />
        )}
        <Tile label="Ingestion checks" value={`${stats.ingestOk}/${results.ingestion.length}`} good={stats.ingestOk === results.ingestion.length} />
        <Tile label="Median retrieval time" value={`${(stats.median / 1000).toFixed(1)} s`} />
      </div>

      <label className="flex min-h-10 cursor-pointer items-center gap-2 self-start text-[12.5px] text-slate-600">
        <input type="checkbox" checked={onlyProblems} onChange={(e) => setOnlyProblems(e.target.checked)} className="h-4 w-4 accent-indigo-600" />
        Only questions with a problem
      </label>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full min-w-[640px] text-left text-[12.5px]">
          <thead className="border-b border-slate-200 bg-slate-50 text-[11.5px] font-semibold text-slate-500">
            <tr>
              <th className="px-3 py-2">Question</th>
              <th className="px-3 py-2">Retrieval</th>
              <th className="px-3 py-2">Answer</th>
              <th className="px-3 py-2 text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((q) => (
              <QuestionRow key={q.id} q={q} />
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-slate-500">No problems in this run.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function Verdict({ ok, children }: { ok: boolean; children: ReactNode }) {
  const Icon = ok ? CheckCircle2 : XCircle;
  return (
    <span className={`inline-flex items-start gap-1 ${ok ? "text-emerald-700" : "text-amber-700"}`}>
      <Icon className="mt-[1px] h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{children}</span>
    </span>
  );
}

function QuestionRow({ q }: { q: RegressionQuestion }) {
  // Unanswerable questions: retrieval passes when nothing is sent; otherwise the LLM must refuse.
  const retrieval = q.answerable ? (
    <Verdict ok={q.facets_covered === q.facets && q.uncovered.length === 0}>
      {q.facets_covered}/{q.facets} parts found
      {q.uncovered.length > 0 && <span className="block text-slate-500">reported missing: {q.uncovered.join("; ")}</span>}
    </Verdict>
  ) : q.sources_sent === 0 ? (
    <Verdict ok>refused before the LLM</Verdict>
  ) : (
    <span className="text-slate-500">sent to the LLM to refuse</span>
  );

  let answer: ReactNode = <span className="text-slate-400">not graded</span>;
  if (q.problems !== null) {
    answer = q.problems.length === 0 ? <Verdict ok>pass</Verdict> : <Verdict ok={false}>{q.problems.join("; ")}</Verdict>;
  }

  return (
    <tr className="align-top">
      <td className="px-3 py-2">
        <span className="font-mono text-[11px] text-slate-400">{q.id}</span>
        <span className="block text-slate-800" title={q.question}>
          {q.question.length > 140 ? `${q.question.slice(0, 140)}…` : q.question}
        </span>
      </td>
      <td className="px-3 py-2">{retrieval}</td>
      <td className="px-3 py-2">
        {answer}
        {q.unverified && q.unverified.length > 0 && (
          <span className="block text-[11.5px] text-amber-700">not in any source: {q.unverified.join(", ")}</span>
        )}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-slate-500">{(q.latency_ms / 1000).toFixed(1)} s</td>
    </tr>
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
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full min-w-[560px] text-left text-[12.5px] tabular-nums">
          <thead className="border-b border-slate-200 bg-slate-50 text-[11.5px] font-semibold text-slate-500">
            <tr>
              <th className="px-3 py-2">Mode</th>
              <th className="px-3 py-2 text-right" title="Share of questions with a correct passage first">Recall@1</th>
              <th className="px-3 py-2 text-right" title="Share of questions with a correct passage in the top 5">Recall@5</th>
              <th className="px-3 py-2 text-right" title="Share of questions with a correct passage in the top 10">Recall@10</th>
              <th className="px-3 py-2 text-right" title="Average of 1/rank of the first correct passage">MRR</th>
              <th className="px-3 py-2 text-right">Avg time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {results.modes.map((m) => (
              <tr key={m.mode} className={m.mrr === best ? "bg-indigo-50/50" : undefined}>
                <td className="px-3 py-2 font-medium text-slate-800">
                  {MODE_LABELS[m.mode] ?? m.mode}
                  {m.mode === "hybrid_rerank" && <span className="ml-1.5 text-[11px] font-normal text-slate-500">(used for answers)</span>}
                </td>
                <td className="px-3 py-2 text-right">{(m.recall_at_1 * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 text-right">{(m.recall_at_5 * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 text-right">{(m.recall_at_10 * 100).toFixed(0)}%</td>
                <td className="px-3 py-2 text-right">{m.mrr.toFixed(3)}</td>
                <td className="px-3 py-2 text-right text-slate-500">{m.avg_ms.toLocaleString()} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {results.threshold && (
        <p className="text-[12.5px] text-slate-600">
          Relevance threshold {results.threshold.value}: refuses {results.threshold.unanswerable_refused}/{results.threshold.unanswerable}{" "}
          unanswerable questions and wrongly refuses {results.threshold.answerable_refused}/{results.threshold.answerable} answerable ones.
        </p>
      )}
    </Section>
  );
}
