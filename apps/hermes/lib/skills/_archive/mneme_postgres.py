"""Mneme skill — long-term knowledge storage and retrieval for Hermes.

All information that needs to persist beyond a single session goes here.
Connects directly to the Mnemosyne Postgres database (pgvector) at
10.0.50.14, bypassing n8n for simplicity.

Requires: psycopg2-binary (uncomment in requirements.txt)
Requires: Mnemosyne Postgres running with mnemosyne schema

Connection config in config/config.yml:
    mnemosyne:
      postgres_host: 10.0.50.14
      postgres_port: 5432
      postgres_db: mnemosyne
      postgres_user: hermes
      postgres_password: ""
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.core.context import Context
from lib.core.skill_registry import register_skill

# ── Constants ─────────────────────────────────────────────────────────────────
VALID_BUCKETS = {"IDEA", "ADMIN", "REFERENCE", "JOURNAL", "PERSON", "PROJECT", "PURSUIT"}
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"
TOP_K_RESULTS = 5


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _get_connection(config_path: Path | None = None):  # type: ignore[return]
    """Open a psycopg2 connection using mnemosyne config.

    Raises:
        RuntimeError: If psycopg2 is not installed or DB config is missing.
    """
    try:
        import psycopg2  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "psycopg2-binary is required for Mnemosyne integration. "
            "Uncomment it in requirements.txt and run: pip install -r requirements.txt"
        ) from exc

    import yaml

    cfg_path = config_path or (Path(__file__).parent.parent.parent / "config" / "config.yml")
    if not cfg_path.exists():
        raise RuntimeError(f"Config file not found: {cfg_path}")

    raw = yaml.safe_load(cfg_path.read_text()) or {}
    sb = raw.get("mnemosyne", {})

    required = ["postgres_host", "postgres_port", "postgres_db",
                "postgres_user", "postgres_password"]
    missing = [k for k in required if k not in sb]
    if missing:
        raise RuntimeError(
            f"Mnemosyne config missing keys in config.yml: {', '.join(missing)}"
        )

    return psycopg2.connect(
        host=sb["postgres_host"],
        port=sb["postgres_port"],
        dbname=sb["postgres_db"],
        user=sb["postgres_user"],
        password=sb["postgres_password"],
    )


def _get_embedding(text: str) -> list[float]:
    """Generate a 768-dim embedding using nomic-embed-text via Ollama.

    Args:
        text: Text to embed.

    Returns:
        List of floats (768 dimensions).

    Raises:
        RuntimeError: On connection failure or unexpected response.
    """
    import httpx

    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL} for embedding."
        ) from exc
    except (httpx.HTTPStatusError, KeyError) as exc:
        raise RuntimeError(f"Embedding request failed: {exc}") from exc


# ── Skills ────────────────────────────────────────────────────────────────────

@register_skill()
def save_note(
    text: str,
    bucket: str,
    context: Context,
    dry_run: bool = False,
    title: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Save a note to the Mnemosyne Postgres database.

    Generates an embedding and writes the resource to the mnemosyne resources
    table. Use this for any information that should persist long-term.

    Args:
        text: The full text content to save.
        bucket: One of: IDEA, ADMIN, REFERENCE, JOURNAL, PERSON, PROJECT, PURSUIT.
        context: Active context.
        dry_run: If True, describe the save without writing.
        title: Optional title (auto-generated from first 60 chars if absent).
        metadata: Optional bucket-specific JSONB metadata dict.

    Returns:
        Confirmation message with the new resource's UUID.
    """
    bucket = bucket.upper()
    if bucket not in VALID_BUCKETS:
        raise ValueError(
            f"Invalid bucket '{bucket}'. Must be one of: {', '.join(sorted(VALID_BUCKETS))}"
        )

    resolved_title = title or text[:60].strip().replace("\n", " ")
    if dry_run:
        return (
            f"[dry-run] Would save to Mnemosyne:\n"
            f"  bucket: {bucket}\n"
            f"  title:  {resolved_title}\n"
            f"  text:   {text[:100]}..."
        )

    resource_id = str(uuid.uuid4())
    embedding = _get_embedding(text)
    now = datetime.now(timezone.utc)

    slug = resource_id[:8]
    meta_json = json.dumps(metadata) if metadata else "{}"

    conn = _get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO resources (
                        id, title, original_text, source_type, bucket,
                        slug, embedding, confidence, metadata,
                        ingested_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s::vector, %s, %s::jsonb,
                        %s, %s
                    )
                    """,
                    (
                        resource_id,
                        resolved_title,
                        text,
                        "hermes",
                        bucket,
                        slug,
                        str(embedding),
                        90,
                        meta_json,
                        now,
                        now,
                    ),
                )
    finally:
        conn.close()

    return f"Saved to Mnemosyne [{bucket}] — id: {resource_id}, title: {resolved_title}"


@register_skill()
def search_memory(
    query: str,
    context: Context,
    dry_run: bool = False,
    bucket: str = "",
    limit: int = TOP_K_RESULTS,
) -> str:
    """Search Mnemosyne using semantic (vector) similarity.

    Embeds the query and finds the most similar resources in Postgres
    using pgvector cosine distance.

    Args:
        query: Natural-language search query.
        context: Active context.
        dry_run: If True, describe the search without executing.
        bucket: Optional filter to a specific bucket (e.g. "IDEA").
        limit: Number of results to return (default 5).

    Returns:
        Formatted list of matching resources.
    """
    if dry_run:
        return f"[dry-run] Would search Mnemosyne for: {query!r}"

    embedding = _get_embedding(query)

    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            if bucket:
                cur.execute(
                    """
                    SELECT id, title, summary, bucket,
                           embedding <=> %s::vector AS distance
                    FROM resources
                    WHERE deleted_at IS NULL
                      AND bucket = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (str(embedding), bucket.upper(), str(embedding), limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, title, summary, bucket,
                           embedding <=> %s::vector AS distance
                    FROM resources
                    WHERE deleted_at IS NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (str(embedding), str(embedding), limit),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return "No results found in Mnemosyne."

    lines = [f"Mnemosyne search results for '{query}':"]
    for resource_id, title, summary, bkt, distance in rows:
        short_summary = (summary or "")[:120]
        lines.append(f"\n[{bkt}] {title}")
        lines.append(f"  id: {resource_id}")
        lines.append(f"  distance: {distance:.4f}")
        if short_summary:
            lines.append(f"  {short_summary}")

    return "\n".join(lines)


@register_skill()
def ask_memory(
    question: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Ask a question and get an answer synthesised from Mnemosyne context.

    Performs a semantic search, then returns the raw context chunks for
    the agent loop to synthesise into an answer. (RAG — Retrieval Augmented
    Generation.)

    Args:
        question: The question to answer.
        context: Active context.
        dry_run: If True, describe without executing.

    Returns:
        Retrieved context passages formatted for the LLM to synthesise.
    """
    if dry_run:
        return f"[dry-run] Would query Mnemosyne to answer: {question!r}"

    raw_results = search_memory(question, context=context, limit=5)
    return (
        f"Relevant Mnemosyne context for: '{question}'\n\n"
        f"{raw_results}\n\n"
        f"Use the above context to answer the question. "
        f"If the context does not contain the answer, say so."
    )
