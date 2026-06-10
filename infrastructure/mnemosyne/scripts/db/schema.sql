-- Mnemosyne Postgres schema (DORMANT — apply once the mnemosyne role/db exists).
-- Targets the same database that unblocks the embeddings sidecar.
-- Two tables: the event log (replaces append-only log.md) and archived-page cold storage.

-- ---------------------------------------------------------------------------
-- mneme_log — structured replacement for wiki/log.md
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mneme_log (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL,           -- embedded event timestamp
    operation   TEXT NOT NULL,                  -- see CHECK below
    bucket      TEXT NOT NULL,                  -- IDEA|ADMIN|...|RAW|— (report)
    page_title  TEXT NOT NULL,
    source      TEXT NOT NULL,                  -- telegram|claude_code|scheduled|...
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mneme_log_operation_ck CHECK (operation IN
        ('ingest','create','update','merge','rename','delete','report','lint'))
);
CREATE INDEX IF NOT EXISTS mneme_log_ts_idx        ON mneme_log (ts);
CREATE INDEX IF NOT EXISTS mneme_log_bucket_ts_idx ON mneme_log (bucket, ts);
CREATE INDEX IF NOT EXISTS mneme_log_title_idx     ON mneme_log (page_title);

-- ---------------------------------------------------------------------------
-- mneme_archived_pages — cold storage for archived wiki pages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mneme_archived_pages (
    id           BIGSERIAL PRIMARY KEY,
    bucket       TEXT NOT NULL,
    title        TEXT NOT NULL,
    orig_path    TEXT NOT NULL,                 -- path relative to wiki root
    archived_on  DATE NOT NULL,
    archived_reason TEXT,                       -- closed|aged|machine-report
    page_date    DATE,                          -- from filename/frontmatter
    status       TEXT,                          -- ADMIN status at archive time
    frontmatter  JSONB,
    body         TEXT,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (bucket, title, page_date)
);
CREATE INDEX IF NOT EXISTS mneme_archived_bucket_idx ON mneme_archived_pages (bucket);
CREATE INDEX IF NOT EXISTS mneme_archived_fm_idx     ON mneme_archived_pages USING GIN (frontmatter);
