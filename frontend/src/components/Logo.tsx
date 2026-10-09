import { Network } from "lucide-react";

/** The SourceTrail wordmark: icon tile + name + RAG badge. */
export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
        <Network className="h-4 w-4 text-white" aria-hidden />
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="font-heading text-[15px] font-bold tracking-tight text-slate-900">SourceTrail</span>
        <span className="rounded border border-indigo-100/80 bg-indigo-50 px-1.5 py-0.5 text-[12px] font-semibold text-indigo-600">
          RAG
        </span>
      </div>
    </div>
  );
}
