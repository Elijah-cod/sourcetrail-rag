"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

/** What the sidebar says about availability. "connecting" only before the first answer. */
export type Health = "connecting" | "ready" | "busy" | "reconnecting" | "unavailable";

const RETRY_MS = 10_000;          // check again sooner while something is wrong

/** Asks the backend "can you answer?" now and every 30 seconds (every 10 while it can't). */
export function useHealth(intervalMs = 30_000) {
  const [health, setHealth] = useState<Health>("connecting");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    const check = async () => {
      const status = await checkHealth();
      if (cancelled) return;
      // One missed check is usually a sleeping server waking up; two in a row is an outage.
      failures = status === "unreachable" ? failures + 1 : 0;
      setHealth(status === "unreachable" ? (failures >= 2 ? "unavailable" : "reconnecting") : status);
      timer = setTimeout(check, status === "ready" || status === "busy" ? intervalMs : RETRY_MS);
    };
    void check();
    return () => {
      // Cleanup: runs when the component goes away, so we never update a dead component.
      cancelled = true;
      clearTimeout(timer);
    };
  }, [intervalMs]);

  return health;
}
