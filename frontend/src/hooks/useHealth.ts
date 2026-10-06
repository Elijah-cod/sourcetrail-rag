"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";

/** Asks the backend "are you OK?" now and every 30 seconds. null = not known yet. */
export function useHealth(intervalMs = 30_000) {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const ok = await checkHealth();
      if (!cancelled) setOnline(ok);
    };
    void check();
    const timer = setInterval(check, intervalMs);
    return () => {
      // Cleanup: runs when the component goes away, so we never update a dead component.
      cancelled = true;
      clearInterval(timer);
    };
  }, [intervalMs]);

  return online;
}
