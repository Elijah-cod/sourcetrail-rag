// Every call to the backend goes through this file.
import type { Benchmarks, Chunk, DocumentInfo, IngestResult, Mode, QueryResult } from "./types";

/** An error from the API, carrying the human-readable message the backend sent. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public retryAfter?: number,
  ) {
    super(message);
  }
}

/** FastAPI errors look like {"detail": "text"} or, for validation errors, {"detail": [{"msg": ...}]}. */
function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return fallback;
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  try {
    // Same origin: the browser sends the workspace cookie automatically.
    return await fetch(`/api${path}`, { credentials: "same-origin", ...init });
  } catch (error) {
    if (init?.signal?.aborted) throw error;     // stopped on purpose, not a network problem
    throw new ApiError("Can't reach the server. Is the backend running?", 0);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await send(path, init);
  if (response.status === 204) return undefined as T;  // "No Content" (e.g. after a delete)
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const retry = Number(response.headers.get("Retry-After")) || undefined;
    throw new ApiError(messageFrom(body, `Request failed (${response.status})`), response.status, retry);
  }
  return body as T;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const health = await request<{ status: string; database: string }>("/health");
    return health.database === "ok";
  } catch {
    return false;
  }
}

export const listDocuments = () => request<DocumentInfo[]>("/documents");

export function uploadDocument(file: File) {
  const form = new FormData();          // multipart/form-data, like an HTML file input
  form.append("file", file);
  return request<IngestResult>("/documents", { method: "POST", body: form });
}

export const addUrl = (url: string) =>
  request<IngestResult>("/sources/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

export const deleteDocument = (id: string) =>
  request<void>(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });

/** What the server is doing while it prepares an answer (see POST /query/stream). */
export type Stage = { stage: "search" | "parts" | "write" | "check"; count?: number; done?: number; sources?: number };

/** Ask a question. `onStage` is called as each stage starts, so a slow answer shows progress.
 *  The server sends one JSON object per line: stages, then {"result"} or {"error"}. */
export async function askQuestionStream(
  question: string,
  mode: Mode,
  topK: number,
  onStage: (stage: Stage) => void,
  signal?: AbortSignal,
) {
  const response = await send("/query/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode, top_k: topK }),
    signal,
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null);
    const retry = Number(response.headers.get("Retry-After")) || undefined;
    throw new ApiError(messageFrom(body, `Request failed (${response.status})`), response.status, retry);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";          // a line may arrive in pieces: keep the unfinished end
    for (const line of lines.filter((l) => l.trim())) {
      const event = JSON.parse(line) as Stage | { result: QueryResult } | { error: string };
      if ("result" in event) return event.result;
      if ("error" in event) throw new ApiError(event.error, 500);
      onStage(event);
    }
  }
  throw new ApiError("The answer was cut off. Please try again.", 0);
}

export const getChunk = (documentId: string, chunkId: string) =>
  request<Chunk>(`/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}`);

export const getBenchmarks = () => request<Benchmarks>("/benchmarks");
