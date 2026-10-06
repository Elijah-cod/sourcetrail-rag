import { BookOpen, X } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  children?: ReactNode;
  footer?: ReactNode;
};

/**
 * Right-hand "Referenced Sources" panel.
 * - lg and up: a column next to the chat (hidden when closed).
 * - below lg: slides in over the chat; full width on phones.
 */
export function SourcesPanel({ open, onClose, children, footer }: Props) {
  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-slate-900/30 transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden
      />
      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-full flex-col justify-between overflow-hidden border-l border-slate-200 bg-white shadow-xs transition-transform duration-200 sm:w-96 lg:static lg:z-auto lg:shrink-0 lg:translate-x-0 ${
          open ? "translate-x-0" : "translate-x-full lg:hidden"
        }`}
        aria-label="Referenced sources"
      >
        <div className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
          <div className="flex items-center gap-2">
            <BookOpen className="h-[18px] w-[18px] text-indigo-600" aria-hidden />
            <span className="font-heading text-[13.5px] font-bold text-slate-900">Referenced Sources</span>
          </div>
          <button type="button" onClick={onClose} className="rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700" aria-label="Close sources panel">
            <X className="h-[18px] w-[18px]" />
          </button>
        </div>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-slate-50/50 p-4">
          {children ?? (
            <p className="mt-10 text-center text-[13px] leading-relaxed text-slate-500">
              Ask a question and the passages behind the answer will appear here.
              <br />
              Click any <span className="font-mono font-semibold text-indigo-600">[1]</span> in an answer to inspect it.
            </p>
          )}
        </div>
        {footer && <div className="flex items-center justify-between border-t border-slate-200 bg-white p-3 text-xs text-slate-500">{footer}</div>}
      </aside>
    </>
  );
}
