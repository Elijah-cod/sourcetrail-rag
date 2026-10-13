"use client";

import { AlertTriangle, ChevronDown, ChevronRight, Download, Loader2, LogOut, RefreshCw } from "lucide-react";
import { Fragment, useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { BenchmarksView } from "@/components/BenchmarksView";
import { LogoMark } from "@/components/Logo";
import { MODE_LABELS } from "@/components/SettingsPopover";
import { formatMs, StageTimings } from "@/components/admin/StageTimings";
import {
  adminExportUrl,
  adminLogin,
  adminLogout,
  adminSession,
  ApiError,
  getAdminOverview,
  getIngestEvents,
  getQueryEvents,
} from "@/lib/api";
import type { AdminOverview, QueryEvent } from "@/lib/types";

// The admin area: not linked from the app, and every request behind it needs the session cookie
// the server sets after the password. This page only decides what to show; the server decides access.

type Section = "overview" | "benchmarks" | "queries" | "ingestion";
const SECTIONS: { id: Section; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "queries", label: "Query performance" },
  { id: "ingestion", label: "Ingestion health" },
];
const PERIODS = [1, 7];

const when = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const stamp = (iso: string | null | undefined) => (iso ? when.format(new Date(iso)) : "—");
const ms = (value: number | null | undefined) => (value == null ? "—" : formatMs(value));

export default function AdminPage() {
  const [state, setState] = useState<"checking" | "signed-out" | "signed-in">("checking");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    adminSession()
      .then(() => setState("signed-in"))
      .catch(() => setState("signed-out"));
  }, []);

  /** Any 401 from a data call: back to the password, with the server's reason ("expired"…). */
  const onUnauthorized = useCallback((error: unknown) => {
    if (error instanceof ApiError && error.status === 401) {
      setNotice(error.message === "Sign in to continue." ? null : error.message);
      setState("signed-out");
      return true;
    }
    return false;
  }, []);

  if (state === "checking") {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-surface">
        <Loader2 className="h-5 w-5 animate-spin text-ink-400" aria-label="Loading" />
      </main>
    );
  }
  if (state === "signed-out") {
    return <SignIn notice={notice} onSignedIn={() => { setNotice(null); setState("signed-in"); }} />;
  }
  return <Dashboard onUnauthorized={onUnauthorized} onSignedOut={() => setState("signed-out")} />;
}

// ---------- sign in ----------

function SignIn({ notice, onSignedIn }: { notice: string | null; onSignedIn: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await adminLogin(password);
      setPassword("");
      onSignedIn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That didn't work. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const message = error ?? notice;
  return (
    <main className="flex min-h-dvh items-center justify-center bg-surface px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-ink-200 bg-raised p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <LogoMark className="h-8 w-8" />
          <h1 className="font-heading text-lg font-bold text-ink-900">SourceTrail admin</h1>
        </div>
        <label htmlFor="admin-password" className="mt-6 block text-[13px] font-semibold text-ink-700">
          Password
        </label>
        <input
          id="admin-password"
          type="password"
          autoComplete="current-password"
          autoFocus
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={message ? "admin-message" : undefined}
          className="mt-1.5 h-11 w-full rounded-lg border border-ink-200 bg-surface px-3 text-[14px] text-ink-900 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
        />
        {message && (
          <p id="admin-message" role="alert" className="mt-3 text-[13px] text-danger-700">
            {message}
          </p>
        )}
        <button
          type="submit"
          disabled={busy || !password}
          className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-[14px] font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-60"
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          Sign in
        </button>
      </form>
    </main>
  );
}

// ---------- signed in ----------

function Dashboard({ onUnauthorized, onSignedOut }: { onUnauthorized: (e: unknown) => boolean; onSignedOut: () => void }) {
  const [section, setSection] = useState<Section>("overview");
  const [days, setDays] = useState(1);

  const signOut = async () => {
    await adminLogout().catch(() => undefined);
    onSignedOut();
  };

  return (
    <div className="min-h-dvh bg-surface">
      <header className="border-b border-ink-200 bg-raised">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-8">
          <div className="flex items-center gap-2">
            <LogoMark className="h-7 w-7" />
            <span className="font-heading text-[15px] font-bold text-ink-900">SourceTrail admin</span>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-[12.5px] text-ink-600">
              Period
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="h-9 rounded-lg border border-ink-200 bg-surface px-2 text-[12.5px] text-ink-800"
              >
                {PERIODS.map((d) => (
                  <option key={d} value={d}>{d === 1 ? "Last 24 hours" : `Last ${d} days`}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={signOut}
              className="flex h-9 items-center gap-1.5 rounded-lg border border-ink-200 px-3 text-[12.5px] font-semibold text-ink-700 hover:bg-ink-50"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden />
              Log out
            </button>
          </div>
        </div>
        <nav aria-label="Admin sections" className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4 md:px-8">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSection(s.id)}
              aria-current={section === s.id ? "page" : undefined}
              className={`shrink-0 border-b-2 px-3 py-2.5 text-[13px] font-semibold transition-colors ${
                section === s.id ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500 hover:text-ink-800"
              }`}
            >
              {s.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {section === "overview" && <Overview days={days} onUnauthorized={onUnauthorized} />}
        {section === "benchmarks" && (
          <>
            <BenchmarksView />
            <div className="mx-auto max-w-5xl px-4 pb-8 md:px-8">
              <ExportLink table="benchmarks" days={days} />
            </div>
          </>
        )}
        {section === "queries" && <Queries days={days} onUnauthorized={onUnauthorized} />}
        {section === "ingestion" && <Ingestion days={days} onUnauthorized={onUnauthorized} />}
      </main>
    </div>
  );
}

/** Loads one admin endpoint for the chosen period; a 401 signs out. */
function useAdminData<T>(load: (days: number) => Promise<T>, days: number, onUnauthorized: (e: unknown) => boolean) {
  const [result, setResult] = useState<{ key: string; data: T | null; error: string | null } | null>(null);
  const [reloads, setReloads] = useState(0);
  const key = `${days}:${reloads}`;

  useEffect(() => {
    let live = true;
    load(days)
      .then((data) => live && setResult({ key, data, error: null }))
      .catch((e) => {
        if (live && !onUnauthorized(e)) {
          const error = e instanceof ApiError ? e.message : "That didn't work. Try again.";
          setResult((r) => ({ key, data: r?.data ?? null, error }));
        }
      });
    return () => {
      live = false;
    };
  }, [load, days, key, onUnauthorized]);

  return {
    data: result?.data ?? null,
    error: result?.error ?? null,
    loading: result?.key !== key,
    reload: () => setReloads((n) => n + 1),
  };
}

function Page({ title, subtitle, loading, onReload, actions, error, children }: {
  title: string;
  subtitle: string;
  loading: boolean;
  onReload: () => void;
  actions?: ReactNode;
  error: string | null;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 py-6 md:px-8 md:py-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-heading text-xl font-bold text-ink-900">{title}</h1>
          <p className="mt-1 max-w-2xl text-[13px] text-ink-600">{subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {actions}
          <button
            type="button"
            onClick={onReload}
            disabled={loading}
            className="flex h-11 items-center gap-1.5 rounded-lg border border-ink-200 bg-raised px-3 text-[12.5px] font-semibold text-ink-700 shadow-2xs hover:bg-ink-50 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden />}
            Reload
          </button>
        </div>
      </div>
      {error && (
        <p className="flex items-start gap-2 rounded-xl border border-danger-200 bg-danger-50 px-4 py-3 text-[13px] text-danger-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {error}
        </p>
      )}
      {children}
    </div>
  );
}

function ExportLink({ table, days }: { table: "queries" | "ingestion" | "benchmarks"; days: number }) {
  return (
    <a
      href={adminExportUrl(table, Math.max(days, 7))}
      className="flex h-11 w-fit items-center gap-1.5 rounded-lg border border-ink-200 bg-raised px-3 text-[12.5px] font-semibold text-ink-700 shadow-2xs hover:bg-ink-50"
    >
      <Download className="h-3.5 w-3.5" aria-hidden />
      Export CSV
    </a>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-dashed border-ink-200 px-4 py-8 text-center text-[13px] text-ink-500">{children}</p>;
}

// ---------- overview ----------

function Overview({ days, onUnauthorized }: { days: number; onUnauthorized: (e: unknown) => boolean }) {
  const { data, error, loading, reload } = useAdminData(getAdminOverview, days, onUnauthorized);
  const problems = data ? problemsIn(data) : [];

  return (
    <Page title="Overview" subtitle="Whether SourceTrail is healthy, and how questions and uploads went in this period."
          loading={loading} onReload={reload} error={error}>
      {data && (
        <>
          <section aria-label="Status" className={`rounded-xl border px-4 py-3 text-[13.5px] ${
            problems.length ? "border-warning-200 bg-warning-50 text-warning-800" : "border-success-200 bg-success-50 text-success-800"}`}>
            {problems.length === 0 ? (
              <p className="font-semibold">Everything looks healthy.</p>
            ) : (
              <>
                <p className="font-semibold">Needs a look:</p>
                <ul className="mt-1 list-disc pl-5">{problems.map((p) => <li key={p}>{p}</li>)}</ul>
              </>
            )}
          </section>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Tile label="Questions" value={String(data.queries.total)} />
            <Tile label="Answered" value={String(data.queries.answered)} />
            <Tile label="Typical answer time" value={ms(data.queries.p50_ms)} note={`95% within ${ms(data.queries.p95_ms)}`} />
            <Tile label="Uploads" value={String(data.ingestion.ok)} note={`${data.ingestion.failed} failed`} />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <Facts title="Service" rows={[
              ["Database", data.service.database === "ok" ? "Connected" : "Not reachable"],
              ["Models", data.service.models],
              ["Answer model", data.service.llm],
              ["Running since", stamp(data.service.started_at)],
              ["Model load", data.service.startup_ms?.ready_ms != null ? ms(data.service.startup_ms.ready_ms) : "—"],
              ["Checked", stamp(data.service.checked_at)],
            ]} />
            <Facts title="Build" rows={[
              ["Version", data.build.version],
              ["Deployment", data.build.revision ?? "—"],
              ["Commit", data.build.commit ?? "—"],
              ["LLM", data.build.llm_model],
              ["Embeddings", data.build.embedding_model],
              ["Reranker", data.build.reranker_model],
            ]} />
            <Facts title="This period" rows={[
              ["No answer in the documents", String(data.queries.refused)],
              ["Answers with a missing part", String(data.queries.missing_parts)],
              ["Errors", String(data.queries.errors)],
              ["Uploads with a warning", String(data.ingestion.warnings)],
              ["Failed admin sign-ins", String(data.failed_logins)],
              ["Benchmarks last run", stamp(data.benchmark_run_at)],
            ]} />
            <Facts title="Retention" rows={[
              ["Documents", `${data.retention.documents_hours} hours after last use`],
              ["Question and upload records", `${data.retention.telemetry_days} days (no question text)`],
              ["Admin sign-in records", `${data.retention.admin_events_days} days`],
            ]} />
          </div>
        </>
      )}
    </Page>
  );
}

function problemsIn(o: AdminOverview): string[] {
  const problems: string[] = [];
  if (o.service.database !== "ok") problems.push("The database is not reachable.");
  if (o.service.llm !== "configured") problems.push("No answer model API key is set, so questions can't be answered.");
  if (o.queries.errors) problems.push(`${o.queries.errors} question${o.queries.errors === 1 ? "" : "s"} ended in an error.`);
  if (o.ingestion.failed) problems.push(`${o.ingestion.failed} upload${o.ingestion.failed === 1 ? "" : "s"} failed.`);
  if (o.failed_logins >= 5) problems.push(`${o.failed_logins} failed admin sign-ins.`);
  return problems;
}

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-ink-200 bg-raised px-4 py-3">
      <p className="text-[12px] text-ink-500">{label}</p>
      <p className="mt-1 font-heading text-xl font-bold tabular-nums text-ink-900">{value}</p>
      {note && <p className="mt-0.5 text-[12px] text-ink-500">{note}</p>}
    </div>
  );
}

function Facts({ title, rows }: { title: string; rows: [string, string][] }) {
  return (
    <section className="rounded-xl border border-ink-200 bg-raised px-4 py-3">
      <h2 className="text-[13px] font-semibold text-ink-800">{title}</h2>
      <dl className="mt-2 grid grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] gap-x-3 gap-y-1.5 text-[13px]">
        {rows.map(([k, v]) => (
          <Fragment key={k}>
            <dt className="text-ink-500">{k}</dt>
            <dd className="break-words text-ink-800">{v}</dd>
          </Fragment>
        ))}
      </dl>
    </section>
  );
}

// ---------- query performance ----------

const STATUS_LABELS: Record<QueryEvent["status"], string> = {
  answered: "Answered",
  not_found: "Not in documents",
  llm_unavailable: "Answer model unavailable",
  error: "Error",
};

function Queries({ days, onUnauthorized }: { days: number; onUnauthorized: (e: unknown) => boolean }) {
  const { data, error, loading, reload } = useAdminData(getQueryEvents, days, onUnauthorized);
  const [open, setOpen] = useState<string | null>(null);

  return (
    <Page title="Query performance" subtitle="One row per question: outcome, sources and time per stage. Question text is never stored."
          loading={loading} onReload={reload} error={error} actions={<ExportLink table="queries" days={days} />}>
      {data && data.length === 0 && <Empty>No questions in this period.</Empty>}
      {data && data.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-ink-200 bg-raised">
          <table className="w-full min-w-[640px] text-left text-[13px]">
            <thead className="border-b border-ink-200 text-[12px] text-ink-500">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Time</th>
                <th scope="col" className="px-3 py-2 font-semibold">Outcome</th>
                <th scope="col" className="px-3 py-2 font-semibold">Mode</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Parts</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Sources</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.map((q) => {
                const expanded = open === q.id;
                return (
                  <Fragment key={q.id}>
                    <tr className="border-b border-ink-100 last:border-0">
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => setOpen(expanded ? null : q.id)}
                          aria-expanded={expanded}
                          aria-label={`Stage times for the question at ${stamp(q.created_at)}, id ${q.id.slice(0, 8)}`}
                          className="flex items-center gap-1 text-left text-ink-800 hover:text-brand-700"
                        >
                          {expanded ? <ChevronDown className="h-3.5 w-3.5" aria-hidden /> : <ChevronRight className="h-3.5 w-3.5" aria-hidden />}
                          {stamp(q.created_at)}
                        </button>
                      </td>
                      <td className="px-3 py-2">
                        <span className={q.status === "answered" ? (q.missing ? "text-warning-700" : "text-ink-800") : q.status === "not_found" ? "text-ink-600" : "text-danger-700"}>
                          {STATUS_LABELS[q.status] ?? q.status}
                          {q.status === "answered" && q.missing > 0 && ` (${q.missing} part${q.missing === 1 ? "" : "s"} missing)`}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-ink-600">{MODE_LABELS[q.mode] ?? q.mode}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{q.parts || 1}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{q.sources} / {q.citations} cited</td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums">{ms(q.total_ms)}</td>
                    </tr>
                    {expanded && (
                      <tr className="border-b border-ink-100 bg-ink-50/50">
                        <td colSpan={6} className="px-3 py-3">
                          <StageTimings timings={q.timings ?? {}} />
                          <p className="mt-2 font-mono text-[11.5px] text-ink-400">id {q.id}</p>
                          {q.error && <p className="mt-1 text-[12.5px] text-danger-700">{q.error}</p>}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Page>
  );
}

// ---------- ingestion health ----------

function Ingestion({ days, onUnauthorized }: { days: number; onUnauthorized: (e: unknown) => boolean }) {
  const { data, error, loading, reload } = useAdminData(getIngestEvents, days, onUnauthorized);

  return (
    <Page title="Ingestion health" subtitle="One row per upload or web page: whether it worked, its size and any warning. Contents are never stored here."
          loading={loading} onReload={reload} error={error} actions={<ExportLink table="ingestion" days={days} />}>
      {data && data.length === 0 && <Empty>No uploads in this period.</Empty>}
      {data && data.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-ink-200 bg-raised">
          <table className="w-full min-w-[640px] text-left text-[13px]">
            <thead className="border-b border-ink-200 text-[12px] text-ink-500">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Time</th>
                <th scope="col" className="px-3 py-2 font-semibold">Type</th>
                <th scope="col" className="px-3 py-2 font-semibold">Result</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Chunks</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Characters</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Took</th>
                <th scope="col" className="px-3 py-2 font-semibold">Deleted after</th>
              </tr>
            </thead>
            <tbody>
              {data.map((e) => (
                <tr key={e.id} className="border-b border-ink-100 align-top last:border-0">
                  <td className="px-3 py-2 text-ink-800">{stamp(e.created_at)}</td>
                  <td className="px-3 py-2 uppercase text-ink-600">{e.source_type}</td>
                  <td className="px-3 py-2">
                    {e.ok ? (
                      <>
                        <span className="text-success-700">Added</span>
                        {e.warning && <p className="mt-0.5 max-w-xs text-[12px] text-warning-700">{e.warning}</p>}
                      </>
                    ) : (
                      <span className="text-danger-700">Failed{e.error ? `: ${e.error}` : ""}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{e.chunks}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{e.characters.toLocaleString()}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{ms(e.duration_ms)}</td>
                  <td className="px-3 py-2 text-ink-600">{e.ok ? stamp(e.expires_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Page>
  );
}
