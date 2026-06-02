#!/usr/bin/env python3
"""Read the latest entry from the weight log and report nudge state.

Reads:
    MNEME_WIKI_PATH (default ~/mneme/wiki)
    The page journal/weight-log.md, which contains a markdown table:

        | Date       | Weight (lbs) | Notes               |
        |------------|--------------|---------------------|
        | 2026-05-28 | 249.4        | morning weigh-in    |

    Newest entries at the top (project convention).

Args:
    --day YYYY-MM-DD  (default today)

Emits JSON to stdout:
    {
      "last_entry": {"date": "YYYY-MM-DD", "weight": 249.4, "notes": "..."},
      "gap_days": 1,
      "nudge": false,
      "logged_today": false,
      "logged_yesterday": true,
      "day": "YYYY-MM-DD"
    }

`nudge` is true when the most recent entry is older than yesterday (i.e.
gap_days >= 2). When the log is empty or missing, last_entry is null and
nudge is true. Exit 0 on success, EXIT_NO_WIKI if the wiki root is gone.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

EXIT_OK = 0
EXIT_NO_WIKI = 5

ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([0-9.]+)\s*\|\s*(.*?)\s*\|\s*$")
WEIGHT_LOG_REL = "journal/weight-log.md"


def resolve_wiki_root() -> Path:
    env_path = os.environ.get("MNEME_WIKI_PATH")
    if env_path:
        root = Path(env_path).expanduser().resolve()
    else:
        root = (Path.home() / "mneme" / "wiki").resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Wiki root does not exist or is not a directory: {root}")
    return root


def parse_entries(text: str) -> list[tuple[date, float, str]]:
    """Parse all '| YYYY-MM-DD | weight | notes |' rows. Latest first."""
    entries: list[tuple[date, float, str]] = []
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        try:
            entry_date = date.fromisoformat(match.group(1))
            weight = float(match.group(2))
        except ValueError:
            continue
        entries.append((entry_date, weight, match.group(3).strip()))
    entries.sort(key=lambda e: e[0], reverse=True)
    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read latest weight-log entry.")
    parser.add_argument("--day", help="ISO date (default: today).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        wiki_root = resolve_wiki_root()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NO_WIKI

    if args.day:
        try:
            today = date.fromisoformat(args.day)
        except ValueError:
            print(f"error: invalid --day: {args.day!r}", file=sys.stderr)
            return 1
    else:
        today = datetime.now().astimezone().date()

    log_path = wiki_root / WEIGHT_LOG_REL
    entries: list[tuple[date, float, str]] = []
    if log_path.is_file():
        try:
            entries = parse_entries(log_path.read_text(encoding="utf-8"))
        except OSError:
            entries = []

    yesterday = today - timedelta(days=1)
    logged_today = any(e[0] == today for e in entries)
    logged_yesterday = any(e[0] == yesterday for e in entries)

    if entries:
        latest_date, latest_weight, latest_notes = entries[0]
        last_entry = {
            "date": latest_date.isoformat(),
            "weight": latest_weight,
            "notes": latest_notes,
        }
        gap_days = (today - latest_date).days
    else:
        last_entry = None
        gap_days = -1

    nudge = (last_entry is None) or (gap_days >= 2)

    json.dump({
        "last_entry": last_entry,
        "gap_days": gap_days,
        "nudge": nudge,
        "logged_today": logged_today,
        "logged_yesterday": logged_yesterday,
        "day": today.isoformat(),
    }, sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
