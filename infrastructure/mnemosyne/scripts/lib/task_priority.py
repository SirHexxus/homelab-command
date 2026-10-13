#!/usr/bin/env python3
"""Canonical ADMIN task-priority model — single source of truth.

The model lives in the vault at `schema/priority.json` (machine-readable
companion to `schema/15-admin-task-priority.md`): the LOW < MEDIUM < HIGH <
CRITICAL scale, the urgency x impact -> priority matrix, the per-priority
attention windows, and the deadline-escalation thresholds. Every reader of
`urgency:` / `impact:` / `priority:` / `reviewed:` — `set-task-priority`,
`next-tasks`, `daily-digest`, `check-frontmatter-types`,
`report-task-throughput` — resolves them through this module, so the matrix
can change in one place.

Fail-soft by design (mirrors lib/task_status.py): if the JSON is missing or
unreadable, a hard-coded copy is used so the 07:00 digest never breaks on a
vault hiccup.

Importable:
    import task_priority
    task_priority.compute_priority("HIGH", "MEDIUM")        # -> "MEDIUM"
    task_priority.is_past_window("MEDIUM", "2026-09-01", today)

CLI:
    task_priority.py --compute HIGH MEDIUM   # print the matrix result
    task_priority.py --list-levels           # levels, lowest first
    task_priority.py --dump-matrix           # "URGENCY IMPACT PRIORITY" lines
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from task_status import default_wiki_root

# Hard-coded fallback — kept in sync with schema/priority.json. Used only when
# the JSON cannot be read.
_FALLBACK = {
    "levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    "default": "MEDIUM",
    # matrix[urgency][impact] -> priority. Impact is weighted slightly above
    # urgency: CRITICAL urgency on LOW impact is only MEDIUM.
    "matrix": {
        "LOW": {"LOW": "LOW", "MEDIUM": "LOW", "HIGH": "MEDIUM", "CRITICAL": "HIGH"},
        "MEDIUM": {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "CRITICAL": "HIGH"},
        "HIGH": {"LOW": "MEDIUM", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "CRITICAL": "CRITICAL"},
        "CRITICAL": {
            "LOW": "MEDIUM", "MEDIUM": "HIGH", "HIGH": "CRITICAL", "CRITICAL": "CRITICAL",
        },
    },
    # Days from `reviewed:` before a task asks to be re-decided.
    "attention_window_days": {"CRITICAL": 1, "HIGH": 7, "MEDIUM": 30, "LOW": 90},
    # A real deadline raises effective urgency (computed, never written back).
    "escalation": {
        "high_within_days": 7,
        "critical_within_days": 0,
    },
}


def _load_model(path: Path | None = None) -> dict:
    """Read the priority model JSON, falling back to the embedded copy."""
    if path is None:
        path = default_wiki_root() / "schema" / "priority.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        # Expected until schema/priority.json lands in the vault — stay quiet.
        return _FALLBACK
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: cannot read {path} ({exc}); using built-in priority "
              f"model", file=sys.stderr)
        return _FALLBACK
    # Tolerate a partial file: backfill any missing key from the fallback.
    return {key: data.get(key, value) for key, value in _FALLBACK.items()}


_MODEL = _load_model()


def reload_model(wiki_root: Path) -> None:
    """Re-read the model from `wiki_root`, rebinding the module global.

    Callers that accept an explicit --wiki-root must call this after parsing
    args, mirroring task_status.reload_vocab.
    """
    global _MODEL
    _MODEL = _load_model(Path(wiki_root) / "schema" / "priority.json")


def levels() -> list[str]:
    """Priority levels, lowest first."""
    return list(_MODEL["levels"])


def rank(level: str | None) -> int:
    """Position of `level` on the scale (LOW=0 …); -1 for null/unknown."""
    norm = normalize(level)
    return _MODEL["levels"].index(norm) if norm else -1


def normalize(level: str | None) -> str | None:
    """Canonical upper-case level, or None for null/empty/unknown values."""
    word = (level or "").strip().upper()
    return word if word in _MODEL["levels"] else None


def is_null(value: str | None) -> bool:
    """True for an absent, empty, or literal-`null` frontmatter value."""
    return (value or "").strip().lower() in ("", "null", "~")


def compute_priority(urgency: str | None, impact: str | None) -> str | None:
    """Matrix lookup of urgency x impact; None if either input is unset."""
    u, i = normalize(urgency), normalize(impact)
    if u is None or i is None:
        return None
    return _MODEL["matrix"][u][i]


def parse_due(raw: str | None) -> date | None:
    """Calendar date of a `due:` value (YYYY-MM-DD or YYYY-MM-DDTHH:MM)."""
    if is_null(raw):
        return None
    text = raw.strip().strip("'\"")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def is_valid_due(raw: str | None) -> bool:
    """True for null, YYYY-MM-DD, or YYYY-MM-DDTHH:MM."""
    if is_null(raw):
        return True
    text = raw.strip().strip("'\"")
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M"):
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    return False


def effective_urgency(urgency: str | None, due: str | None, today: date) -> str | None:
    """Urgency raised by a real deadline's proximity. Never written back.

    Due today or past -> CRITICAL; due within the escalation window -> at
    least HIGH. Without a deadline this is just the stored urgency.
    """
    current = normalize(urgency)
    due_date = parse_due(due)
    if due_date is None:
        return current
    esc = _MODEL["escalation"]
    days_left = (due_date - today).days
    floor = None
    if days_left <= esc["critical_within_days"]:
        floor = "CRITICAL"
    elif days_left <= esc["high_within_days"]:
        floor = "HIGH"
    if floor is None:
        return current
    return floor if rank(floor) > rank(current) else current


def effective_priority(
    urgency: str | None,
    impact: str | None,
    due: str | None,
    today: date,
) -> str | None:
    """Matrix result using deadline-escalated urgency (reports only).

    A task with a deadline but no impact set is scored as default impact, so
    a real deadline is never hidden by missing triage.
    """
    eff_u = effective_urgency(urgency, due, today)
    imp = impact
    if normalize(imp) is None and parse_due(due) is not None:
        imp = _MODEL["default"]
    return compute_priority(eff_u, imp)


def window_days(priority: str | None) -> int:
    """Attention window for `priority`; the default level's when unset."""
    level = normalize(priority) or _MODEL["default"]
    return int(_MODEL["attention_window_days"][level])


def parse_reviewed(raw: str | None) -> date | None:
    """Date of a `reviewed:` value, or None when unreviewed/invalid."""
    if is_null(raw):
        return None
    try:
        return date.fromisoformat(raw.strip().strip("'\"")[:10])
    except ValueError:
        return None


def is_unreviewed(reviewed: str | None) -> bool:
    """True when James has never made a recorded decision on the task."""
    return parse_reviewed(reviewed) is None


def window_ends(priority: str | None, reviewed: str | None) -> date | None:
    """Last day inside the attention window; None when unreviewed."""
    reviewed_on = parse_reviewed(reviewed)
    if reviewed_on is None:
        return None
    return reviewed_on + timedelta(days=window_days(priority))


def is_past_window(priority: str | None, reviewed: str | None, today: date) -> bool:
    """True when the task should ask to be re-decided.

    Unreviewed tasks count as past their window.
    """
    ends = window_ends(priority, reviewed)
    return ends is None or today > ends


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--compute", nargs=2, metavar=("URGENCY", "IMPACT"),
                       help="print the priority for an urgency/impact pair")
    group.add_argument("--list-levels", action="store_true",
                       help="print levels, lowest first, one per line")
    group.add_argument("--dump-matrix", action="store_true",
                       help="print every 'URGENCY IMPACT PRIORITY' cell (for bash)")
    parser.add_argument("--wiki-root", type=Path, default=None, metavar="DIR",
                        help="read schema/priority.json from this wiki root")
    args = parser.parse_args()

    if args.wiki_root is not None:
        reload_model(args.wiki_root)

    if args.list_levels:
        for level in levels():
            print(level)
        return 0
    if args.dump_matrix:
        for urgency in levels():
            for impact in levels():
                print(f"{urgency} {impact} {compute_priority(urgency, impact)}")
        return 0

    urgency, impact = args.compute
    result = compute_priority(urgency, impact)
    if result is None:
        print(f"Error: urgency and impact must each be one of "
              f"{', '.join(levels())}", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
