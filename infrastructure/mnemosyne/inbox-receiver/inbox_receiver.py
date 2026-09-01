#!/usr/bin/env python3
"""Mnemosyne inbox receiver — minimal Flask app for the interim ingest path.

Accepts IngestItem JSON payloads from n8n via POST /inbox, writes each item as
a timestamped JSON file to wiki/inbox/, then commits it under the shared mneme
commit lock. Pushing is mneme-sync's job -- this app never talks to the remote.
No LLM, no classification — that happens later via claude -p on the laptop.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import subprocess
import time
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

# The shared commit lock every mneme-* worker takes around its own
# stage+commit. Kept in sync with scripts/lib/wiki_git.py by name, not by
# import: this app ships with only Flask and no path into the scripts tree.
LOCK_NAME = "mneme-commit.lock"
LOCK_TIMEOUT = 120.0
LOCK_POLL = 0.2

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


def _rebase_in_progress() -> bool:
    """True if a halted rebase has left replay state behind."""
    git_dir = WIKI_ROOT / ".git"
    return any((git_dir / name).exists()
               for name in ("rebase-merge", "rebase-apply"))


def _detached_head() -> bool:
    """True if HEAD is not on a branch."""
    result = subprocess.run(
        ["git", "-C", str(WIKI_ROOT), "symbolic-ref", "--quiet", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode != 0


def _commit_inbox_item(rel: str, message: str) -> None:
    """Stage and commit one inbox item under the shared commit lock.

    Publishing is mneme-sync's job alone. This app used to run its own
    `git pull --rebase && git push`, unlocked, which on 2026-09-01 collided
    with a sync already rebasing: the repo was left on a detached HEAD, the
    caller got a 500 and retried, and the retry plus the re-triage of items
    the halted replay had restored turned two notes into six pages. Commit
    locally, return success, and let the next sync publish within minutes.

    Raises RuntimeError if the item could not be committed.
    """
    lock_path = WIKI_ROOT / ".git" / LOCK_NAME
    deadline = time.monotonic() + LOCK_TIMEOUT

    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o644)
    except OSError as exc:
        raise RuntimeError(f"cannot open commit lock: {exc}") from exc

    try:
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"commit lock busy after {LOCK_TIMEOUT:.0f}s"
                    ) from None
                time.sleep(LOCK_POLL)

        if _rebase_in_progress() or _detached_head():
            raise RuntimeError(
                "repo mid-rebase or on a detached HEAD; refusing to commit"
            )

        _git(["add", "--", rel])
        _git(["commit", "-q", "-m", message])
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


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

        rel = str(filepath.relative_to(WIKI_ROOT))
        try:
            _commit_inbox_item(rel, f"mneme: inbox {source} — {ts}")
        except RuntimeError as exc:
            log.error("Git commit failed: %s", exc)
            filepath.unlink(missing_ok=True)
            return jsonify({"error": "Git commit failed — item not persisted"}), 500

        log.info("Committed: %s (mneme-sync publishes)", filename)
        return jsonify({"status": "ok", "file": filename})

    return app


if __name__ == "__main__":
    if not INBOX_TOKEN:
        raise SystemExit("INBOX_TOKEN environment variable is required")
    if not WIKI_ROOT.exists():
        raise SystemExit(f"WIKI_ROOT does not exist: {WIKI_ROOT}")

    app = create_app()
    app.run(host="0.0.0.0", port=PORT)
