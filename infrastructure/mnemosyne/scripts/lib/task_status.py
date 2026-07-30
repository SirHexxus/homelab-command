#!/usr/bin/env python3
"""Canonical ADMIN task-status vocabulary — single source of truth.

The vocabulary lives in the vault at `schema/statuses.json` (machine-readable
companion to `schema/06-yaml-frontmatter.md`). Every reader of an ADMIN task's
`status:` field — `daily-digest`, `archive-wiki`, `set-task-status`, and the
bash `wiki-common.sh` (via `--list-closed`) — resolves "is this task closed?"
through this module, so the three historically-divergent definitions can no
longer drift apart.

Fail-soft by design (mirrors lib/mneme_log.py / lib/embeddings.py): if the JSON
is missing or unreadable, a hard-coded copy of the superset is used so the 07:00
digest never breaks on a vault hiccup.

Importable:
    import task_status
    if task_status.is_closed(fm.get("status", "")):  # case-insensitive
        ...

CLI (for the bash consumer):
    task_status.py --list-closed   # closed words, lower-cased, one per line
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Hard-coded fallback — kept in sync with schema/statuses.json. Used only when
# the JSON cannot be read, so a closed task is never mistaken for an open one.
_FALLBACK = {
    "active": ["Pending", "Active", "Blocked"],
    "closed": ["Done", "Completed", "Skipped", "Closed", "Cancelled"],
}

def default_wiki_root() -> Path:
    """Wiki root from $MNEME_WIKI_PATH, else ~/mneme/wiki.

    Mirrors lib/raw_source.py::resolve_wiki_root, but never raises: callers use
    this as an argparse default, so a missing root must surface at use time (or
    via their own validation) rather than at import.
    """
    env_path = os.environ.get("MNEME_WIKI_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / "mneme" / "wiki"


DEFAULT_WIKI_ROOT = default_wiki_root()


def _load_vocab(path: Path | None = None) -> dict[str, list[str]]:
    """Read the status vocabulary JSON, falling back to the embedded copy."""
    if path is None:
        path = default_wiki_root() / "schema" / "statuses.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: cannot read {path} ({exc}); using built-in status "
              f"vocabulary", file=sys.stderr)
        return _FALLBACK
    # Tolerate a partial file: backfill either missing key from the fallback.
    return {
        "active": data.get("active", _FALLBACK["active"]),
        "closed": data.get("closed", _FALLBACK["closed"]),
    }


_VOCAB = _load_vocab()

# Lower-cased frozensets for case-insensitive membership tests.
CLOSED_STATUSES: frozenset[str] = frozenset(s.lower() for s in _VOCAB["closed"])
ACTIVE_STATUSES: frozenset[str] = frozenset(s.lower() for s in _VOCAB["active"])
ALL_STATUSES: frozenset[str] = CLOSED_STATUSES | ACTIVE_STATUSES

# any-case -> canonical Title-case form, e.g. "done" -> "Done".
_CANONICAL: dict[str, str] = {
    s.lower(): s for s in (*_VOCAB["closed"], *_VOCAB["active"])
}


def reload_vocab(wiki_root: Path) -> None:
    """Re-read the vocabulary from `wiki_root`, rebinding the module globals.

    Import-time resolution honours $MNEME_WIKI_PATH, which covers the worker
    units. Callers that accept an explicit --wiki-root must call this after
    parsing args, otherwise a root that differs from the environment would be
    scored against the wrong vocabulary.
    """
    global _VOCAB, CLOSED_STATUSES, ACTIVE_STATUSES, ALL_STATUSES, _CANONICAL
    _VOCAB = _load_vocab(Path(wiki_root) / "schema" / "statuses.json")
    CLOSED_STATUSES = frozenset(s.lower() for s in _VOCAB["closed"])
    ACTIVE_STATUSES = frozenset(s.lower() for s in _VOCAB["active"])
    ALL_STATUSES = CLOSED_STATUSES | ACTIVE_STATUSES
    _CANONICAL = {s.lower(): s for s in (*_VOCAB["closed"], *_VOCAB["active"])}


def is_closed(status: str) -> bool:
    """True if `status` is any closed-state word (case- and whitespace-insensitive)."""
    return (status or "").strip().lower() in CLOSED_STATUSES


def canonical(status: str) -> str | None:
    """Canonical Title-case form of `status`, or None if it is not a known word."""
    return _CANONICAL.get((status or "").strip().lower())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-closed", action="store_true",
                       help="print closed-state words (lower-cased, one per line)")
    group.add_argument("--list-active", action="store_true",
                       help="print active-state words (lower-cased, one per line)")
    args = parser.parse_args()

    words = sorted(CLOSED_STATUSES if args.list_closed else ACTIVE_STATUSES)
    for word in words:
        print(word)
    return 0


if __name__ == "__main__":
    sys.exit(main())
