-- 003_usage_events.sql
-- A log of rate-limited actions ("query", "upload", "llm"), used to count recent usage.
-- `subject` is a hashed client IP, or 'global' for site-wide limits. Never a raw IP.

CREATE TABLE usage_events (
    id         bigserial   PRIMARY KEY,
    kind       text        NOT NULL,
    subject    text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- "How many <kind> events for <subject> since <time>?" is the only question we ask.
CREATE INDEX usage_events_lookup ON usage_events (kind, subject, created_at);
