"""Shared LLM client helper for Mnemosyne — Vertex AI via google-genai.

Used by extract-image-data, daily-digest, and any future Mnemosyne script that
needs text or multimodal generation. Centralizes:

- Vertex creds loading from ~/.config/mnemosyne/vertex-creds.json
- google-genai Client construction with the service-account credentials
- Text + multimodal call shapes used by the existing scripts

Backend choice: Vertex AI direct (NOT through litellm). This is intentional —
Mnemosyne scripts make a small number of one-shot calls per invocation. The
proxy layer's value (routing, observability, retries) is for an agent like
Hermes, not for a cron-driven script. When daily-digest and extract-image-data
move to Hermes-Agent (planned), they'll route through litellm at that point.

The same Vertex SA file used here is also mounted at /etc/litellm/vertex-sa.json
on the Chiron LXC — so credentials are temporarily duplicated. That's an
acceptable short-term tradeoff per James 2026-06-03.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_VERTEX_CREDS_PATH = Path.home() / ".config" / "mnemosyne" / "vertex-creds.json"
DEFAULT_MODEL = "gemini-2.5-flash"


class LLMError(RuntimeError):
    """Raised on credentials or SDK errors. Callers handle for graceful exit."""


def load_vertex_creds() -> dict:
    """Return {project, location, sa_path, model} from the vertex creds file.

    Path resolution: VERTEX_CREDENTIALS env var, then DEFAULT_VERTEX_CREDS_PATH.
    """
    raw_path = os.environ.get("VERTEX_CREDENTIALS", "").strip()
    creds_path = Path(raw_path) if raw_path else DEFAULT_VERTEX_CREDS_PATH
    try:
        creds = json.loads(creds_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LLMError(f"cannot read Vertex creds at {creds_path}: {exc}")
    except json.JSONDecodeError as exc:
        raise LLMError(f"Vertex creds at {creds_path} is not valid JSON: {exc}")
    project = (creds.get("project") or "").strip()
    location = (creds.get("location") or "").strip()
    sa_path = (creds.get("sa_path") or "").strip()
    model = (creds.get("model") or DEFAULT_MODEL).strip()
    missing = [k for k, v in (("project", project), ("location", location), ("sa_path", sa_path)) if not v]
    if missing:
        raise LLMError(
            f"Vertex creds at {creds_path} missing required fields: {', '.join(missing)}"
        )
    if not Path(sa_path).exists():
        raise LLMError(f"Vertex service account file not found: {sa_path}")
    return {
        "project": project,
        "location": location,
        "sa_path": sa_path,
        "model": model,
    }


def get_client(creds: dict | None = None):
    """Return a google-genai Client configured for Vertex AI.

    Reuses creds if provided; otherwise loads them. Sets
    GOOGLE_APPLICATION_CREDENTIALS in the process environment so the SDK
    picks up the SA via Application Default Credentials.
    """
    if creds is None:
        creds = load_vertex_creds()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds["sa_path"]
    try:
        from google import genai
    except ImportError as exc:
        raise LLMError(
            f"google-genai is not installed ({exc}). Install with: pip install google-genai"
        )
    return genai.Client(
        vertexai=True,
        project=creds["project"],
        location=creds["location"],
    )


def call_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    creds: dict | None = None,
):
    """Single-turn text generation. Returns the raw response object.

    Caller extracts .text and .usage_metadata as needed. Returning the raw
    response (not a string) keeps usage-metadata logging possible in callers
    like daily-digest without complicating the helper signature.
    """
    if creds is None:
        creds = load_vertex_creds()
    client = get_client(creds)
    from google.genai import types
    return client.models.generate_content(
        model=model or creds["model"],
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )


def call_multimodal(
    *,
    system_prompt: str,
    user_text: str,
    image_bytes: bytes,
    mime: str,
    model: str | None = None,
    creds: dict | None = None,
):
    """Single-turn multimodal (image + text) generation. Returns raw response."""
    if creds is None:
        creds = load_vertex_creds()
    client = get_client(creds)
    from google.genai import types
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime),
        user_text,
    ]
    return client.models.generate_content(
        model=model or creds["model"],
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
