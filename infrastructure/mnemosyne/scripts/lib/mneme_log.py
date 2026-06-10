#!/usr/bin/env python3
"""Append an event to the mneme_log Postgres table (authoritative event log).

Fail-soft by design: a DB error never propagates to the caller — wiki ingestion
must not break on a Postgres hiccup (mirrors the graceful-degrade stance of
lib/embeddings.py). Importable as `log_event(...)` and runnable as a CLI so bash
callers (lib/wiki-common.sh) can log too. UTF-8 is forced via mneme_pg because
the cluster is SQL_ASCII.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make mneme_pg importable

VALID_OPS = {"ingest", "create", "update", "merge", "rename",
             "delete", "report", "lint"}


def log_event(operation: str, bucket: str, title: str, source: str,
              ts: datetime | None = None) -> bool:
    """Insert one event row. Returns True on success, False on swallowed error."""
    when = ts or datetime.now(timezone.utc)
    try:
        import mneme_pg
        conn = mneme_pg.connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO mneme_log (ts, operation, bucket, page_title, source) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (when, operation, bucket, title, source),
                )
        finally:
            conn.close()
        return True
    except Exception as exc:  # fail-soft: never break the caller
        print(f"Warning: mneme_log insert failed ({type(exc).__name__}: {exc}); "
              f"event not recorded: {operation} | {bucket} | {title}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--op", required=True, help="operation (ingest, update, report, ...)")
    ap.add_argument("--bucket", required=True, help="bucket, or — for reports")
    ap.add_argument("--title", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--ts", help="ISO timestamp; default now (UTC)")
    args = ap.parse_args()
    if args.op not in VALID_OPS:
        print(f"Warning: undocumented operation '{args.op}' "
              f"(see schema/09-log-format.md)", file=sys.stderr)
    ts = None
    if args.ts:
        try:
            ts = datetime.fromisoformat(args.ts.replace("Z", "+00:00"))
        except ValueError:
            print(f"Warning: bad --ts {args.ts}; using now()", file=sys.stderr)
    log_event(args.op, args.bucket, args.title, args.source, ts)
    return 0  # always 0 — fail-soft


if __name__ == "__main__":
    sys.exit(main())
