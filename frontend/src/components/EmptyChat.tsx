import { Network } from "lucide-react";

const SUGGESTIONS = [
  "How does SourceTrail combine vector and keyword search?",
  "Why do I get fewer results after creating an IVFFlat index?",
  "How do I make a field in a Pydantic model optional?",
  "Which PostgreSQL index is best for full-text search?",
];

/** First screen of the chat: what this is, plus example questions to click. */
export function EmptyChat({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="mx-auto flex max-w-2xl flex-1 flex-col items-center justify-center gap-6 px-2 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-200 bg-gradient-to-tr from-indigo-50 to-indigo-100 text-indigo-600">
        <Network className="h-6 w-6" aria-hidden />
      </div>
      <div className="space-y-2">
        <h1 className="font-heading text-xl font-bold text-slate-900 sm:text-2xl">Ask your documents anything</h1>
        <p className="text-[14px] leading-relaxed text-slate-600">
          Answers come from the demo collection (FastAPI &amp; pgvector docs, a PDF and a CSV) and anything you upload —
          with every claim linked to the exact passage it came from.
        </p>
      </div>
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onPick(question)}
            className="rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-left text-[13px] text-slate-700 shadow-2xs transition-colors hover:border-indigo-300 hover:bg-indigo-50/40"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
