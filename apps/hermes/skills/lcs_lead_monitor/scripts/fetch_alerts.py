#!/usr/bin/env python3
"""Pull unseen procurement-alert emails from the bids intake mailbox.

This is the deterministic *fetch* half of the lcs_lead_monitor skill. It does
not classify, score, or summarise — it only returns raw alert emails for the
agent to reason over (mirrors the daily_digest "scripts fetch, agent judges"
split).

Reads:
    BIDS_IMAP_HOST     IMAP server for bids@hexxusweb.com (required for IMAP mode)
    BIDS_IMAP_PORT     IMAP port (default 993)
    BIDS_IMAP_USER     Mailbox username (required for IMAP mode)
    BIDS_IMAP_PASS     Mailbox password (required for IMAP mode)
    BIDS_IMAP_MAILBOX  Folder to read (default "INBOX")

Args:
    --since YYYY-MM-DD  Only fetch messages received on/after this date (optional).
    --mark-seen         Mark fetched messages \\Seen so they are not re-pulled.
    --fixture PATH      DEV MODE: read alerts from a JSON file instead of IMAP.
                        The file must already match the output schema below.
                        Lets Week-1 development and tests run with no live mailbox.
    --limit N           Cap the number of messages returned (default: no cap).

Emits JSON to stdout — a list of raw alert envelopes:
    [
      {
        "portal":      "cal-eprocure" | "planetbids" | "bidnet" | "az-app" | "unknown",
        "subject":     "...",
        "body":        "plain-text body",
        "received":    "YYYY-MM-DD",
        "message_id":  "<...>",
        "links":       ["https://...", ...]
      },
      ...
    ]

Exit codes:
    0   ok (zero or more alerts emitted)
    1   usage error
    5   IMAP configuration missing
    6   IMAP connection / fetch error

STATUS: SCAFFOLD. IMAP fetch + portal detection are TODO (Week 1). Fixture mode
is implemented so the contract is testable now.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_CONFIG = 5
EXIT_IMAP_ERROR = 6

KNOWN_PORTAL_SENDERS = {
    # TODO (Week 1): map alert sender domains to portal labels once the first
    # real alerts land in bids@hexxusweb.com and we can see the From: domains.
    # "notifications@caleprocure.ca.gov": "cal-eprocure",
    # "noreply@bidnetdirect.com": "bidnet",
    # "...@planetbids.com": "planetbids",
    # "...@az.gov": "az-app",
}


def load_fixture(path: Path) -> list[dict]:
    """Load alert envelopes from a JSON fixture (dev/test mode)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read fixture {path}: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    if not isinstance(data, list):
        print("error: fixture must be a JSON list of alert envelopes", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)
    return data


def fetch_via_imap(since: str | None, mark_seen: bool, limit: int | None) -> list[dict]:
    """Pull unseen alert emails from the bids mailbox over IMAP.

    TODO (Week 1): implement with imaplib + email.parser.
      1. Connect IMAP4_SSL(host, port), login(user, pass), select(mailbox).
      2. SEARCH (UNSEEN [SINCE <date>]).
      3. For each id: FETCH RFC822, parse with email.message_from_bytes,
         extract subject, plain-text body, Date -> received (ISO),
         Message-ID, and URLs from the body.
      4. Classify portal from the From: domain via KNOWN_PORTAL_SENDERS.
      5. If mark_seen: STORE +FLAGS \\Seen.
    Until implemented, raise so callers fall back to --fixture in dev.
    """
    host = os.environ.get("BIDS_IMAP_HOST", "").strip()
    user = os.environ.get("BIDS_IMAP_USER", "").strip()
    password = os.environ.get("BIDS_IMAP_PASS", "").strip()
    if not (host and user and password):
        print(
            "error: BIDS_IMAP_HOST / BIDS_IMAP_USER / BIDS_IMAP_PASS unset "
            "(use --fixture for dev)",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_NO_CONFIG)
    raise NotImplementedError(
        "IMAP fetch is not implemented yet (Week 1). Run with --fixture for now."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch procurement alert emails.")
    parser.add_argument("--since", help="Only messages on/after this ISO date.")
    parser.add_argument("--mark-seen", action="store_true", help="Flag fetched as Seen.")
    parser.add_argument("--fixture", help="DEV: read alerts from a JSON file.")
    parser.add_argument("--limit", type=int, help="Cap number of alerts returned.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.fixture:
        alerts = load_fixture(Path(args.fixture).expanduser())
    else:
        alerts = fetch_via_imap(args.since, args.mark_seen, args.limit)

    if args.limit is not None:
        alerts = alerts[: args.limit]

    json.dump(alerts, sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
