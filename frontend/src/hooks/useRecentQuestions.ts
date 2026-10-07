"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";

/*
 * The last few questions you asked, remembered in this browser (localStorage).
 *
 * Why useSyncExternalStore? The page is pre-rendered at build time, where there is no
 * localStorage. This hook lets React render "no recent questions" on the server and then
 * switch to the stored list in the browser without a hydration mismatch.
 */

const KEY = "sourcetrail:recent-questions";
const MAX = 6;
const CHANGED = "sourcetrail:recent-changed";   // our own event, so this tab updates too

function read(): string {
  try {
    return localStorage.getItem(KEY) ?? "[]";
  } catch {
    return "[]";        // private mode / blocked storage: just behave as if empty
  }
}

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);     // changes from other tabs
  window.addEventListener(CHANGED, onChange);       // changes from this tab
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(CHANGED, onChange);
  };
}

export function useRecentQuestions() {
  // Returns the raw JSON string: strings compare by value, so React only re-renders on real changes.
  const raw = useSyncExternalStore(subscribe, read, () => "[]");
  const questions = useMemo<string[]>(() => {
    try {
      const parsed: unknown = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter((q): q is string => typeof q === "string") : [];
    } catch {
      return [];
    }
  }, [raw]);

  const remember = useCallback((question: string) => {
    try {
      const current: string[] = JSON.parse(read());
      const next = [question, ...current.filter((q) => q !== question)].slice(0, MAX);
      localStorage.setItem(KEY, JSON.stringify(next));
      window.dispatchEvent(new Event(CHANGED));
    } catch {
      /* storage unavailable: nothing to remember */
    }
  }, []);

  return { questions, remember };
}
