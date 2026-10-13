"use client";

import { BookOpen, X } from "lucide-react";
import type { ReactNode } from "react";
import { useModalDrawer } from "@/hooks/useModalDrawer";

type Props = {
  open: boolean;
  onClose: () => void;
  children?: ReactNode;
  footer?: ReactNode;
};

/**
 * Right-hand "Referenced Sources" panel.
 * - lg and up: a column next to the chat (hidden when closed).
 * - below lg: slides in over the chat as a modal dialog; on phones a sheet over the lower 70%.
 */
export function SourcesPanel({ open, onClose, children, footer }: Props) {
  const { panel, modal } = useModalDrawer<HTMLDivElement>(open, onClose);
  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-ink-900/30 transition-opacity lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden
      />
      <div
        ref={panel}
        // Phones: a sheet over the lower part of the screen, so the answer stays in view above it.
        className={`fixed inset-x-0 bottom-0 z-50 flex h-[70dvh] flex-col justify-between overflow-hidden rounded-t-2xl border-t border-ink-200 bg-raised shadow-xs transition-[transform,visibility] duration-200 sm:inset-x-auto sm:inset-y-0 sm:right-0 sm:h-auto sm:w-96 sm:rounded-none sm:border-t-0 sm:border-l lg:static lg:z-auto lg:shrink-0 lg:translate-x-0 lg:translate-y-0 ${
          open ? "translate-y-0 sm:translate-x-0" : "invisible translate-y-full sm:translate-x-full sm:translate-y-0 lg:hidden"
        }`}
        id="sources-panel"
        {...(modal ? { role: "dialog", "aria-modal": true, "aria-labelledby": "sources-panel-title" } : { role: "complementary", "aria-label": "Referenced sources" })}
        inert={modal && !open}
      >
        <div className="flex h-14 items-center justify-between border-b border-ink-200 bg-raised px-4">
          <div className="flex items-center gap-2">
            <BookOpen className="h-[18px] w-[18px] text-brand-600" aria-hidden />
            <h2 id="sources-panel-title" className="font-heading text-[13.5px] font-bold text-ink-900">Referenced Sources</h2>
          </div>
          <button type="button" onClick={onClose} data-autofocus className="flex h-11 w-11 items-center justify-center rounded-lg text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-700" aria-label="Close sources panel">
            <X className="h-[18px] w-[18px]" />
          </button>
        </div>
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-ink-50/50 p-4">
          {children ?? (
            <p className="mt-10 text-center text-[13px] leading-relaxed text-ink-500">
              Ask a question and the passages behind the answer will appear here.
              <br />
              Click any <span className="font-mono font-semibold text-brand-600">[1]</span> in an answer to inspect it.
            </p>
          )}
        </div>
        {footer && <div className="flex items-center justify-between border-t border-ink-200 bg-raised p-3 text-xs text-ink-500">{footer}</div>}
      </div>
    </>
  );
}
