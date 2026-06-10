-- One-time Postgres bootstrap for Mnemosyne (run as a superuser on LXC 105 / 10.0.50.14).
-- Shared with the embeddings sidecar — same role + db serve both.
-- Replace the password before running.

CREATE ROLE mnemosyne LOGIN PASSWORD 'CHOOSE_A_STRONG_PASSWORD';
CREATE DATABASE mnemosyne OWNER mnemosyne;

\connect mnemosyne
GRANT ALL ON SCHEMA public TO mnemosyne;

-- pgvector extension is needed ONLY by the embeddings sidecar (wiki_embeddings).
-- The log/archive tables in schema.sql do NOT need it. Safe to run if pgvector
-- is installed; skip otherwise and add it during the embeddings standup.
CREATE EXTENSION IF NOT EXISTS vector;
