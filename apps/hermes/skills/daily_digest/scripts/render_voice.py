#!/usr/bin/env python3
"""Render text to an OGG/Opus voice note via Gemini TTS (Leda voice).

Calls the gemini-2.5-flash-preview-tts model with responseModalities=[AUDIO]
and prebuiltVoiceConfig.voiceName=Leda. Decodes the returned PCM (s16le,
24kHz mono) and re-encodes to OGG/Opus via ffmpeg for Telegram delivery.

Reads:
    GOOGLE_API_KEY (required)

Args:
    --input PATH    Markdown / text file to read aloud (required).
    --output PATH   Where to write the OGG/Opus file (required).
    --voice NAME    Voice name (default: Leda).
    --model NAME    TTS model (default: gemini-2.5-flash-preview-tts).
    --bitrate K     Opus bitrate, e.g. 32k (default).
    --max-chars N   Truncate input over N characters (default 4000).

Exit codes:
    0  ok (output written)
    1  usage error
    8  GOOGLE_API_KEY unset
    9  Gemini TTS request failed
   10  ffmpeg not available / encode failed
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

GEMINI_TTS_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
REQUEST_TIMEOUT_SECONDS = 60

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_KEY = 8
EXIT_TTS_FAILED = 9
EXIT_ENCODE_FAILED = 10


def strip_frontmatter(text: str) -> str:
    """Strip a leading YAML frontmatter block. Pass-through if absent."""
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2].lstrip()


def clean_for_speech(text: str) -> str:
    """Strip markdown structure that doesn't read well aloud.

    Wikilinks [[Page Title]] -> Page Title; headings (#) lose the prefix;
    list bullets are kept (TTS reads them naturally with the punctuation).
    """
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def call_gemini_tts(text: str, voice: str, model: str, api_key: str) -> bytes | None:
    """Returns raw PCM bytes (s16le, 24kHz mono) or None on failure."""
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
            },
        },
    }
    req = urllib.request.Request(
        GEMINI_TTS_URL.format(model=model),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    try:
        inline = body["candidates"][0]["content"]["parts"][0]["inlineData"]
        data_b64 = inline["data"]
    except (KeyError, IndexError, TypeError):
        return None

    try:
        return base64.b64decode(data_b64)
    except (ValueError, TypeError):
        return None


def encode_to_opus(pcm_bytes: bytes, output: Path, bitrate: str) -> bool:
    """PCM s16le 24kHz mono -> OGG/Opus via ffmpeg. False on failure."""
    if shutil.which("ffmpeg") is None:
        print("error: ffmpeg not found on PATH", file=sys.stderr)
        return False

    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as tmp:
        tmp.write(pcm_bytes)
        pcm_path = Path(tmp.name)

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "s16le", "-ar", "24000", "-ac", "1",
                "-i", str(pcm_path),
                "-c:a", "libopus", "-b:a", bitrate,
                str(output),
            ],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
            return False
    finally:
        pcm_path.unlink(missing_ok=True)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render text to OGG/Opus via Gemini TTS.")
    parser.add_argument("--input", required=True, help="Input text/markdown file.")
    parser.add_argument("--output", required=True, help="Output OGG/Opus path.")
    parser.add_argument("--voice", default="Leda", help="Gemini voice name (default Leda).")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-preview-tts",
        help="Gemini TTS model.",
    )
    parser.add_argument("--bitrate", default="32k", help="Opus bitrate (default 32k).")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Truncate input beyond this many characters (default 4000).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("error: GOOGLE_API_KEY unset", file=sys.stderr)
        return EXIT_NO_KEY

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return EXIT_USAGE

    raw = input_path.read_text(encoding="utf-8")
    speakable = clean_for_speech(strip_frontmatter(raw))
    if not speakable:
        print("error: input is empty after stripping frontmatter / markup", file=sys.stderr)
        return EXIT_USAGE

    if len(speakable) > args.max_chars:
        speakable = speakable[: args.max_chars].rsplit(" ", 1)[0] + " …"

    pcm = call_gemini_tts(speakable, args.voice, args.model, api_key)
    if pcm is None:
        print("error: Gemini TTS request failed", file=sys.stderr)
        return EXIT_TTS_FAILED

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not encode_to_opus(pcm, output_path, args.bitrate):
        return EXIT_ENCODE_FAILED

    size = output_path.stat().st_size
    print(f"Wrote {size} bytes to {output_path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
