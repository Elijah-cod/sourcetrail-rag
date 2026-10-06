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
  timings: { search_ms?: number; rerank_ms?: number; generation_ms?: number };
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
