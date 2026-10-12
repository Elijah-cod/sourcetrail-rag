"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

/** "connecting" = first check under way; "starting" = it's taking long enough that the server
 *  is probably starting up (a free server sleeps when idle and loads its models on waking). */
export type Health = "connecting" | "starting" | "online" | "offline";

const STARTING_AFTER_MS = 2_000;

/** Asks the backend "are you OK?" now and every 30 seconds. */
export function useHealth(intervalMs = 30_000) {
  const [health, setHealth] = useState<Health>("connecting");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      // Only a slow answer means "starting"; a quick one never flashes the label.
      const slow = setTimeout(() => {
        if (!cancelled) setHealth((now) => (now === "online" ? now : "starting"));
      }, STARTING_AFTER_MS);
      const ok = await checkHealth();
      clearTimeout(slow);
      if (!cancelled) setHealth(ok ? "online" : "offline");
    };
    void check();
    const timer = setInterval(check, intervalMs);
    return () => {
      // Cleanup: runs when the component goes away, so we never update a dead component.
      cancelled = true;
      clearInterval(timer);
    };
  }, [intervalMs]);

  return health;
}
