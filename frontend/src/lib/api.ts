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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    // Same origin: the browser sends the workspace cookie automatically.
    response = await fetch(`/api${path}`, { credentials: "same-origin", ...init });
  } catch {
    throw new ApiError("Can't reach the server. Is the backend running?", 0);
  }

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

export const askQuestion = (question: string, mode: Mode, topK: number) =>
  request<QueryResult>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode, top_k: topK }),
  });

export const getChunk = (documentId: string, chunkId: string) =>
  request<Chunk>(`/documents/${encodeURIComponent(documentId)}/chunks/${encodeURIComponent(chunkId)}`);

export const getBenchmarks = () => request<Benchmarks>("/benchmarks");
