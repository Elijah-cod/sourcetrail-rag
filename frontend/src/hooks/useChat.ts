"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, askQuestionStream, type Stage } from "@/lib/api";
import type { Mode, QueryResult } from "@/lib/types";

export type UserMessage = { id: number; role: "user"; text: string; sentAt: number };
export type AssistantMessage = {
  id: number;
  role: "assistant";
  question: string;      // what the visitor typed (shown in the chat)
  query: string;         // what was actually searched (usually the same, see ask())
  status: "loading" | "done" | "error";
  startedAt?: number;    // while loading: when the question was sent (for the elapsed time)
  stage?: Stage;         // while loading: what the server is doing now
  result?: QueryResult;
  error?: string;
};
export type Message = UserMessage | AssistantMessage;

export type Settings = { mode: Mode; topK: number };

const STOPPED = "Stopped. Ask again whenever you're ready.";

/** The conversation: the list of messages, asking a question, and the retrieval settings. */
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [settings, setSettings] = useState<Settings>({ mode: "hybrid_rerank", topK: 6 });
  const nextId = useRef(1);
  // One per answer being prepared, so "Stop" can cancel it.
  const running = useRef(new Map<number, AbortController>());

  /** Send a question, with a way to stop it; an abort ends as `null`. */
  const run = useCallback(
    async (answerId: number, query: string, onStage: (stage: Stage) => void) => {
      const controller = new AbortController();
      running.current.set(answerId, controller);
      try {
        return await askQuestionStream(query, settings.mode, settings.topK, onStage, controller.signal);
      } catch (error) {
        if (controller.signal.aborted) return null;
        throw error;
      } finally {
        running.current.delete(answerId);
      }
    },
    [settings],
  );

  /** `query` lets the page search for something more specific than what was typed:
   *  "Summarise https://…" is shown as typed but searched as "Summarise <page title>". */
  const ask = useCallback(
    async (question: string, query: string = question) => {
      const answerId = nextId.current + 1;
      nextId.current += 2;
      // Show the question and a "thinking…" placeholder immediately, before the server answers.
      setMessages((list) => [
        ...list,
        { id: answerId - 1, role: "user", text: question, sentAt: Date.now() },
        { id: answerId, role: "assistant", question, query, status: "loading", startedAt: Date.now() },
      ]);

      const finish = (changes: Partial<AssistantMessage>) =>
        setMessages((list) => list.map((m) => (m.id === answerId && m.role === "assistant" ? { ...m, ...changes } : m)));

      try {
        const result = await run(answerId, query, (stage) => finish({ stage }));
        if (result === null) {
          finish({ status: "error", stage: undefined, error: STOPPED });
          return null;
        }
        finish({ status: "done", stage: undefined, result });
        return answerId;
      } catch (error) {
        let message = error instanceof Error ? error.message : "Something went wrong.";
        if (error instanceof ApiError && error.status === 429 && error.retryAfter) {
          message = `You're asking quickly — please wait ${error.retryAfter} seconds and try again.`;
        }
        finish({ status: "error", error: message });
        return null;
      }
    },
    [run],
  );

  /** Ask the same question again (e.g. after changing settings), replacing that answer in place. */
  const regenerate = useCallback(
    async (answerId: number) => {
      const target = messages.find((m) => m.id === answerId && m.role === "assistant") as AssistantMessage | undefined;
      if (!target) return;
      const update = (changes: Partial<AssistantMessage>) =>
        setMessages((list) => list.map((m) => (m.id === answerId && m.role === "assistant" ? { ...m, ...changes } : m)));
      update({ status: "loading", stage: undefined, result: undefined, error: undefined, startedAt: Date.now() });
      try {
        const result = await run(answerId, target.query, (stage) => update({ stage }));
        update(result === null ? { status: "error", stage: undefined, error: STOPPED } : { status: "done", stage: undefined, result });
      } catch (error) {
        update({ status: "error", error: error instanceof Error ? error.message : "Something went wrong." });
      }
    },
    [messages, run],
  );

  /** Stop waiting for an answer. The server finishes its current step, but nothing more is shown. */
  const stop = useCallback((answerId: number) => running.current.get(answerId)?.abort(), []);

  const clear = useCallback(() => setMessages([]), []);
  const loading = messages.some((m) => m.role === "assistant" && m.status === "loading");

  return { messages, ask, regenerate, stop, clear, loading, settings, setSettings };
}
