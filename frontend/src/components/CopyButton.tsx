"use client";

import { Check, Copy, X } from "lucide-react";
import { useEffect, useState } from "react";
import { copyText } from "@/lib/clipboard";

type Props = {
  text: () => string;          // a function, so the text is only built when clicked
  label: string;               // what it copies, for screen readers and the tooltip
  children?: React.ReactNode;  // optional visible text, e.g. "Copy passage"
  className?: string;
};

/** A copy button that confirms in place: the icon turns into a tick for a moment.
 *  (No pop-up needed: the feedback appears exactly where you clicked.) */
export function CopyButton({ text, label, children, className }: Props) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  // Go back to the normal icon after 1.5 seconds.
  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 1500);
    return () => clearTimeout(timer);
  }, [state]);

  const Icon = state === "copied" ? Check : state === "failed" ? X : Copy;
  const title = state === "copied" ? "Copied" : state === "failed" ? "Your browser blocked copying" : label;
  return (
    <button
      type="button"
      onClick={async () => setState((await copyText(text())) ? "copied" : "failed")}
      title={title}
      aria-label={title}
      className={className}
    >
      <Icon className={`${children ? "h-3.5 w-3.5" : "h-4 w-4"} ${state === "copied" ? "text-emerald-600" : state === "failed" ? "text-rose-600" : ""}`} aria-hidden />
      {children && <span>{state === "copied" ? "Copied" : children}</span>}
    </button>
  );
}
