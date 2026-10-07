"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, askQuestion } from "@/lib/api";
import type { Mode, QueryResult } from "@/lib/types";

export type UserMessage = { id: number; role: "user"; text: string };
export type AssistantMessage = {
  id: number;
  role: "assistant";
  question: string;      // what the visitor typed (shown in the chat)
  query: string;         // what was actually searched (usually the same, see ask())
  status: "loading" | "done" | "error";
  result?: QueryResult;
  error?: string;
};
export type Message = UserMessage | AssistantMessage;

export type Settings = { mode: Mode; topK: number };

/** The conversation: the list of messages, asking a question, and the retrieval settings. */
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [settings, setSettings] = useState<Settings>({ mode: "hybrid_rerank", topK: 6 });
  const nextId = useRef(1);

  /** `query` lets the page search for something more specific than what was typed:
   *  "Summarise https://…" is shown as typed but searched as "Summarise <page title>". */
  const ask = useCallback(
    async (question: string, query: string = question) => {
      const answerId = nextId.current + 1;
      nextId.current += 2;
      // Show the question and a "thinking…" placeholder immediately, before the server answers.
      setMessages((list) => [
        ...list,
        { id: answerId - 1, role: "user", text: question },
        { id: answerId, role: "assistant", question, query, status: "loading" },
      ]);

      const finish = (changes: Partial<AssistantMessage>) =>
        setMessages((list) => list.map((m) => (m.id === answerId && m.role === "assistant" ? { ...m, ...changes } : m)));

      try {
        const result = await askQuestion(query, settings.mode, settings.topK);
        finish({ status: "done", result });
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
    [settings],
  );

  /** Ask the same question again (e.g. after changing settings), replacing that answer in place. */
  const regenerate = useCallback(
    async (answerId: number) => {
      const target = messages.find((m) => m.id === answerId && m.role === "assistant") as AssistantMessage | undefined;
      if (!target) return;
      const update = (changes: Partial<AssistantMessage>) =>
        setMessages((list) => list.map((m) => (m.id === answerId && m.role === "assistant" ? { ...m, ...changes } : m)));
      update({ status: "loading", result: undefined, error: undefined });
      try {
        update({ status: "done", result: await askQuestion(target.query, settings.mode, settings.topK) });
      } catch (error) {
        update({ status: "error", error: error instanceof Error ? error.message : "Something went wrong." });
      }
    },
    [messages, settings],
  );

  const clear = useCallback(() => setMessages([]), []);
  const loading = messages.some((m) => m.role === "assistant" && m.status === "loading");

  return { messages, ask, regenerate, clear, loading, settings, setSettings };
}
