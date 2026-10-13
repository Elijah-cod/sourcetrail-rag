// The shapes of data the backend sends. They mirror backend/app/schemas.py,
// so TypeScript can catch mistakes like reading a field that doesn't exist.

export type SourceType = "pdf" | "docx" | "md" | "txt" | "csv" | "url";

export type DocumentInfo = {
  id: string;
  title: string;
  source_type: SourceType;
  source_uri: string | null;
  published_year: number | null;
  created_at: string;
  is_demo: boolean;
  chunk_count: number;
};

export type IngestResult = {
  document_id: string;
  title: string;
  slug: string;
  chunk_count: number;
  characters: number;
  warning: string | null;
};

export type Mode = "vector" | "keyword" | "hybrid" | "hybrid_rerank";

export type Citation = {
  n: number;
  chunk_id: string;
  document_id: string;
  document_title: string;
  source_type: SourceType;
  source_uri: string | null;
  page: number | null;
  section: string | null;
  snippet: string;
};

export type Source = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page: number | null;
  section: string | null;
  score: number;
  ranks: Record<string, number>;
  text: string;
};

export type QueryResult = {
  status: "answered" | "not_found" | "llm_unavailable";
  answer: string;
  citations: Citation[];
  sources: Source[];
  filters: { year?: number };
  /** When the answer was ready (ISO 8601, UTC); shown in the visitor's own time zone. */
  created_at?: string;
  /** Figures or codes in the answer that no source contains (worth checking). */
  unverified?: string[];
};

export type Chunk = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  source_type: SourceType;
  source_uri: string | null;
  ord: number;
  page: number | null;
  section: string | null;
  text: string;
};

/** GET /benchmarks: the latest results of the two evaluation scripts (null = not run yet). */
export type RetrievalResults = {
  generated_at: string;
  answerable: number;
  unanswerable: number;
  modes: { mode: Mode; recall_at_1: number; recall_at_5: number; recall_at_10: number; mrr: number; precision_at_5: number; avg_ms: number }[];
  threshold: { value: number; answerable_refused: number; answerable: number; unanswerable_refused: number; unanswerable: number } | null;
};

export type RegressionQuestion = {
  id: string;
  fixture: string;
  question: string;
  answerable: boolean;
  facets_covered: number;
  facets: number;
  sources_sent: number;
  latency_ms: number;
  uncovered: string[];
  problems: string[] | null;       // null = answers weren't graded in this run
  unverified: string[] | null;
};

export type RegressionResults = {
  generated_at: string;
  with_answers: boolean;
  ingestion: { id: string; fixture: string; ok: boolean; detail: string }[];
  questions: RegressionQuestion[];
};

export type Benchmarks = { retrieval: RetrievalResults | null; regression: RegressionResults | null };

// ---------- admin area ----------

export type AdminOverview = {
  service: {
    database: "ok" | "down";
    models: string;
    llm: string;
    checked_at: string;
    started_at: string;
    uptime_s: number;
    startup_ms: Record<string, number> | null;
  };
  build: {
    version: string;
    revision: string | null;
    commit: string | null;
    llm_model: string;
    embedding_model: string;
    reranker_model: string;
  };
  period_days: number;
  queries: {
    total: number;
    answered: number;
    refused: number;
    missing_parts: number;
    errors: number;
    p50_ms: number | null;
    p95_ms: number | null;
  };
  ingestion: { ok: number; failed: number; warnings: number };
  failed_logins: number;
  benchmark_run_at: string | null;
  retention: { documents_hours: number; telemetry_days: number; admin_events_days: number };
};

/** One answered question: outcome and time per stage, never its text. */
export type QueryEvent = {
  id: string;
  created_at: string;
  mode: Mode;
  status: "answered" | "not_found" | "llm_unavailable" | "error";
  parts: number;
  missing: number;
  sources: number;
  citations: number;
  total_ms: number | null;
  timings: Record<string, number>;
  error: string | null;
};

export type IngestEvent = {
  id: string;
  created_at: string;
  source_type: string;
  ok: boolean;
  chunks: number;
  characters: number;
  duration_ms: number | null;
  warning: string | null;
  error: string | null;
  expires_at: string | null;
};
