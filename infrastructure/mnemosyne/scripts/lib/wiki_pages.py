"""Which files in a wiki bucket directory are pages.

One home for the rule, so every walker sees the same page set. Pages sit
directly in their bucket directory, except that ``reference/`` may hold one
level of subfolders (``reference/problems/`` holds problem records; see the
wiki's ``schema/16-problem-records.md``). ``find_wiki_files`` in
``wiki-common.sh`` mirrors this rule for the bash scripts.
"""
from __future__ import annotations

from pathlib import Path

# Bucket directories whose pages may sit one subfolder deep.
NESTED_BUCKET_DIRS = frozenset({"reference"})


def bucket_pages(bucket_dir: Path) -> list[Path]:
    """Return the bucket's ``.md`` pages, sorted. Missing directory → []."""
    if not bucket_dir.is_dir():
        return []
    pages = list(bucket_dir.glob("*.md"))
    if bucket_dir.name in NESTED_BUCKET_DIRS:
        pages.extend(bucket_dir.glob("*/*.md"))
    return sorted(pages)
