"""Shared helpers for reading and editing ADMIN task pages.

Extracted from `set-task-status` so `set-task-priority` and later tools edit
frontmatter the same way: line-based, preserving every untouched line, key
order, and the page body byte-for-byte. No YAML library — the vault's
frontmatter is flat `key: value` lines, and a round-trip through a YAML
dumper would reformat fields no one asked to change.
"""

from __future__ import annotations

import sys
from pathlib import Path


def resolve_task(wiki_root: Path, title: str) -> Path | None:
    """Return the admin page for `title`, or None (printing near-matches)."""
    path = wiki_root / "admin" / f"{title}.md"
    if path.exists():
        return path
    needle = title.lower()
    hits = [p.stem for p in sorted((wiki_root / "admin").glob("*.md"))
            if needle in p.stem.lower()]
    print(f"Error: no admin task named {title!r}.", file=sys.stderr)
    if hits:
        print("Did you mean:", file=sys.stderr)
        for hit in hits[:5]:
            print(f"  {hit}", file=sys.stderr)
    return None


def split_frontmatter(text: str) -> tuple[list[str], int, int]:
    """Return (lines, fm_start, fm_end) — indices of the `---` fences, or (-1,-1)."""
    lines = text.splitlines(keepends=True)
    fences = [i for i, ln in enumerate(lines) if ln.rstrip("\n") == "---"]
    if len(fences) < 2:
        return lines, -1, -1
    return lines, fences[0], fences[1]


def read_fields(text: str) -> dict[str, str]:
    """Flat `key: value` frontmatter as a dict (values stripped, raw text)."""
    lines, start, end = split_frontmatter(text)
    fields: dict[str, str] = {}
    if start == -1:
        return fields
    for line in lines[start + 1:end]:
        if line[:1] in (" ", "\t", "-") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def set_fields(text: str, updates: dict[str, str | None]) -> str:
    """Return `text` with frontmatter `updates` applied.

    A string value replaces the key's line in place, or is appended just
    before the closing fence when the key is absent. A None value removes the
    key. Everything else is preserved exactly.

    Raises:
        ValueError: If the page has no frontmatter block.
    """
    lines, start, end = split_frontmatter(text)
    if start == -1:
        raise ValueError("no YAML frontmatter")

    index: dict[str, int] = {}
    for i in range(start + 1, end):
        line = lines[i]
        if line[:1] in (" ", "\t", "-") or ":" not in line:
            continue
        index.setdefault(line.partition(":")[0].strip(), i)

    removed: set[int] = set()
    appended: list[str] = []
    for key, value in updates.items():
        if value is None:
            if key in index:
                removed.add(index[key])
            continue
        new_line = f"{key}: {value}\n"
        if key in index:
            lines[index[key]] = new_line
        else:
            appended.append(new_line)

    out = [ln for i, ln in enumerate(lines[:end]) if i not in removed]
    return "".join(out + appended + lines[end:])
