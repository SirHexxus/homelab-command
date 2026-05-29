#!/usr/bin/env python3
"""Read a page from the Mnemosyne wiki by relative path.

Port of read_wiki_page from apps/hermes/lib/skills/wiki.py — Spike 4
verification of the Hermes-Agent skill format.

Behavior parity with the homegrown version:
- Wiki root from $MNEME_WIKI_PATH; fallback ~/mneme/wiki
- Path-traversal guard (no escaping the wiki root)
- UTF-8 read with replacement on decode errors
- Distinct exit codes for the common error classes

Usage:
    read_wiki_page.py <relative_path>

Example:
    read_wiki_page.py "projects/Project - Hermes.md"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# Exit codes — match the SKILL.md table.
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_IS_DIR = 3
EXIT_TRAVERSAL = 4
EXIT_NO_WIKI = 5


def resolve_wiki_root() -> Path:
    """Return the resolved wiki root path or raise FileNotFoundError."""
    env_path = os.environ.get('MNEME_WIKI_PATH')
    if env_path:
        root = Path(env_path).expanduser().resolve()
    else:
        root = Path.home() / 'mneme' / 'wiki'
        root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"Wiki root does not exist: {root}\n"
            "Set $MNEME_WIKI_PATH in ~/.hermes/.env or "
            "ensure ~/mneme/wiki exists."
        )
    if not root.is_dir():
        raise FileNotFoundError(f"Wiki root is not a directory: {root}")
    return root


def safe_target(wiki_root: Path, rel_path: str) -> Path:
    """Resolve rel_path inside wiki_root; raise PermissionError on escape."""
    candidate = (wiki_root / rel_path).resolve()
    if not candidate.is_relative_to(wiki_root):
        raise PermissionError(
            f"Path {rel_path!r} escapes the wiki root ({wiki_root})."
        )
    return candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Read a page from the Mnemosyne wiki.'
    )
    parser.add_argument(
        'path',
        help='Relative path to the wiki page (e.g. "ideas/Five-Layer AI Stack.md").',
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

    if not target.exists():
        print(f"error: wiki page not found: {target}", file=sys.stderr)
        return EXIT_NOT_FOUND
    if not target.is_file():
        print(f"error: path is a directory, not a page: {target}", file=sys.stderr)
        return EXIT_IS_DIR

    content = target.read_text(encoding='utf-8', errors='replace')
    sys.stdout.write(content)
    if not content.endswith('\n'):
        sys.stdout.write('\n')
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
