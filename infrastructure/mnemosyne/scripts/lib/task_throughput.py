#!/usr/bin/env python3
"""ADMIN task throughput — are tasks actually getting done?

The metric behind the priority reframe (Rule #9: measure the result that
matters). Per priority level: open, unreviewed, and past-window counts now;
tasks opened and closed in the last week; and median days from `created` to
`closed` over a rolling four weeks.

Closed tasks are gathered from every place one can live, de-duplicated by
title: `admin/` (closed but not yet swept), `archive/admin-closed/` on disk,
and `mneme_archived_pages` in Postgres (authoritative — the disk archive is
pruned). Postgres is fail-soft: without it the numbers are marked partial.
Only tasks closed with a `closed:` date count, so history starts at rollout.

Used by `maintenance/report-task-throughput` (weekly report, via --markdown)
and by `daily-digest` (Sunday summary, via compute() + digest_summary()).

CLI:
    task_throughput.py --markdown [--wiki-root DIR]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

import admin_page
import admin_tasks
import task_priority
import task_status

WEEK_DAYS = 7
MEDIAN_DAYS = 28
UNTRIAGED = "untriaged"


def _parse_date(raw: str | None) -> date | None:
    if task_priority.is_null(raw):
        return None
    try:
        return date.fromisoformat(raw.strip().strip("'\"")[:10])
    except ValueError:
        return None


def _closed_record(title: str, fields: dict) -> dict | None:
    """A closed-task record, or None when it has no usable `closed:` date."""
    closed = _parse_date(fields.get("closed"))
    if closed is None or not task_status.is_closed(fields.get("status", "")):
        return None
    return {
        "title": title,
        "status": (fields.get("status") or "").strip(),
        "created": _parse_date(fields.get("created")),
        "closed": closed,
        "priority": task_priority.normalize(fields.get("priority")) or UNTRIAGED,
    }


def _closed_from_disk(wiki_root: Path) -> list[dict]:
    records = []
    for folder in (wiki_root / "admin", wiki_root / "archive" / "admin-closed"):
        for path in sorted(folder.glob("*.md")):
            fields = admin_page.read_fields(path.read_text(encoding="utf-8"))
            record = _closed_record(path.stem, fields)
            if record:
                records.append(record)
    return records


def _closed_from_postgres(since: date) -> list[dict] | None:
    """Archived ADMIN rows closed on/after `since`; None if Postgres fails."""
    try:
        import mneme_pg
        import psycopg2
    except ImportError as exc:
        print(f"Warning: Postgres client unavailable ({exc}); throughput is "
              f"partial", file=sys.stderr)
        return None
    # Creds (RuntimeError/ValueError from mneme_pg), IO, and every driver error.
    pg_errors = (psycopg2.Error, RuntimeError, ValueError, OSError)
    try:
        conn = mneme_pg.connect()
    except pg_errors as exc:
        print(f"Warning: Postgres unavailable ({exc}); throughput is partial",
              file=sys.stderr)
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title, frontmatter FROM mneme_archived_pages "
                "WHERE bucket = 'ADMIN' AND frontmatter ? 'closed' "
                "AND frontmatter->>'closed' >= %s",
                (since.isoformat(),),
            )
            rows = cur.fetchall()
    except pg_errors as exc:
        print(f"Warning: Postgres query failed ({exc}); throughput is partial",
              file=sys.stderr)
        return None
    finally:
        conn.close()
    records = []
    for title, fm in rows:
        fields = {k: str(v) for k, v in (fm or {}).items()}
        record = _closed_record(title, fields)
        if record:
            records.append(record)
    return records


def collect_closed(
    wiki_root: Path,
    since: date,
    use_postgres: bool = True,
) -> tuple[list[dict], bool]:
    """Closed tasks with closed >= `since`, de-duplicated. (records, complete).

    `use_postgres=False` reads the disk only (tests); the result then counts
    as complete because nothing was expected from the database.
    """
    by_title: dict[str, dict] = {}
    pg = _closed_from_postgres(since) if use_postgres else []
    for record in (pg or []) + _closed_from_disk(wiki_root):
        if record["closed"] >= since:
            by_title[record["title"]] = record
    return list(by_title.values()), pg is not None


def compute(wiki_root: Path, today: date, use_postgres: bool = True) -> dict:
    """Throughput statistics, keyed by priority level (plus UNTRIAGED)."""
    week_start = today - timedelta(days=WEEK_DAYS)
    median_start = today - timedelta(days=MEDIAN_DAYS)
    open_tasks = admin_tasks.load_open_tasks(wiki_root, today)
    closed, complete = collect_closed(wiki_root, median_start, use_postgres)

    rows = {level: {"open": 0, "unreviewed": 0, "past_window": 0, "opened": 0,
                    "closed": 0, "cancelled": 0, "close_days": []}
            for level in [*reversed(task_priority.levels()), UNTRIAGED]}

    for task in open_tasks:
        row = rows[task["priority"] or UNTRIAGED]
        row["open"] += 1
        row["unreviewed"] += task["unreviewed"]
        row["past_window"] += task["past_window"] and not task["unreviewed"]
        created = _parse_date(task["created"])
        row["opened"] += bool(created and created > week_start)

    for record in closed:
        row = rows[record["priority"]]
        created = record["created"]
        if created and created > week_start:
            row["opened"] += 1
        if record["closed"] > week_start:
            row["closed"] += 1
            row["cancelled"] += record["status"].lower() in ("cancelled", "skipped")
        if created:
            row["close_days"].append((record["closed"] - created).days)

    for row in rows.values():
        days = row.pop("close_days")
        row["median_days"] = statistics.median(days) if days else None

    totals = {key: sum(r[key] for r in rows.values())
              for key in ("open", "unreviewed", "past_window", "opened", "closed",
                          "cancelled")}
    return {"today": today, "rows": rows, "totals": totals, "complete": complete}


def to_markdown(stats: dict) -> str:
    """Report body (the shared write_report adds frontmatter)."""
    today = stats["today"].isoformat()
    t = stats["totals"]
    lines = [
        f"# Task Throughput Report — {today}",
        "",
        f"**This week:** {t['opened']} opened, {t['closed']} closed "
        f"({t['cancelled']} of them cancelled or skipped) · "
        f"**Open now:** {t['open']} · **To re-decide:** "
        f"{t['unreviewed']} unreviewed, {t['past_window']} past their window",
        "",
        "| Priority | Open | Unreviewed | Past window | Opened (7d) | Closed (7d) "
        "| Median days to close (28d) |",
        "|---|---|---|---|---|---|---|",
    ]
    for level, r in stats["rows"].items():
        median = "—" if r["median_days"] is None else f"{r['median_days']:g}"
        lines.append(f"| {level} | {r['open']} | {r['unreviewed']} | {r['past_window']} "
                     f"| {r['opened']} | {r['closed']} | {median} |")
    lines += [
        "",
        "Closed counts only include tasks closed through `set-task-status`, which "
        "stamps `closed:` — measurement started with the priority reframe "
        "(2026-10). Cancelling is a legitimate close.",
    ]
    if not stats["complete"]:
        lines += ["", "**Partial:** Postgres was unavailable, so tasks already swept "
                  "out of the disk archive are missing from the closed counts."]
    lines += ["", "---", "*Generated by report-task-throughput*"]
    return "\n".join(lines)


def digest_summary(stats: dict) -> str:
    """Plain-text input lines for the digest's Sunday summary."""
    t = stats["totals"]
    parts = [f"Last 7 days: {t['opened']} tasks opened, {t['closed']} closed "
             f"({t['cancelled']} cancelled or skipped). {t['open']} open now; "
             f"{t['unreviewed'] + t['past_window']} waiting to be re-decided."]
    medians = [f"{level} {r['median_days']:g} days"
               for level, r in stats["rows"].items()
               if r["median_days"] is not None]
    if medians:
        parts.append("Median time to close (28 days), by priority: "
                     + ", ".join(medians) + ".")
    if not stats["complete"]:
        parts.append("(Partial — archive database unavailable.)")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--markdown", action="store_true", required=True,
                        help="print the report body as Markdown")
    parser.add_argument("--wiki-root", type=Path, default=task_status.default_wiki_root(),
                        metavar="DIR", help="wiki root")
    args = parser.parse_args()
    task_status.reload_vocab(args.wiki_root)
    task_priority.reload_model(args.wiki_root)
    print(to_markdown(compute(args.wiki_root, date.today())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
