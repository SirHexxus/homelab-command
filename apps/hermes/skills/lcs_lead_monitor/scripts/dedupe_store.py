#!/usr/bin/env python3
"""Filter procurement opportunities to the new, still-actionable ones.

Deterministic gatekeeper between the agent's classified opportunities and the
memo step. Two jobs:
    1. Dedupe — drop opportunities already surfaced (keyed by agency +
       solicitation number + close date), so the same RFP appearing on multiple
       portals or on consecutive days is sent once.
    2. Date sanity — drop opportunities that are expired or close sooner than a
       minimum runway (default 7 days), so James only sees actionable leads.

Reads:
    LCS_LEAD_STORE  Path to the JSON seen-store
                    (default ~/.cache/hermes/lcs_lead_store.json).

Input (stdin, or --input PATH): JSON list of opportunity objects. Each should
carry at least:
    {"agency": "...", "solicitation_number": "...", "close_date": "YYYY-MM-DD", ...}
Other fields are passed through untouched.

Args:
    --input PATH         Read opportunities from a file instead of stdin.
    --min-runway-days N  Minimum days-until-close to keep (default 7).
    --day YYYY-MM-DD     Treat this as "today" (default: actual today).
    --commit             Record the kept opportunities in the store. Without
                         this flag the store is not modified (dry run).

Emits JSON to stdout — the kept (new, in-runway) opportunities, each annotated:
    {..., "_key": "<dedupe key>", "_runway_days": <int>}

Exit codes:
    0   ok
    1   usage / malformed input

STATUS: SCAFFOLD but functional — the dedupe + date logic is real; the field
names it keys on may be tuned once real alerts are parsed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1

DEFAULT_STORE = Path.home() / ".cache" / "hermes" / "lcs_lead_store.json"


def normalize(value: str | None) -> str:
    """Lowercase, collapse whitespace, strip punctuation noise for stable keys."""
    if not value:
        return ""
    text = re.sub(r"\s+", " ", str(value).strip().lower())
    return re.sub(r"[^a-z0-9 \-]", "", text)


def dedupe_key(opp: dict) -> str:
    """Stable key = normalized agency + solicitation number + close date."""
    return "|".join(
        (
            normalize(opp.get("agency")),
            normalize(opp.get("solicitation_number")),
            normalize(opp.get("close_date")),
        )
    )


def load_store(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_store(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")


def runway_days(close_date: str | None, today: date) -> int | None:
    """Days from today to close_date; None if the date is missing/unparseable."""
    if not close_date:
        return None
    try:
        return (date.fromisoformat(str(close_date)) - today).days
    except ValueError:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dedupe + date-sanity opportunities.")
    parser.add_argument("--input", help="Read opportunities from a file (else stdin).")
    parser.add_argument("--min-runway-days", type=int, default=7)
    parser.add_argument("--day", help="Override 'today' (ISO date).")
    parser.add_argument("--commit", action="store_true", help="Persist kept items.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.day:
        try:
            today = date.fromisoformat(args.day)
        except ValueError:
            print(f"error: invalid --day: {args.day!r}", file=sys.stderr)
            return EXIT_USAGE
    else:
        today = datetime.now().astimezone().date()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    try:
        opportunities = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: malformed input JSON: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not isinstance(opportunities, list):
        print("error: input must be a JSON list of opportunities", file=sys.stderr)
        return EXIT_USAGE

    store_path = Path(os.environ.get("LCS_LEAD_STORE", str(DEFAULT_STORE))).expanduser()
    store = load_store(store_path)

    kept: list[dict] = []
    for opp in opportunities:
        if not isinstance(opp, dict):
            continue
        key = dedupe_key(opp)
        if key in store:
            continue
        runway = runway_days(opp.get("close_date"), today)
        # Keep unknown-date items (runway None) so a parse gap never silently
        # drops a real lead; the memo will flag the missing close date.
        if runway is not None and runway < args.min_runway_days:
            continue
        annotated = {**opp, "_key": key, "_runway_days": runway}
        kept.append(annotated)
        if args.commit:
            store[key] = {
                "first_seen": today.isoformat(),
                "agency": opp.get("agency"),
                "solicitation_number": opp.get("solicitation_number"),
                "close_date": opp.get("close_date"),
            }

    if args.commit:
        save_store(store_path, store)

    json.dump(kept, sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
