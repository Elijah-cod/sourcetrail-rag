-- 001_init.sql — first version of the database schema.

-- Turn on the pgvector extension so Postgres understands the "vector" type.
CREATE EXTENSION IF NOT EXISTS vector;

-- A workspace is a private "box" of documents.
-- Each visitor gets one (no login needed); the demo collection is a special one.
CREATE TABLE workspaces (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    is_demo      boolean     NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

-- The demo workspace has a fixed, well-known ID so the code can always find it.
INSERT INTO workspaces (id, is_demo)
VALUES ('00000000-0000-0000-0000-000000000001', true);

-- One row per uploaded file or ingested web page.
CREATE TABLE documents (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id   uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    slug           text NOT NULL,          -- short readable name, e.g. "annual-report-2024"
    title          text NOT NULL,
    source_type    text NOT NULL CHECK (source_type IN ('pdf','docx','md','txt','csv','url')),
    source_uri     text,                   -- original filename or URL
    published_year int,                    -- used for filters like "in 2024"
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, slug)
);

CREATE INDEX documents_workspace_idx ON documents (workspace_id);

-- One row per chunk (a small piece of a document). This is what we search.
CREATE TABLE chunks (
    id          text PRIMARY KEY,          -- stable ID, e.g. "annual-report-2024:p47:c03"
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ord         int  NOT NULL,             -- position of the chunk inside its document
    text        text NOT NULL,
    page        int,                       -- PDF page number, if any
    section     text,                      -- heading the chunk sits under, if any
    embedding   vector(384),               -- meaning of the text as 384 numbers (bge-small)
    -- Keyword-search version of the text, kept up to date automatically by Postgres.
    -- Words in the section heading count more (weight A) than words in the body (weight B).
    tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(section, '')), 'A') ||
        setweight(to_tsvector('english', text), 'B')
    ) STORED
);

CREATE INDEX chunks_document_idx  ON chunks (document_id);
-- HNSW index: makes "find the closest vectors" fast (cosine distance).
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
-- GIN index: makes "find chunks containing these words" fast.
CREATE INDEX chunks_tsv_idx       ON chunks USING gin (tsv);
