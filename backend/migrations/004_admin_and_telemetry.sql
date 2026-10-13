-- 004_admin_and_telemetry.sql
-- What the admin area shows: one row per answered question and per document added, plus the
-- admin's sign-in sessions and events. No question, answer or document text is stored here.
-- Deleted automatically (app/maintenance.py): telemetry after 7 days, admin events after 30.

CREATE TABLE query_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  timestamptz NOT NULL DEFAULT now(),
    mode        text        NOT NULL,
    status      text        NOT NULL,          -- answered | not_found | llm_unavailable | error
    parts       int         NOT NULL DEFAULT 0, -- parts the question was split into
    missing     int         NOT NULL DEFAULT 0, -- parts no passage was found for
    sources     int         NOT NULL DEFAULT 0,
    citations   int         NOT NULL DEFAULT 0,
    total_ms    real,
    timings     jsonb       NOT NULL DEFAULT '{}', -- milliseconds per stage
    error       text                               -- a category, never a stack trace
);
CREATE INDEX query_events_created ON query_events (created_at);

CREATE TABLE ingest_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  timestamptz NOT NULL DEFAULT now(),
    source_type text        NOT NULL,          -- pdf | docx | md | txt | csv | url | unknown
    ok          boolean     NOT NULL,
    chunks      int         NOT NULL DEFAULT 0,
    characters  int         NOT NULL DEFAULT 0,
    duration_ms real,
    warning     text,
    error       text,
    document_id uuid                               -- while the document still exists
);
CREATE INDEX ingest_events_created ON ingest_events (created_at);

-- The cookie carries a random token; only its SHA-256 is stored, so a database leak can't be replayed.
CREATE TABLE admin_sessions (
    token_hash  text        PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz
);

CREATE TABLE admin_events (
    id          bigserial   PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    kind        text        NOT NULL,          -- login | login_failed | logout | expired
    subject     text                           -- hashed client IP, never the IP or a password
);
CREATE INDEX admin_events_created ON admin_events (created_at);
