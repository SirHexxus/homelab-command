# Embeddings Sidecar — Setup & Operations

The Daily Digest's Section 5 (stale-but-now-relevant) is backed by a pgvector
sidecar: `nomic-embed-text` (Ollama LXC 101) → Postgres `wiki_embeddings`
(LXC 105). The wiki stays canonical; this cache is derived and regenerable.

Code:
- `lib/embeddings.py` — embed + connection + schema + stale query
- `embed-wiki` — incremental indexer (cron'd before the digest)
- `daily-digest` — `collect_stale_relevant()` queries the cache at render time

## What's done

- All code written, compiles, and degrades gracefully when the DB is absent
  (digest still generates; section omits with a stderr warning).
- `psycopg2-binary` installed into user site.

## What's blocked on you (one-time DB setup)

The sidecar needs a Postgres role + database on LXC 105 (10.0.50.14). Run, as a
Postgres superuser on that host (adjust the password):

    CREATE ROLE mnemosyne LOGIN PASSWORD 'CHOOSE_A_STRONG_PASSWORD';
    CREATE DATABASE mnemosyne OWNER mnemosyne;
    \c mnemosyne
    CREATE EXTENSION IF NOT EXISTS vector;
    GRANT ALL ON SCHEMA public TO mnemosyne;

(`embed-wiki` calls `ensure_schema()` itself, so the table/indexes are created
on first run — the role just needs CREATE on the database.)

## Credentials (pick one)

The code resolves connection params as: env vars > `pg-creds.json` > defaults
(host 10.0.50.14, port 5432, db `mnemosyne`, user `mnemosyne`). Password has no
default. Either:

- **Creds file** (parity with vertex-creds.json), `~/.config/mnemosyne/pg-creds.json`:

      {"password": "THE_PASSWORD"}

  (host/port/dbname/user optional — add only to override the defaults.)
  `chmod 600` it.

- **Env** in `~/.bashrc.local` (where OPENWEATHER_API_KEY etc. live):
  `export MNEME_PG_PASSWORD=...` (and any `MNEME_PG_HOST/PORT/DB/USER` overrides).

## First index + verify

    embed-wiki --dry-run        # reports counts, no writes (~468 pages)
    embed-wiki                  # embed + upsert; re-run is a near no-op
    daily-digest --dry-run      # shows the [dry-run] Stale-relevant block
    daily-digest --no-send --no-write   # full render incl. Section 5

Tune `STALE_MAX_DISTANCE` in `daily-digest` (default 0.35 cosine distance —
smaller = stricter) against a few real runs so the section stays signal.

## Cron

Add an indexer run a few minutes before the 07:00 digest so it reflects
overnight captures (it writes only to Postgres, not the vault):

    55 6 * * * . ~/.bashrc.local && /home/james/projects/homelab-command/infrastructure/mnemosyne/scripts/embed-wiki >> /home/james/mneme/embed.log 2>&1

## Close-out (after first good run)

Flip the ADMIN task `Wire Stale-But-Now-Relevant Detection into Daily Digest`
to Done and append a log.md entry. Do NOT git-commit the wiki — the vault-sync
cron handles that. The homelab-command repo changes are separate and committed
on request.
