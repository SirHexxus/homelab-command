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
import sys
from pathlib import Path

# Hard-coded fallback — kept in sync with schema/statuses.json. Used only when
# the JSON cannot be read, so a closed task is never mistaken for an open one.
_FALLBACK = {
    "active": ["Pending", "Active", "Blocked"],
    "closed": ["Done", "Completed", "Skipped", "Closed", "Cancelled"],
}

DEFAULT_WIKI_ROOT = Path.home() / "mneme" / "wiki"
_VOCAB_PATH = DEFAULT_WIKI_ROOT / "schema" / "statuses.json"


def _load_vocab(path: Path = _VOCAB_PATH) -> dict[str, list[str]]:
    """Read the status vocabulary JSON, falling back to the embedded copy."""
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
