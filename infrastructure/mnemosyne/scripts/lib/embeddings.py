"""Embeddings sidecar helpers for Mnemosyne — Ollama nomic-embed-text + pgvector.

The wiki stays canonical; this module reads and writes a *derived, regenerable*
vector cache in Postgres (LXC 105). Drop the table and re-run `embed-wiki` to
rebuild it from the vault at any time — git is the backup, never this cache.

Two backends:
  - Ollama (LXC 101, http://10.0.50.10:11434) for `nomic-embed-text`, 768-dim.
    Pure-stdlib urllib call, matching lib/weather.py's no-dependency shape.
  - Postgres (LXC 105, 10.0.50.14:5432) with the pgvector extension, via
    psycopg2. Connection params come from the environment (never hardcoded);
    an optional ~/.config/mnemosyne/pg-creds.json supplies defaults for parity
    with vertex-creds.json / gcal-creds.json.

Unlike weather.py, these helpers DO raise typed errors (EmbeddingError /
DBError) so the batch indexer (embed-wiki) can report and abort. The digest's
collect_stale_relevant() catches them and degrades to an empty section.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# ── Ollama (embedding model) ──────────────────────────────────────────────────

EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
DEFAULT_OLLAMA_BASE_URL = "http://10.0.50.10:11434"
EMBED_TIMEOUT_SECONDS = 30

# ── Postgres (sidecar cache) ──────────────────────────────────────────────────

DEFAULT_PG_CREDS_PATH = Path.home() / ".config" / "mnemosyne" / "pg-creds.json"
DEFAULT_PG_HOST = "10.0.50.14"
DEFAULT_PG_PORT = 5432
DEFAULT_PG_DB = "mnemosyne"
DEFAULT_PG_USER = "mnemosyne"
EMBEDDINGS_TABLE = "wiki_embeddings"


class EmbeddingError(RuntimeError):
    """Ollama embedding call failed (connection, HTTP, or bad response)."""


class DBError(RuntimeError):
    """Postgres connection, schema, or query failed."""


# ── Embedding ─────────────────────────────────────────────────────────────────

def ollama_base_url() -> str:
    """Embedding endpoint base URL. OLLAMA_BASE_URL env overrides the default."""
    return os.environ.get("OLLAMA_BASE_URL", "").strip() or DEFAULT_OLLAMA_BASE_URL


def embed_text(text: str) -> list[float]:
    """Return the 768-dim nomic-embed-text embedding for `text`.

    Pure stdlib (urllib), mirroring lib/weather.py. Raises EmbeddingError on any
    failure so callers decide whether to abort (embed-wiki) or degrade
    (daily-digest).
    """
    url = f"{ollama_base_url()}/api/embeddings"
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=EMBED_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise EmbeddingError(f"cannot reach Ollama at {url}: {exc}") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise EmbeddingError(f"bad embedding response from {url}: {exc}") from exc

    embedding = data.get("embedding")
    if not isinstance(embedding, list) or len(embedding) != EMBED_DIM:
        got = len(embedding) if isinstance(embedding, list) else type(embedding).__name__
        raise EmbeddingError(f"unexpected embedding shape from {url}: {got}")
    return embedding


def to_vector_literal(embedding: list[float]) -> str:
    """Render an embedding as pgvector's text input form: '[0.1,0.2,...]'.

    Lets us bind vectors with a plain `%s::vector` cast and avoid a dependency
    on the `pgvector` Python package.
    """
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


# ── Postgres connection ───────────────────────────────────────────────────────

def load_pg_params() -> dict:
    """Resolve connection params: env wins, then pg-creds.json, then defaults.

    Env vars: MNEME_PG_HOST, MNEME_PG_PORT, MNEME_PG_DB, MNEME_PG_USER,
    MNEME_PG_PASSWORD. The password has no default — it must come from env or
    the creds file; credentials are never hardcoded. Creds-file path override:
    MNEME_PG_CREDS.
    """
    file_creds: dict = {}
    raw_path = os.environ.get("MNEME_PG_CREDS", "").strip()
    creds_path = Path(raw_path) if raw_path else DEFAULT_PG_CREDS_PATH
    if creds_path.exists():
        try:
            file_creds = json.loads(creds_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DBError(f"cannot read pg creds at {creds_path}: {exc}")

    def pick(env_key: str, file_key: str, default=None):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
        file_val = file_creds.get(file_key)
        if file_val not in (None, ""):
            return file_val
        return default

    password = pick("MNEME_PG_PASSWORD", "password", None)
    if not password:
        raise DBError(
            "Postgres password not set. Provide MNEME_PG_PASSWORD or a "
            f"'password' field in {creds_path}."
        )
    return {
        "host": pick("MNEME_PG_HOST", "host", DEFAULT_PG_HOST),
        "port": int(pick("MNEME_PG_PORT", "port", DEFAULT_PG_PORT)),
        "dbname": pick("MNEME_PG_DB", "dbname", DEFAULT_PG_DB),
        "user": pick("MNEME_PG_USER", "user", DEFAULT_PG_USER),
        "password": password,
    }


def get_conn():
    """Open a psycopg2 connection to the sidecar database. Raises DBError."""
    try:
        import psycopg2
    except ImportError as exc:
        raise DBError(
            "psycopg2 is required. Install: "
            "pip install --user --break-system-packages psycopg2-binary"
        ) from exc
    params = load_pg_params()
    try:
        return psycopg2.connect(**params)
    except Exception as exc:  # psycopg2.OperationalError and friends
        raise DBError(
            f"cannot connect to Postgres at {params['host']}:{params['port']}: {exc}"
        ) from exc


def ensure_schema(conn) -> None:
    """Create the pgvector extension, table, and indexes if absent. Idempotent.

    The ANN (hnsw) index is best-effort: on an older pgvector that lacks it, we
    roll back just that statement and fall back to exact search, which is plenty
    fast at vault scale (hundreds of pages).
    """
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {EMBEDDINGS_TABLE} (
                path         TEXT PRIMARY KEY,
                bucket       TEXT NOT NULL,
                title        TEXT NOT NULL,
                updated      DATE,
                content_hash TEXT NOT NULL,
                embedding    vector({EMBED_DIM}) NOT NULL,
                indexed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {EMBEDDINGS_TABLE}_updated_idx "
            f"ON {EMBEDDINGS_TABLE} (updated);"
        )
    conn.commit()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {EMBEDDINGS_TABLE}_embedding_idx "
                f"ON {EMBEDDINGS_TABLE} USING hnsw (embedding vector_cosine_ops);"
            )
        conn.commit()
    except Exception:  # pgvector < 0.5 has no hnsw; exact search still works
        conn.rollback()


# ── Sidecar reads/writes ──────────────────────────────────────────────────────

def fetch_hashes(conn) -> dict[str, str]:
    """Map of path -> content_hash for every indexed page (incremental sync)."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT path, content_hash FROM {EMBEDDINGS_TABLE};")
        return {row[0]: row[1] for row in cur.fetchall()}


def upsert_page(
    conn,
    *,
    path: str,
    bucket: str,
    title: str,
    updated: str | None,
    content_hash: str,
    embedding: list[float],
) -> None:
    """Insert or update one page's embedding row. Caller commits."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO {EMBEDDINGS_TABLE}
                (path, bucket, title, updated, content_hash, embedding, indexed_at)
            VALUES (%s, %s, %s, %s, %s, %s::vector, now())
            ON CONFLICT (path) DO UPDATE SET
                bucket       = EXCLUDED.bucket,
                title        = EXCLUDED.title,
                updated      = EXCLUDED.updated,
                content_hash = EXCLUDED.content_hash,
                embedding    = EXCLUDED.embedding,
                indexed_at   = now();
            """,
            (path, bucket, title, updated or None, content_hash,
             to_vector_literal(embedding)),
        )


def prune_missing(conn, present_paths: set[str]) -> int:
    """Delete rows whose path is no longer on disk. Returns rows removed."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT path FROM {EMBEDDINGS_TABLE};")
        indexed = {row[0] for row in cur.fetchall()}
        stale = indexed - present_paths
        for path in stale:
            cur.execute(f"DELETE FROM {EMBEDDINGS_TABLE} WHERE path = %s;", (path,))
    return len(stale)


# ── Stale-but-now-relevant query ──────────────────────────────────────────────

def stale_relevant(
    *,
    today: date,
    buckets: tuple[str, ...],
    stale_age_days: int,
    recent_days: int,
    max_distance: float,
    limit: int,
) -> list[dict[str, str]]:
    """Old pages (in `buckets`, updated > stale_age_days ago) whose nearest
    recently-updated page (within recent_days) is within `max_distance` cosine
    distance. Delta-detection: dormant pages that re-align with recent activity.

    Returns up to `limit` dicts {title, updated, why_now} ordered by closeness.
    Raises DBError on any backend failure — the digest caller degrades to [].
    """
    stale_before = today.fromordinal(today.toordinal() - stale_age_days)
    recent_after = today.fromordinal(today.toordinal() - recent_days)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT s.title,
                       s.updated,
                       r.title AS why_now,
                       (s.embedding <=> r.embedding) AS distance
                FROM {EMBEDDINGS_TABLE} s
                CROSS JOIN LATERAL (
                    SELECT title, embedding
                    FROM {EMBEDDINGS_TABLE} rr
                    WHERE rr.updated >= %(recent_after)s
                      AND rr.path <> s.path
                    ORDER BY rr.embedding <=> s.embedding
                    LIMIT 1
                ) r
                WHERE s.bucket = ANY(%(buckets)s)
                  AND s.updated <= %(stale_before)s
                  AND (s.embedding <=> r.embedding) <= %(max_distance)s
                ORDER BY distance ASC
                LIMIT %(limit)s;
                """,
                {
                    "buckets": list(buckets),
                    "stale_before": stale_before,
                    "recent_after": recent_after,
                    "max_distance": max_distance,
                    "limit": limit,
                },
            )
            rows = cur.fetchall()
    except DBError:
        raise
    except Exception as exc:
        raise DBError(f"stale-relevant query failed: {exc}") from exc
    finally:
        conn.close()

    results: list[dict[str, str]] = []
    for title, updated, why_now, _distance in rows:
        results.append({
            "title": title,
            "updated": updated.isoformat() if updated else "(unknown)",
            "why_now": why_now,
        })
    return results
