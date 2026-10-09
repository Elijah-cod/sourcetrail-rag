"use client";

import { useEffect, useEffectEvent, useRef } from "react";
import { useMediaQuery } from "./useMediaQuery";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Below the lg breakpoint the side panels slide over the page, so they must behave like a
 *  modal dialog: focus moves in when they open (to the element marked `data-autofocus`),
 *  Tab stays inside, Escape closes, and focus goes back to whatever opened them.
 *  On lg and up they are ordinary columns and none of this applies.
 *  Returns a ref for the panel and whether it is currently acting as a modal. */
export function useModalDrawer<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const panel = useRef<T>(null);
  const modal = useMediaQuery("(max-width: 1023.98px)");
  const close = useEffectEvent(onClose);

  useEffect(() => {
    if (!open || !modal || !panel.current) return;
    const box = panel.current;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    // Wait for the slide-in to start so the panel is visible and can take focus.
    const frame = requestAnimationFrame(() => box.querySelector<HTMLElement>("[data-autofocus]")?.focus());

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      } else if (e.key === "Tab") {
        const items = [...box.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.getClientRects().length > 0);
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        const inside = box.contains(document.activeElement);
        if (e.shiftKey && (document.activeElement === first || !inside)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && (document.activeElement === last || !inside)) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKey);
      if (opener?.isConnected) opener.focus();
    };
  }, [open, modal]);

  return { panel, modal };
}
