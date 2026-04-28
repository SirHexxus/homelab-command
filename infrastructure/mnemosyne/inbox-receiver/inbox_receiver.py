#!/usr/bin/env python3
"""Mnemosyne inbox receiver — minimal Flask app for the interim ingest path.

Accepts IngestItem JSON payloads from n8n via POST /inbox, writes each item as
a timestamped JSON file to wiki/inbox/, then commits and pushes to GitHub.
No LLM, no classification — that happens later via claude -p on the laptop.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request


# ── Configuration ─────────────────────────────────────────────────────────────

WIKI_ROOT = Path(os.environ.get("WIKI_ROOT", "/opt/inbox-receiver/wiki"))
INBOX_DIR = WIKI_ROOT / "inbox"
INBOX_TOKEN = os.environ.get("INBOX_TOKEN", "")
PORT = int(os.environ.get("PORT", "8080"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


# ── Auth ──────────────────────────────────────────────────────────────────────

def _require_bearer(f):
    """Enforce Bearer token auth via INBOX_TOKEN env var."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not INBOX_TOKEN:
            log.error("INBOX_TOKEN not configured")
            return jsonify({"error": "INBOX_TOKEN not configured on server"}), 500
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != INBOX_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git(args: list[str]) -> subprocess.CompletedProcess:
    """Run a git command in WIKI_ROOT. Raises on non-zero exit."""
    result = subprocess.run(
        ["git", "-C", str(WIKI_ROOT)] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result


def _commit_and_push(filepath: Path, source: str, ts: str) -> None:
    """Stage the inbox file, commit it, and push to origin."""
    _git(["add", str(filepath.relative_to(WIKI_ROOT))])
    _git(["commit", "-m", f"mneme: inbox {source} — {ts}"])
    _git(["push"])


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Flask:
    """Create and configure the inbox-receiver Flask app."""
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/inbox")
    @_require_bearer
    def inbox():
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"error": "Request body must be JSON"}), 400

        payload: dict[str, Any] = body.get("payload", body)

        raw_content_type = payload.get("raw_content_type", "text")
        source = payload.get("source", "unknown")
        text = payload.get("text")
        file_ref = payload.get("file_ref")
        metadata = payload.get("metadata", {})
        bucket_hint = payload.get("bucket_hint")

        if not text and not file_ref:
            return jsonify({"error": "payload must include 'text' or 'file_ref'"}), 400

        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d-%H%M%S")
        uid = uuid.uuid4().hex[:8]
        filename = f"{ts}-{uid}.json"
        filepath = INBOX_DIR / filename

        item = {
            "raw_content_type": raw_content_type,
            "source": source,
            "text": text,
            "file_ref": file_ref,
            "metadata": metadata,
            "bucket_hint": bucket_hint,
            "capture_ts": now.isoformat(),
        }

        try:
            INBOX_DIR.mkdir(parents=True, exist_ok=True)
            filepath.write_text(json.dumps(item, ensure_ascii=False, indent=2))
            log.info("Wrote inbox item: %s", filename)
        except OSError as exc:
            log.error("Failed to write inbox file: %s", exc)
            return jsonify({"error": "Failed to write inbox file"}), 500

        try:
            _commit_and_push(filepath, source, ts)
            log.info("Committed and pushed: %s", filename)
        except RuntimeError as exc:
            log.error("Git operation failed: %s", exc)
            filepath.unlink(missing_ok=True)
            return jsonify({"error": "Git push failed — item not persisted"}), 500

        return jsonify({"status": "ok", "file": filename})

    return app


if __name__ == "__main__":
    if not INBOX_TOKEN:
        raise SystemExit("INBOX_TOKEN environment variable is required")
    if not WIKI_ROOT.exists():
        raise SystemExit(f"WIKI_ROOT does not exist: {WIKI_ROOT}")

    app = create_app()
    app.run(host="0.0.0.0", port=PORT)
