"use client";

import { AlertTriangle, CalendarRange, RefreshCw, ShieldCheck } from "lucide-react";
import type { Stage } from "@/lib/api";
import { answerWithSources } from "@/lib/clipboard";
import { CopyButton } from "./CopyButton";
import { LogoMark } from "./Logo";
import { useEffect, useRef } from "react";
import type { AssistantMessage, Message } from "@/hooks/useChat";
import { citationColor } from "@/lib/citations";
import { scrollBehavior } from "@/lib/motion";
import type { QueryResult } from "@/lib/types";
import { AnswerText } from "./AnswerText";

type Props = {
  messages: Message[];
  onCite: (answerId: number, n: number, claim?: string) => void;
  active: { answerId: number; n: number; claim?: string } | null;   // the citation open in the sources panel
  onRegenerate: (answerId: number) => void;
  busy: boolean;
};

export function ChatMessages({ messages, onCite, active, onRegenerate, busy }: Props) {
  const end = useRef<HTMLDivElement>(null);

  // Keep the newest message in view whenever the conversation changes.
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: scrollBehavior(), block: "end" });
  }, [messages]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col space-y-7">
      {messages.map((m) =>
        m.role === "user" ? (
          <div key={m.id} className="flex max-w-[85%] items-start gap-3 self-end sm:max-w-2xl">
            <div className="flex flex-col items-end gap-1.5">
              <span className="text-[12px] font-medium text-ink-500">You</span>
              <div className="whitespace-pre-wrap break-words rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-3 text-[14.5px] leading-relaxed text-white shadow-sm shadow-brand-600/15">
                {m.text}
              </div>
            </div>
          </div>
        ) : (
          <AssistantBubble
            key={m.id}
            message={m}
            onCite={(n, claim) => onCite(m.id, n, claim)}
            activeN={active?.answerId === m.id ? active.n : null}
            activeClaim={active?.answerId === m.id ? active.claim : undefined}
            onRegenerate={() => onRegenerate(m.id)}
            busy={busy}
          />
        ),
      )}
      <div ref={end} />
    </div>
  );
}

type BubbleProps = {
  message: AssistantMessage;
  onCite: (n: number, claim?: string) => void;
  activeN: number | null;
  activeClaim?: string;
  onRegenerate: () => void;
  busy: boolean;
};

function AssistantBubble({ message, onCite, activeN, activeClaim, onRegenerate, busy }: BubbleProps) {
  return (
    <div className="flex w-full items-start gap-3 self-start sm:gap-3.5">
      <LogoMark className="hidden h-8 w-8 sm:block" />
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-heading text-[14px] font-bold text-ink-900">SourceTrail</span>
            {message.status === "done" && message.result && <StatusPill result={message.result} onCite={onCite} />}
            {message.result?.filters.year && (
              <span className="inline-flex items-center gap-1 rounded-full border border-ink-200 bg-raised px-2 py-0.5 text-[12px] font-medium text-ink-600">
                <CalendarRange className="h-3 w-3" aria-hidden />
                {message.result.filters.year} documents
              </span>
            )}
          </div>
          {message.status !== "loading" && (
            <div className="-my-2 ml-auto flex items-center">
              {message.result && (
                <CopyButton
                  label="Copy answer with sources"
                  text={() => answerWithSources(message.result!)}
                  className="flex h-10 w-10 items-center justify-center rounded-lg text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-700"
                />
              )}
              <IconButton label="Ask again with the current settings" onClick={onRegenerate} disabled={busy}>
                <RefreshCw className="h-4 w-4" />
              </IconButton>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-ink-200/90 bg-raised p-4 text-[14.5px] leading-relaxed text-ink-800 shadow-sm sm:p-5 md:p-6">
          {message.status === "loading" && <Thinking stage={message.stage} />}
          {message.status === "error" && (
            <p className="flex items-start gap-2 text-danger-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              {message.error}
            </p>
          )}
          {message.status === "done" && message.result && (
            <div className="space-y-4">
              <AnswerText text={message.result.answer} citations={message.result.citations} onCite={onCite} activeN={activeN} activeClaim={activeClaim} />
              <Unverified values={message.result.unverified} />
              <Timings result={message.result} />
              <Referenced result={message.result} onCite={onCite} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Figures the backend couldn't find in any source: may be calculated, may be wrong. */
function Unverified({ values }: { values?: string[] }) {
  if (!values || values.length === 0) return null;
  return (
    <p className="flex items-start gap-2 rounded-lg border border-warning-200 bg-warning-50 px-3 py-2 text-[12.5px] text-warning-800">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>
        Not found in any source, so check before relying on {values.length === 1 ? "it" : "them"} (it may be
        calculated): {values.join(", ")}
      </span>
    </p>
  );
}

/** What the server is doing right now, in words (the stages come from POST /query/stream). */
function stageText(stage?: Stage) {
  switch (stage?.stage) {
    case "parts":
      return `Searching each of the ${stage.count} parts of your question…`;
    case "write":
      return `Writing an answer from ${stage.sources} passage${stage.sources === 1 ? "" : "s"}…`;
    case "check":
      return "Checking the answer against the sources…";
    default:
      return "Searching your documents…";
  }
}

function Thinking({ stage }: { stage?: Stage }) {
  return (
    <div className="flex items-center gap-3 text-[13px] text-ink-500" role="status">
      <span className="flex gap-1" aria-hidden>
        {[0, 150, 300].map((delay) => (
          <span key={delay} className="h-2 w-2 animate-bounce rounded-full motion-reduce:animate-none bg-brand-400" style={{ animationDelay: `${delay}ms` }} />
        ))}
      </span>
      {stageText(stage)}
    </div>
  );
}

function StatusPill({ result, onCite }: { result: QueryResult; onCite: (n: number) => void }) {
  if (result.status === "answered" && result.citations.length > 0) {
    const n = result.citations.length;
    return (
      <button
        type="button"
        onClick={() => onCite(result.citations[0].n)}
        className="tap-target inline-flex items-center gap-1.5 rounded-full border border-success-200 bg-success-50 px-2.5 py-0.5 text-[13px] font-semibold text-success-700 shadow-2xs transition-colors hover:bg-success-100/70"
      >
        <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
        Grounded in {n} source{n === 1 ? "" : "s"}
      </button>
    );
  }
  // "answered" with zero valid citations: the model wrote something but cited nothing we sent.
  const text =
    result.status === "llm_unavailable"
      ? "AI answer unavailable"
      : result.status === "answered"
        ? "Uncited — check the sources"
        : "No supporting sources";
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-warning-200 bg-warning-50 px-2.5 py-0.5 text-[13px] font-semibold text-warning-800">
      <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
      {text}
    </span>
  );
}

/** Real per-stage timings from the backend (replacing the design's sample numbers). */
function Timings({ result }: { result: QueryResult }) {
  const stages = [
    { label: "Search", value: result.timings.search_ms, note: "vector + keyword search" },
    { label: "Rerank", value: result.timings.rerank_ms, note: "cross-encoder reranking" },
    { label: "Answer", value: result.timings.generation_ms, note: "LLM answer and checks" },
  ].filter((s) => s.value !== undefined);
  if (stages.length === 0) return null;
  // One quiet line of figures: useful for debugging, not the point of the answer.
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 border-t border-ink-100 pt-3 text-[13px]">
      {stages.map((s) => (
        <div key={s.label} className="flex items-baseline gap-1.5" title={s.note}>
          <dt className="text-ink-500">{s.label}</dt>
          <dd className="font-mono font-semibold tabular-nums text-ink-800">{formatMs(s.value!)}</dd>
        </div>
      ))}
    </dl>
  );
}

const formatMs = (ms: number) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`);

/** "Referenced:" pills — one per cited document. */
function Referenced({ result, onCite }: { result: QueryResult; onCite: (n: number) => void }) {
  const firstPerDocument = new Map<string, (typeof result.citations)[number]>();
  for (const c of result.citations) if (!firstPerDocument.has(c.document_id)) firstPerDocument.set(c.document_id, c);
  if (firstPerDocument.size === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-1.5 gap-y-3 pt-1">
      <span className="mr-1 text-[13px] font-medium text-ink-500">Referenced:</span>
      {[...firstPerDocument.values()].map((c) => (
        <button
          key={c.document_id}
          type="button"
          onClick={() => onCite(c.n)}
          className="tap-target inline-flex max-w-full items-center gap-1.5 rounded-full border border-ink-200 bg-ink-50 px-2.5 py-1 text-[13px] font-medium text-ink-700 transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
        >
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${citationColor(c.n).dot}`} />
          <span className="truncate">{c.document_title}</span>
        </button>
      ))}
    </div>
  );
}

function IconButton({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="flex h-10 w-10 items-center justify-center rounded-lg text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-700 disabled:opacity-40"
    >
      {children}
    </button>
  );
}
