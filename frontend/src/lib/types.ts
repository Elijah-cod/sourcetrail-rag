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
  /** Milliseconds per stage: embed_ms, search_ms, rerank_ms, facets_ms, lookup_ms, generation_ms,
   *  gap_search_ms, gap_answer_ms, recheck_ms. Only the stages this question went through. */
  timings: Record<string, number>;
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
