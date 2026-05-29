#!/usr/bin/env python3
"""Append a canonical pipe-delimited entry to the Mnemosyne wiki log.

Standalone script for the Hermes-Agent mneme_wiki skill. Enforces the
SCHEMA.md log format in code so the agent cannot accidentally write
malformed entries.

log.md format (per SCHEMA.md):
    {ISO-datetime} | {operation} | {bucket} | {page title} | {source}

Operations: ingest | update | report | lint | merge
Append-only: new entries go at the END of the file.

Wiki root is resolved from $MNEME_WIKI_PATH; fallback ~/mneme/wiki.

Usage:
    append_wiki_log.py <operation> <bucket> <title> <source> [--dry-run]

Example:
    append_wiki_log.py ingest IDEA "Smoke Test" claude_code
    append_wiki_log.py update PROJECT "Project - Hermes" claude_code --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_WIKI = 5

VALID_OPERATIONS = {'ingest', 'update', 'report', 'lint', 'merge'}
VALID_BUCKETS = {
    'IDEA', 'ADMIN', 'REFERENCE', 'JOURNAL',
    'PERSON', 'PROJECT', 'PURSUIT',
}
VALID_SOURCES = {
    'telegram', 'email', 'web_clipper', 'n8n_chat',
    'claude_code', 'manual', 'hermes_agent',
}


def resolve_wiki_root() -> Path:
    env_path = os.environ.get('MNEME_WIKI_PATH')
    if env_path:
        root = Path(env_path).expanduser().resolve()
    else:
        root = (Path.home() / 'mneme' / 'wiki').resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"Wiki root does not exist: {root}\n"
            "Set $MNEME_WIKI_PATH or ensure ~/mneme/wiki exists."
        )
    if not root.is_dir():
        raise FileNotFoundError(f"Wiki root is not a directory: {root}")
    return root


def iso_utc_now() -> str:
    """Return current UTC time as 2026-05-29T12:34:56Z (SCHEMA convention)."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Append a SCHEMA-compliant entry to the wiki log.md.',
    )
    parser.add_argument(
        'operation',
        choices=sorted(VALID_OPERATIONS),
        help='Operation type.',
    )
    parser.add_argument(
        'bucket',
        choices=sorted(VALID_BUCKETS),
        help='Bucket name (UPPERCASE).',
    )
    parser.add_argument('title', help='Page title (e.g. "Project - Hermes").')
    parser.add_argument(
        'source',
        choices=sorted(VALID_SOURCES),
        help='Ingest source.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show the line that would be appended without writing it.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if '|' in args.title:
        print(
            "error: title contains '|' which would corrupt the pipe-delimited "
            "log format. Replace with a different character.",
            file=sys.stderr,
        )
        return EXIT_USAGE

    try:
        wiki_root = resolve_wiki_root()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NO_WIKI

    log_path = wiki_root / 'log.md'
    timestamp = iso_utc_now()
    line = f"{timestamp} | {args.operation} | {args.bucket} | {args.title} | {args.source}\n"

    if args.dry_run:
        print(f"[dry-run] Would append to {log_path}:")
        print(line, end='')
        return EXIT_OK

    # Atomic append. If log.md is missing, create it with a minimal header.
    if not log_path.exists():
        log_path.write_text(
            '# Mnemosyne Log\n\n'
            'Format: `{ISO-datetime} | {operation} | {bucket} | {page title} | {source}`\n'
            'Operations: ingest | update | report | lint | merge\n'
            'Append-only — new entries go at the END of this file, never at the top.\n\n'
            '---\n\n',
            encoding='utf-8',
        )

    with log_path.open('a', encoding='utf-8') as fh:
        fh.write(line)

    print(f"Appended to {log_path}: {line}", end='')
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
