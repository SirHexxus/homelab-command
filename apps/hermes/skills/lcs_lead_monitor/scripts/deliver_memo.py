#!/usr/bin/env python3
"""Deliver one LCS handoff memo to James via Telegram.

Thin, text-only sibling of daily_digest/deliver_digest.py. One memo per call so
each opportunity is an individually forwardable Telegram message. Routes through
`hermes send` so the existing gateway is exercised (same as the digest text path).

Reads:
    HERMES_BIN          Path to the hermes CLI (default "hermes").
    HERMES_SEND_TARGET  Telegram target (default "telegram:James").

Args:
    --file PATH   Markdown/plain-text memo to send (required).
    --target STR  Override HERMES_SEND_TARGET for this send (optional).

Exit codes:
    0   ok
    1   usage error (file missing)
    11  delivery failed

STATUS: SCAFFOLD but functional — delivery path mirrors the working digest
sender; safe to use as soon as the gateway env is present.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_DELIVERY_FAILED = 11


def send_via_hermes(memo_path: Path, target: str, hermes_bin: str) -> bool:
    """Invoke `hermes send --to <target> --file <path>`. True on exit 0."""
    cmd = [hermes_bin, "send", "--to", target, "--file", str(memo_path)]
    result = subprocess.run(cmd, check=False, capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deliver an LCS handoff memo.")
    parser.add_argument("--file", required=True, help="Memo text file to send.")
    parser.add_argument("--target", help="Override the Telegram send target.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    memo_path = Path(args.file)
    if not memo_path.is_file():
        print(f"error: memo file not found: {memo_path}", file=sys.stderr)
        return EXIT_USAGE

    target = (
        args.target
        or os.environ.get("HERMES_SEND_TARGET", "telegram:James").strip()
        or "telegram:James"
    )
    hermes_bin = os.environ.get("HERMES_BIN", "hermes").strip() or "hermes"

    if not send_via_hermes(memo_path, target, hermes_bin):
        return EXIT_DELIVERY_FAILED

    print(f"Memo delivered via {hermes_bin} send --to {target}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
