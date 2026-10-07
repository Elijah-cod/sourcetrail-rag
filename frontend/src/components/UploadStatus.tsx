import { AlertTriangle, CheckCircle2, Loader2, X } from "lucide-react";
import type { UploadItem } from "@/hooks/useDocuments";

type Props = {
  uploads: UploadItem[];
  onDismiss: (id: number) => void;
};

/** Rows for the Documents view: files still processing, and failures with their reason. */
export function UploadRows({ uploads, onDismiss }: Props) {
  // Finished uploads appear in the document list itself, so only show the rest here.
  const visible = uploads.filter((u) => u.status !== "done");
  if (visible.length === 0) return null;
  return (
    <ul className="flex flex-col gap-2" aria-live="polite">
      {visible.map((u) =>
        u.status === "processing" ? (
          <li key={u.id} className="flex items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50/60 p-3">
            <Loader2 className="h-5 w-5 shrink-0 animate-spin text-indigo-600" aria-hidden />
            <div className="min-w-0">
              <p className="truncate text-[13px] font-semibold text-slate-900">{u.name}</p>
              <p className="text-[11.5px] text-slate-600">Reading, splitting and indexing… large PDFs can take a minute.</p>
            </div>
          </li>
        ) : (
          <li key={u.id} className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold text-slate-900">{u.name}</p>
              <p className="text-[12px] text-rose-700">{u.message}</p>
            </div>
            <button type="button" onClick={() => onDismiss(u.id)} className="rounded p-1 text-rose-400 hover:bg-rose-100 hover:text-rose-700" aria-label={`Dismiss ${u.name}`}>
              <X className="h-4 w-4" />
            </button>
          </li>
        ),
      )}
    </ul>
  );
}

/** Small chips above the question box, so uploads started from the chat are visible there too. */
export function UploadChips({ uploads, onDismiss, onOpen }: Props & { onOpen: () => void }) {
  if (uploads.length === 0) return null;
  return (
    <div className="mb-2 flex flex-wrap gap-1.5" aria-live="polite">
      {uploads.slice(-4).map((u) => {
        const style =
          u.status === "processing"
            ? "border-indigo-200 bg-indigo-50 text-indigo-700"
            : u.status === "done"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-700";
        const Icon = u.status === "processing" ? Loader2 : u.status === "done" ? CheckCircle2 : AlertTriangle;
        return (
          <span key={u.id} className={`inline-flex max-w-full items-center gap-1 rounded-md border pl-2 text-[11.5px] font-medium ${style}`}>
            <button type="button" onClick={onOpen} className="flex min-w-0 items-center gap-1.5 py-0.5" title={u.message ?? "Open Documents"}>
              <Icon className={`h-3.5 w-3.5 shrink-0 ${u.status === "processing" ? "animate-spin" : ""}`} aria-hidden />
              <span className="max-w-[180px] truncate">{u.name}</span>
              {u.status === "processing" && <span className="opacity-70">· indexing…</span>}
              {u.status === "error" && <span className="opacity-80">· failed</span>}
            </button>
            {u.status !== "processing" && (
              <button type="button" onClick={() => onDismiss(u.id)} className="rounded p-0.5 pr-1 opacity-60 hover:opacity-100" aria-label={`Dismiss ${u.name}`}>
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        );
      })}
    </div>
  );
}
