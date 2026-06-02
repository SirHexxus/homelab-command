#!/usr/bin/env python3
"""Deliver the daily digest to Telegram — text + voice note.

Text goes through `hermes send --to telegram:<target> --file <text>` so
the existing gateway is exercised. Voice goes through a direct Telegram
Bot API `sendVoice` call because the Hermes-Agent gateway does not have
a voice-attachment surface (Day 1 finding, 2026-05-29).

Reads:
    TELEGRAM_BOT_TOKEN     (required for voice)
    TELEGRAM_HOME_CHANNEL  (chat_id for the home target; required for voice)
    HERMES_BIN             (path to the hermes CLI; default 'hermes')
    HERMES_SEND_TARGET     (e.g. 'telegram:James'; default 'telegram')

Args:
    --text PATH    Markdown text file to send as the text message (required).
    --voice PATH   OGG/Opus voice note (required).
    --caption STR  Optional caption for the voice note (default: empty).
    --no-voice     Skip the voice send (text only).
    --no-text      Skip the text send (voice only). Order is text-then-voice;
                   --no-text + --voice still sends the voice.

Exit codes:
    0   ok (both sends succeeded — or the skipped one isn't requested)
    1   usage error
    11  text delivery failed
    12  voice delivery failed (text succeeded)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TELEGRAM_SEND_VOICE_URL = "https://api.telegram.org/bot{token}/sendVoice"
REQUEST_TIMEOUT_SECONDS = 30

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_TEXT_FAILED = 11
EXIT_VOICE_FAILED = 12


def send_text_via_hermes(text_path: Path, target: str, hermes_bin: str) -> bool:
    """Invoke `hermes send --to <target> --file <path>`. True on exit 0."""
    cmd = [hermes_bin, "send", "--to", target, "--file", str(text_path)]
    result = subprocess.run(cmd, check=False, capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        return False
    return True


def send_voice_via_telegram(
    voice_path: Path, chat_id: str, token: str, caption: str
) -> bool:
    """POST the OGG/Opus file to Telegram sendVoice as multipart/form-data."""
    boundary = "----hermesAgentDailyDigestBoundary"
    body = bytearray()

    def add_field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    add_field("chat_id", chat_id)
    if caption:
        add_field("caption", caption)

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            'Content-Disposition: form-data; name="voice"; '
            f'filename="{voice_path.name}"\r\n'
            "Content-Type: audio/ogg\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(voice_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        TELEGRAM_SEND_VOICE_URL.format(token=token),
        data=bytes(body),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"telegram sendVoice failed: {exc}", file=sys.stderr)
        return False

    if not payload.get("ok"):
        print(f"telegram sendVoice rejected: {payload}", file=sys.stderr)
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deliver digest to Telegram.")
    parser.add_argument("--text", required=True, help="Markdown text file.")
    parser.add_argument("--voice", required=True, help="OGG/Opus voice note.")
    parser.add_argument("--caption", default="", help="Voice note caption.")
    parser.add_argument("--no-voice", action="store_true", help="Skip voice send.")
    parser.add_argument("--no-text", action="store_true", help="Skip text send.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    text_path = Path(args.text)
    voice_path = Path(args.voice)

    if not args.no_text and not text_path.is_file():
        print(f"error: text file not found: {text_path}", file=sys.stderr)
        return EXIT_USAGE
    if not args.no_voice and not voice_path.is_file():
        print(f"error: voice file not found: {voice_path}", file=sys.stderr)
        return EXIT_USAGE

    target = os.environ.get("HERMES_SEND_TARGET", "telegram").strip() or "telegram"
    hermes_bin = os.environ.get("HERMES_BIN", "hermes").strip() or "hermes"

    text_ok = True
    if not args.no_text:
        text_ok = send_text_via_hermes(text_path, target, hermes_bin)
        if not text_ok:
            return EXIT_TEXT_FAILED
        print(f"Text delivered via {hermes_bin} send --to {target}")

    if not args.no_voice:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_HOME_CHANNEL", "").strip()
        if not (token and chat_id):
            print(
                "error: TELEGRAM_BOT_TOKEN / TELEGRAM_HOME_CHANNEL unset",
                file=sys.stderr,
            )
            return EXIT_VOICE_FAILED
        if not send_voice_via_telegram(voice_path, chat_id, token, args.caption):
            return EXIT_VOICE_FAILED
        print(f"Voice delivered via Telegram Bot API to chat {chat_id}")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
