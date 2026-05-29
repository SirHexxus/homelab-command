#!/usr/bin/env python3
"""Write or overwrite a page in the Mnemosyne wiki.

Standalone port of write_wiki_page from apps/hermes/lib/skills/wiki.py
for the Hermes-Agent mneme_wiki skill. No imports from the homegrown
agent — runs anywhere with Python 3.11+.

Behavior parity with the homegrown version:
- Wiki root from $MNEME_WIKI_PATH; fallback ~/mneme/wiki
- Path-traversal guard (no escaping the wiki root)
- UTF-8 write; parent dirs created as needed
- --dry-run reports the intended write without performing it

Usage:
    write_wiki_page.py <relative_path> <content_source> [--dry-run]

    <content_source> is either '-' (read content from stdin) or a path
    to a file whose contents will be written verbatim.

Example:
    echo "# Hi" | write_wiki_page.py "ideas/Smoke Test.md" -
    write_wiki_page.py "ideas/Smoke Test.md" /tmp/content.md --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_TRAVERSAL = 4
EXIT_NO_WIKI = 5


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


def safe_target(wiki_root: Path, rel_path: str) -> Path:
    candidate = (wiki_root / rel_path).resolve()
    if not candidate.is_relative_to(wiki_root):
        raise PermissionError(
            f"Path {rel_path!r} escapes the wiki root ({wiki_root})."
        )
    return candidate


def read_content(source: str) -> str:
    if source == '-':
        return sys.stdin.read()
    src_path = Path(source).expanduser()
    if not src_path.exists():
        raise FileNotFoundError(f"Content source not found: {src_path}")
    if not src_path.is_file():
        raise IsADirectoryError(f"Content source is a directory: {src_path}")
    return src_path.read_text(encoding='utf-8')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Write a page in the Mnemosyne wiki.'
    )
    parser.add_argument(
        'path',
        help='Relative path inside the wiki (e.g. "ideas/Smoke Test.md").',
    )
    parser.add_argument(
        'content_source',
        help='File to read content from, or "-" for stdin.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report the intended write without performing it.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        wiki_root = resolve_wiki_root()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NO_WIKI

    try:
        target = safe_target(wiki_root, args.path)
    except PermissionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_TRAVERSAL

    try:
        content = read_content(args.content_source)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND
    except IsADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    byte_count = len(content.encode('utf-8'))

    if args.dry_run:
        print(f"[dry-run] Would write {byte_count} bytes to {target}")
        return EXIT_OK

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    print(f"Wrote {byte_count} bytes to {target}")
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
