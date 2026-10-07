"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, askQuestion } from "@/lib/api";
import type { Mode, QueryResult } from "@/lib/types";

export type UserMessage = { id: number; role: "user"; text: string };
export type AssistantMessage = {
  id: number;
  role: "assistant";
  question: string;
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

  const ask = useCallback(
    async (question: string) => {
      const answerId = nextId.current + 1;
      nextId.current += 2;
      // Show the question and a "thinking…" placeholder immediately, before the server answers.
      setMessages((list) => [
        ...list,
        { id: answerId - 1, role: "user", text: question },
        { id: answerId, role: "assistant", question, status: "loading" },
      ]);

      const finish = (changes: Partial<AssistantMessage>) =>
        setMessages((list) => list.map((m) => (m.id === answerId && m.role === "assistant" ? { ...m, ...changes } : m)));

      try {
        const result = await askQuestion(question, settings.mode, settings.topK);
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

  const clear = useCallback(() => setMessages([]), []);
  const loading = messages.some((m) => m.role === "assistant" && m.status === "loading");

  return { messages, ask, clear, loading, settings, setSettings };
}
