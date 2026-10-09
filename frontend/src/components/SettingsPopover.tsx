"use client";

import { ChevronDown, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Settings } from "@/hooks/useChat";
import type { Mode } from "@/lib/types";

export const MODE_LABELS: Record<Mode, string> = {
  hybrid_rerank: "Hybrid + rerank",
  hybrid: "Hybrid",
  vector: "Vector only",
  keyword: "Keyword only",
};

const MODE_HELP: Record<Mode, string> = {
  hybrid_rerank: "Best quality: both searches, then a cross-encoder re-scores the top results (~1 s slower).",
  hybrid: "Vector + keyword search merged with Reciprocal Rank Fusion. Fast.",
  vector: "Meaning-based search only (pgvector embeddings).",
  keyword: "Exact-word search only (Postgres full-text).",
};

type Props = { settings: Settings; onChange: (settings: Settings) => void };

export function SettingsPopover({ settings, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const firstField = useRef<HTMLSelectElement>(null);

  // Closing from inside (Escape or the X) puts focus back on the button; a click elsewhere
  // leaves it where the click put it.
  const closeToTrigger = () => {
    setOpen(false);
    trigger.current?.focus();
  };

  // On open, focus the first setting. Close when clicking outside the popover or pressing Escape.
  useEffect(() => {
    if (!open) return;
    firstField.current?.focus();
    const onClick = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeToTrigger();
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    // Phones: the panel is placed against the whole question box (not this button) so it fits on screen.
    <div className="sm:relative" ref={box}>
      <button
        ref={trigger}
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="retrieval-settings"
        // Below sm only the icons are visible, so the name has to come from here.
        aria-label={`Retrieval settings: ${MODE_LABELS[settings.mode]}`}
        className="flex h-10 items-center gap-1.5 rounded-lg border border-indigo-200/80 bg-indigo-50/70 px-2.5 text-xs font-semibold text-indigo-700 transition-colors hover:bg-indigo-100/80"
      >
        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden />
        <span className="hidden sm:inline">{MODE_LABELS[settings.mode]}</span>
        <ChevronDown className="h-3.5 w-3.5 text-indigo-500" aria-hidden />
      </button>
      {open && (
        <div id="retrieval-settings" role="dialog" aria-labelledby="retrieval-settings-title" className="absolute inset-x-0 bottom-full z-50 mb-2 flex flex-col gap-3 sm:inset-x-auto sm:bottom-12 sm:left-0 sm:mb-0 sm:w-[17rem] rounded-xl border border-slate-200 bg-white p-3 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 pb-1 text-xs font-bold text-slate-800">
            <h2 id="retrieval-settings-title">Retrieval settings</h2>
            <button type="button" onClick={closeToTrigger} className="-my-2 -mr-2 flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close settings">
              <X className="h-4 w-4" />
            </button>
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-[12px] font-medium text-slate-500">Search mode</span>
            <select
              ref={firstField}
              value={settings.mode}
              onChange={(e) => onChange({ ...settings, mode: e.target.value as Mode })}
              className="h-10 rounded-lg border border-slate-200 bg-slate-50 px-2 text-xs text-slate-800 focus:border-indigo-500 focus:outline-none"
            >
              {(Object.keys(MODE_LABELS) as Mode[]).map((mode) => (
                <option key={mode} value={mode}>
                  {MODE_LABELS[mode]}
                </option>
              ))}
            </select>
            <span className="text-[12px] leading-snug text-slate-500">{MODE_HELP[settings.mode]}</span>
          </label>
          <label className="flex flex-col gap-1">
            <span className="flex justify-between text-[12px] font-medium text-slate-500">
              Sources per answer
              <span className="font-mono font-bold text-indigo-600">{settings.topK}</span>
            </span>
            <input
              type="range"
              min={1}
              max={10}
              value={settings.topK}
              onChange={(e) => onChange({ ...settings, topK: Number(e.target.value) })}
              className="h-10 w-full cursor-pointer accent-indigo-600"
            />
          </label>
        </div>
      )}
    </div>
  );
}
