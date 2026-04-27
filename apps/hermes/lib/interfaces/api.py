"""Minimal Flask HTTP interface for Hermes — POST /task, GET /health.

This is an internal service-to-service channel on VLAN 50. It is NOT the Phase 4 web UI.
Do not add user-facing features, session management, or public-facing auth here.

Routes:
  GET  /health  — no auth required; used by Ansible verify step and Uptime Kuma
  POST /task    — Bearer token auth; accepts {workflow, task, payload, context_name}
"""

from __future__ import annotations

import os
from functools import wraps
from typing import Any

from flask import Flask, jsonify, request

from lib.core.agent_loop import run_agent
from lib.core.context import load_context
from lib.core.ingest import IngestItem
import lib.skills.filesystem  # noqa: F401 — registers filesystem skills
import lib.skills.shell        # noqa: F401 — registers shell skills
import lib.skills.wiki         # noqa: F401 — registers wiki skills


# ── Auth ──────────────────────────────────────────────────────────────────────

def _require_bearer(f):
    """Decorator that enforces Bearer token auth via HERMES_API_TOKEN env var."""
    @wraps(f)
    def decorated(*args, **kwargs):
        expected = os.environ.get("HERMES_API_TOKEN", "")
        if not expected:
            return jsonify({"error": "HERMES_API_TOKEN not configured on server"}), 500
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != expected:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Task routing ──────────────────────────────────────────────────────────────

# Maps (workflow, task) → routing config for the agent loop.
# Add new workflow/task pairs here as Hermes expands to new domains.
_TASK_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("mnemosyne", "ingest"): {"task_type": "wiki_write", "prompt_template": "ingest"},
    ("mnemosyne", "query"):  {"task_type": "wiki_read",  "prompt_template": "query"},
}


def _build_ingest_prompt(item: IngestItem) -> str:
    """Build a natural-language task prompt for a wiki ingest operation."""
    parts = [
        "Ingest the following item into the Mnemosyne wiki.",
        f"Source: {item.source}",
        f"Content type: {item.raw_content_type}",
    ]
    if item.text:
        parts.append(f"Content:\n{item.text}")
    if item.file_ref:
        parts.append(f"File reference (MinIO path): {item.file_ref}")
    if item.bucket_hint:
        parts.append(f"Suggested bucket: {item.bucket_hint}")
    if item.metadata:
        meta_lines = "\n".join(f"  {k}: {v}" for k, v in item.metadata.items())
        parts.append(f"Metadata:\n{meta_lines}")
    parts.append(
        "Read SCHEMA.md and the relevant wiki pages, integrate this knowledge, "
        "write or update the appropriate page, and commit the changes."
    )
    return "\n".join(parts)


def _build_query_prompt(payload: dict[str, Any]) -> str:
    """Build a natural-language task prompt for a wiki query operation."""
    query = payload.get("query") or payload.get("text") or ""
    return (
        f"Answer the following question using the Mnemosyne wiki: {query}\n"
        "Read the wiki index to find relevant pages, then synthesize an answer with citations."
    )


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(default_context_name: str = "personal") -> Flask:
    """Create and configure the Hermes Flask application.

    Args:
        default_context_name: Context to use when context_name is absent from a request.

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/task")
    @_require_bearer
    def task():
        body = request.get_json(silent=True)
        if not body:
            return jsonify({"status": "error", "message": "Request body must be JSON"}), 400

        workflow = body.get("workflow", "")
        task_name = body.get("task", "")
        payload = body.get("payload", {})
        context_name = body.get("context_name", default_context_name)

        route = _TASK_MAP.get((workflow, task_name))
        if route is None:
            return jsonify({
                "status": "error",
                "message": f"Unknown workflow/task: {workflow!r}/{task_name!r}",
            }), 400

        try:
            if route["prompt_template"] == "ingest":
                item = IngestItem.from_dict(payload)
                prompt = _build_ingest_prompt(item)
            else:
                prompt = _build_query_prompt(payload)
        except KeyError as exc:
            return jsonify({
                "status": "error",
                "message": f"Missing required payload field: {exc}",
            }), 400

        # load_context() calls sys.exit(1) on failure — catch it and return 400
        try:
            context = load_context(context_name)
        except SystemExit:
            return jsonify({
                "status": "error",
                "message": f"Unknown or misconfigured context: {context_name!r}",
            }), 400

        result = run_agent(prompt, context, task_type=route["task_type"])

        return jsonify({
            "status": "ok",
            "message": result.answer,
            "data": {
                "model_used": result.model_used,
                "steps": len(result.steps),
            },
        })

    return app
