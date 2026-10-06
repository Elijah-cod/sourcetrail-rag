"use client";

import { AlertCircle, Check } from "lucide-react";
import { useCallback, useRef, useState } from "react";

export type ToastKind = "success" | "error";
type ToastState = { message: string; kind: ToastKind } | null;

/** A tiny notification system: call show("Saved!") and a toast appears for a few seconds. */
export function useToast() {
  const [toast, setToast] = useState<ToastState>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((message: string, kind: ToastKind = "success") => {
    if (timer.current) clearTimeout(timer.current);
    setToast({ message, kind });
    timer.current = setTimeout(() => setToast(null), kind === "error" ? 5000 : 2500);
  }, []);

  return { toast, show };
}

export function Toast({ toast }: { toast: ToastState }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 left-1/2 z-[60] flex max-w-[calc(100vw-2rem)] -translate-x-1/2 items-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-medium text-white shadow-xl transition-opacity duration-200 sm:left-auto sm:right-6 sm:translate-x-0 ${
        toast ? "opacity-100" : "pointer-events-none opacity-0"
      } ${toast?.kind === "error" ? "border-rose-700 bg-rose-600" : "border-slate-800 bg-slate-900"}`}
    >
      {toast?.kind === "error" ? (
        <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
      ) : (
        <Check className="h-4 w-4 shrink-0 text-emerald-400" aria-hidden />
      )}
      <span>{toast?.message}</span>
    </div>
  );
}
