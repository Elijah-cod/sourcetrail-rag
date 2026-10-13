import { AlertTriangle, CheckCircle2, Loader2, X } from "lucide-react";
import type { UploadItem } from "@/hooks/useDocuments";

type Props = {
  uploads: UploadItem[];
  onDismiss: (id: number) => void;
};

/** Rows for the Documents view: files still processing, and failures with their reason. */
export function UploadRows({ uploads, onDismiss }: Props) {
  // Finished uploads appear in the document list itself, so only show the rest here
  // (and finished ones that came with a warning, such as very little text read).
  const visible = uploads.filter((u) => u.status !== "done" || u.message);
  if (visible.length === 0) return null;
  return (
    <ul className="flex flex-col gap-2" aria-live="polite">
      {visible.map((u) =>
        u.status === "processing" ? (
          <li key={u.id} className="flex items-center gap-3 rounded-xl border border-brand-200 bg-brand-50/60 p-3">
            <Loader2 className="h-5 w-5 shrink-0 animate-spin text-brand-600" aria-hidden />
            <div className="min-w-0">
              <p className="truncate text-[13px] font-semibold text-ink-900">{u.name}</p>
              <p className="text-[13px] text-ink-600">
                {u.kind === "link"
                  ? "Fetching the page and indexing its text…"
                  : "Reading, splitting and indexing… large PDFs can take a minute."}
              </p>
            </div>
          </li>
        ) : u.status === "done" ? (
          <li key={u.id} className="flex items-start gap-3 rounded-xl border border-warning-200 bg-warning-50 p-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning-600" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold text-ink-900">
                {u.name} <span className="font-normal text-ink-600">· added, {u.detail}</span>
              </p>
              <p className="text-[12px] text-warning-800">{u.message}</p>
            </div>
            <button type="button" onClick={() => onDismiss(u.id)} className="-my-2 -mr-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-warning-600 hover:bg-warning-100 hover:text-warning-800" aria-label={`Dismiss ${u.name}`}>
              <X className="h-4 w-4" />
            </button>
          </li>
        ) : (
          <li key={u.id} className="flex items-start gap-3 rounded-xl border border-danger-200 bg-danger-50 p-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-danger-600" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-semibold text-ink-900">{u.name}</p>
              <p className="text-[12px] text-danger-700">{u.message}</p>
            </div>
            <button type="button" onClick={() => onDismiss(u.id)} className="-my-2 -mr-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-danger-500 hover:bg-danger-100 hover:text-danger-700" aria-label={`Dismiss ${u.name}`}>
              <X className="h-4 w-4" />
            </button>
          </li>
        ),
      )}
    </ul>
  );
}

/** Small chips above the question box, so files and links added from the chat are visible there.
 *  Hovering a failed chip shows why; clicking any chip opens the Documents view. */
export function UploadChips({ uploads, onDismiss, onOpen }: Props & { onOpen: () => void }) {
  if (uploads.length === 0) return null;
  const recent = uploads.slice(-4);
  // Failure reasons are written out (not just in a tooltip) so they're readable on phones too.
  const problems = recent.filter((u) => u.message);
  return (
    <div className="mb-2" aria-live="polite">
    <div className="flex flex-wrap gap-2">
      {recent.map((u) => {
        const warned = u.status === "done" && Boolean(u.message);
        const style =
          u.status === "processing"
            ? "border-brand-200 bg-brand-50 text-brand-700"
            : warned
              ? "border-warning-200 bg-warning-50 text-warning-800"
              : u.status === "done"
                ? "border-success-200 bg-success-50 text-success-800"
                : "border-danger-200 bg-danger-50 text-danger-700";
        const Icon = u.status === "processing" ? Loader2 : u.status === "done" && !warned ? CheckCircle2 : AlertTriangle;
        return (
          <span key={u.id} className={`inline-flex max-w-full items-center gap-1 rounded-md border pl-2 text-[13px] font-medium ${style}`}>
            <button type="button" onClick={onOpen} className="flex min-h-8 min-w-0 items-center gap-1.5" title={u.message ?? u.detail ?? "Open Documents"}>
              <Icon className={`h-3.5 w-3.5 shrink-0 ${u.status === "processing" ? "animate-spin" : ""}`} aria-hidden />
              <span className="max-w-[180px] truncate">{u.name}</span>
              {u.status === "processing" && <span className="opacity-70">· {u.kind === "link" ? "fetching…" : "indexing…"}</span>}
              {u.status === "done" && <span className="opacity-70">· added{u.detail ? `, ${u.detail.split(",")[0]}` : ""}</span>}
              {u.status === "error" && u.kind !== "notice" && <span className="opacity-80">· failed</span>}
            </button>
            {u.status !== "processing" && (
              <button type="button" onClick={() => onDismiss(u.id)} className="flex h-8 w-8 items-center justify-center opacity-60 hover:opacity-100" aria-label={`Dismiss ${u.name}`}>
                <X className="h-3 w-3" />
              </button>
            )}
          </span>
        );
      })}
    </div>
    {problems.map((u) => (
      <p key={u.id} className={`mt-1 text-[13px] ${u.status === "done" ? "text-warning-800" : "text-danger-700"}`}>
        {u.message!.startsWith(u.name) ? u.message : (
          <>
            <span className="font-semibold">{u.name}:</span> {u.message}
          </>
        )}
      </p>
    ))}
    </div>
  );
}
