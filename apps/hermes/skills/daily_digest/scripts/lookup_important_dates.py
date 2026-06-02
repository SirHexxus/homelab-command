#!/usr/bin/env python3
"""Scan the wiki for birthdays, anniversaries, and ADMIN due-soon items.

Reads:
    MNEME_WIKI_PATH (default ~/mneme/wiki)

Args:
    --lookahead N  (days, default 30)
    --day YYYY-MM-DD  (default today)

Emits JSON to stdout:
    {
      "birthdays": [{"title", "date", "is_today"}],
      "anniversaries": [{"title", "date", "is_today"}],
      "admin": {
          "overdue":    [{"title", "due", "weekday", "task_type"}],
          "due_today":  [...],
          "upcoming":   [...]
      },
      "day": "YYYY-MM-DD",
      "lookahead_days": N
    }

Quiet on empty: empty lists are returned (not omitted). Exit 0 on success,
non-zero only on wiki-root resolution failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

EXIT_OK = 0
EXIT_NO_WIKI = 5

CLOSED_STATUSES = frozenset({"closed", "done", "complete", "completed", "cancelled"})


def resolve_wiki_root() -> Path:
    env_path = os.environ.get("MNEME_WIKI_PATH")
    if env_path:
        root = Path(env_path).expanduser().resolve()
    else:
        root = (Path.home() / "mneme" / "wiki").resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Wiki root does not exist or is not a directory: {root}")
    return root


def parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    return fm


def weekday_name(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%A")
    except (ValueError, TypeError):
        return ""


def next_occurrence(raw: str, today: date, horizon: date) -> date | None:
    """Resolve a YYYY-MM-DD or MM-DD value to the next occurrence in [today, horizon]."""
    if not raw or raw == "null":
        return None
    try:
        if len(raw) == 5:
            month, day = (int(p) for p in raw.split("-"))
            parsed_month, parsed_day = month, day
        else:
            parsed = date.fromisoformat(raw)
            parsed_month, parsed_day = parsed.month, parsed.day
    except (ValueError, TypeError):
        return None

    for year in (today.year, today.year + 1):
        try:
            occurrence = date(year, parsed_month, parsed_day)
        except ValueError:
            continue
        if today <= occurrence <= horizon:
            return occurrence
    return None


def collect_anchor_field(
    wiki_root: Path, today: date, horizon: date, field: str
) -> list[dict[str, str]]:
    """Generic collector for an annual-anchor frontmatter field on PERSON pages."""
    matches: list[dict[str, str]] = []
    people_dir = wiki_root / "people"
    if not people_dir.is_dir():
        return matches

    for md_file in sorted(people_dir.glob("*.md")):
        fm = parse_frontmatter(md_file)
        occurrence = next_occurrence(fm.get(field, ""), today, horizon)
        if occurrence is None:
            continue
        matches.append({
            "title": md_file.stem,
            "date": occurrence.isoformat(),
            "is_today": occurrence == today,
        })
    return matches


def collect_admin(
    wiki_root: Path, today: date, horizon: date
) -> dict[str, list[dict[str, str]]]:
    overdue: list[dict[str, str]] = []
    due_today: list[dict[str, str]] = []
    upcoming: list[dict[str, str]] = []

    admin_dir = wiki_root / "admin"
    if not admin_dir.is_dir():
        return {"overdue": overdue, "due_today": due_today, "upcoming": upcoming}

    for md_file in sorted(admin_dir.glob("*.md")):
        fm = parse_frontmatter(md_file)
        if fm.get("status", "").lower() in CLOSED_STATUSES:
            continue
        raw_due = fm.get("due", "")
        if not raw_due or raw_due == "null":
            continue
        try:
            due_date = date.fromisoformat(raw_due)
        except ValueError:
            continue

        entry = {
            "title": md_file.stem,
            "due": raw_due,
            "weekday": weekday_name(raw_due),
            "task_type": fm.get("task_type", "user"),
        }
        if due_date < today:
            overdue.append(entry)
        elif due_date == today:
            due_today.append(entry)
        elif due_date <= horizon:
            upcoming.append(entry)

    return {"overdue": overdue, "due_today": due_today, "upcoming": upcoming}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan wiki for important dates.")
    parser.add_argument("--lookahead", type=int, default=30, help="Window in days.")
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

    horizon = today + timedelta(days=args.lookahead)

    result = {
        "birthdays": collect_anchor_field(wiki_root, today, horizon, "birthday"),
        "anniversaries": collect_anchor_field(wiki_root, today, horizon, "anniversary"),
        "admin": collect_admin(wiki_root, today, horizon),
        "day": today.isoformat(),
        "lookahead_days": args.lookahead,
    }
    json.dump(result, sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
