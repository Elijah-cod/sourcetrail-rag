# sourcetrail-rag — Design Spec

Date: 2026-10-02
Status: approved for backend implementation
Reference diagram: `docs/Sourcetrail_architecture.excalidraw` ("CiteBase")

## 1. Goal

A public portfolio site where anyone can upload documents or paste URLs and ask
questions. The system turns messy sources into structured, metadata-rich chunks,
retrieves with hybrid vector + keyword search, fuses with RRF, reranks with a
cross-encoder, and generates a grounded answer with inline citations `[1] [2]`
that map back to the exact document, page and chunk.

Success criteria:
- A visitor gets a cited answer from the demo collection within seconds of opening the site.
- A visitor can upload their own files and query them privately (no login).
- Every citation can be inspected (document · page/section · chunk text).
- An evaluation script shows measurable gains: vector → keyword → hybrid → hybrid + reranker.
- Builds and deploys at $0.

Out of scope (later): authentication, multi-user accounts, OCR, images, agents,
knowledge graphs, advanced query planning, Kubernetes, real-time collaboration,
enterprise permissions.

## 2. Stack

| Concern | Choice |
|---|---|
| Language / packaging | Python 3.12, `uv` |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 17 + pgvector (Docker locally, Neon free plan in production) |
| DB driver | psycopg 3 (plain SQL, no ORM) |
| Keyword search | Postgres full-text search (`tsvector`, `websearch_to_tsquery`, `ts_rank_cd`) — BM25-like, not exact BM25 |
| Embeddings | FastEmbed (ONNX, CPU) `BAAI/bge-small-en-v1.5`, 384 dims |
| Reranker | FastEmbed cross-encoder `Xenova/ms-marco-MiniLM-L-6-v2` |
| LLM | OpenAI-compatible client: Groq free tier in production, Ollama optional locally |
| Extraction | `pypdf` (PDF), `python-docx` (DOCX), `trafilatura` (URL/HTML), stdlib (MD, TXT, CSV) |
| Config | `pydantic-settings`, `.env` |
| Tests / CI | `pytest`, GitHub Actions |
| Hosting | Render free web service + Neon free Postgres |

No LangChain / LlamaIndex: chunking, fusion, reranking and citation logic are
written by hand so every step is visible and explainable.

## 3. Architecture

One FastAPI service, one Postgres database. All backend code lives in `backend/` (paths below are relative to it); the UI lives in `frontend/`.

```
app/
  config.py      settings from environment
  db.py          connection pool + migrations runner
  ingest/        extractors: source -> list[Section(text, page, heading, row)]
  chunking.py    type-specific chunking -> Chunk(text, page, section, chunk_id)
  embed.py       FastEmbed wrapper (embed_documents, embed_query)
  store.py       all SQL: insert, vector_search, keyword_search
  query.py       query processing: extract filters (e.g. year) from the question
  retrieve.py    hybrid retrieval: vector + keyword -> RRF -> rerank
  generate.py    prompt with numbered sources -> LLM -> answer + citations
  workspace.py   anonymous workspaces, limits, cleanup
  main.py        FastAPI app + routes
migrations/      numbered .sql files
eval/            questions.jsonl + run_eval.py
tests/
```

Each module has one job and is testable on its own.

## 4. Data model

```sql
workspaces(id uuid pk, created_at, last_seen_at, is_demo bool)
documents(id uuid pk, workspace_id fk, slug text, title text,
          source_type text,   -- pdf|docx|md|txt|csv|url
          source_uri text, published_year int null, created_at)
chunks(id text pk,             -- stable: "{doc_slug}:p{page}:c{n}"
       document_id fk on delete cascade, ord int,
       text text, page int null, section text null,
       embedding vector(384),
       tsv tsvector generated always as (to_tsvector('english', text)) stored)
```
Indexes: HNSW (cosine) on `embedding`, GIN on `tsv`, btree on `documents.workspace_id`.
Every search is filtered to `workspace_id IN (visitor_ws, demo_ws)`.

## 5. Ingestion pipeline

1. **Extract** text + structure per type: PDF → one section per page; MD → one
   section per heading; CSV → one section per row (header repeated); DOCX → per
   heading/paragraph block; TXT → whole text; URL → trafilatura main content + title + date.
2. **Chunk** each section to ~1,000 characters with ~150 overlap, splitting on
   paragraph → sentence → word boundaries. CSV rows are grouped, never split.
3. **Metadata**: source, page, section heading, year (from URL date or filename), stable chunk_id.
4. **Embed** chunk texts in batches; **store** document + chunks in one transaction.

## 6. Query pipeline

1. **Query processing**: extract a year only when a time word precedes it ("in 2024", "since 2019", "FY2024") and exactly one year is mentioned → soft filter on `published_year` (documents dated to another year are skipped; undated documents are kept).
2. **Vector search** top 20 (cosine) and **keyword search** top 20, both workspace-filtered.
3. **RRF fusion**: `score = Σ 1 / (60 + rank)` across both lists → top 30.
4. **Rerank** with cross-encoder → top 6.
5. **Generate**: prompt lists sources as `[1]..[6]` with title/page; model must answer
   only from them, cite with `[n]`, and say it doesn't know when sources don't cover it.
6. **Validate citations**: drop `[n]` outside the source range; return answer +
   `citations: [{n, chunk_id, document title, page, section, snippet}]`.

A `mode` parameter (`vector|keyword|hybrid|hybrid_rerank`) exists for evaluation.

## 7. API

| Method | Path | Purpose |
|---|---|---|
| GET | /health | liveness + DB check |
| POST | /documents | multipart upload (pdf, docx, md, txt, csv) |
| POST | /sources/url | ingest a web page |
| GET | /documents | list visitor + demo documents |
| DELETE | /documents/{id} | delete own document |
| POST | /query | `{question, mode?}` → answer + citations |
| GET | /chunks/{chunk_id} | source inspection |

## 8. Public-site safety (no auth)

- Anonymous workspace: random UUID in an HTTP-only cookie.
- Limits: 10 MB per file, 10 documents and 2,000 chunks per workspace.
- Rate limits: 10 queries/min per workspace; global daily LLM cap under the Groq quota.
- Visitor workspaces and their data are deleted 24 h after last activity.
- URL ingestion: http/https only, block private/loopback IPs (SSRF), 10 s timeout, 5 MB cap.

## 9. Error handling

- Unsupported/corrupt file or empty extraction → 422 with a clear message; nothing stored.
- Ingestion is all-or-nothing per document (single transaction).
- LLM failure or quota exhausted → 503-style response that still returns the retrieved sources.
- Limits exceeded → 413 / 429 with a message.

## 10. Evaluation

`eval/questions.jsonl`: 30–50 questions over the demo collection, each with the
gold chunk_id(s). `run_eval.py` runs all four modes and reports Recall@5,
Recall@10, MRR, Precision@5. Generation metrics (citation correctness first; answer
relevance and faithfulness via LLM-as-judge) follow once retrieval is solid.

## 11. Testing

- Unit tests: chunking, RRF, citation validation, query processing, extractors (fixture files).
- Integration tests against the Docker Postgres: store + search + API endpoints.
- Embedding/reranker/LLM are injectable so unit tests can use fakes.

## 12. Build order (one or more commits each)

Backend: 1 skeleton + Docker Postgres + /health · 2 schema/migrations ·
3 extractors · 4 chunking · 5 embeddings + store · 6 vector search ·
7 keyword search · 8 RRF · 9 reranker · 10 generation + citations ·
11 API routes · 12 workspaces + limits · 13 eval set + script.
Then: 14 chat UI + source viewer · 15 deploy (Render + Neon) + CI.
