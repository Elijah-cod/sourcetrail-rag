import { LogoMark } from "./Logo";

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
      <LogoMark className="h-16 w-16" />
      <div className="space-y-2">
        <h1 className="font-heading text-xl font-bold text-ink-900 sm:text-2xl">Ask your documents anything</h1>
        <p className="text-[14px] leading-relaxed text-ink-600">
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
            className="rounded-xl border border-ink-200 bg-raised px-3.5 py-3 text-left text-[13px] text-ink-700 shadow-2xs transition-colors hover:border-brand-300 hover:bg-brand-50/40"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
