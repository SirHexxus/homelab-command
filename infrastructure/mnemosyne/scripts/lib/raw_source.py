"""Shared helpers for Mnemosyne raw-source files.

Used by extract-video-transcript and extract-image-data (and any future
extract-* scripts) to assemble consistent raw-source frontmatter and filenames.

Sibling raw-sources pattern: when enriching an IDEA from external media,
verbatim source is saved to raw-sources/ with linked_from frontmatter pointing
back to the consuming stub. See SCHEMA.md and the Mnemosyne wiki feedback
memory "Sibling raw-sources file pattern for transcripts" for context.

Pure library: no prints, no sys.exit. Callers handle errors.
"""

from __future__ import annotations

import os
import re
from datetime import date as _date
from pathlib import Path


# Match Obsidian filename sanitization in triage-inbox sanitize_title()
_FORBIDDEN_RE = re.compile(r'[\[\]#\^|*"\\/<>?]')


def resolve_wiki_root() -> Path:
    """Resolve the wiki root from $MNEME_WIKI_PATH or ~/mneme/wiki.

    Mirrors apps/hermes/skills/mneme_wiki/scripts/write_wiki_page.py.
    Raises FileNotFoundError if the root does not exist.
    """
    env_path = os.environ.get("MNEME_WIKI_PATH")
    if env_path:
        root = Path(env_path).expanduser().resolve()
    else:
        root = (Path.home() / "mneme" / "wiki").resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"Wiki root does not exist: {root}\n"
            "Set $MNEME_WIKI_PATH or ensure ~/mneme/wiki exists."
        )
    if not root.is_dir():
        raise FileNotFoundError(f"Wiki root is not a directory: {root}")
    return root


def safe_target(wiki_root: Path, rel_path: str) -> Path:
    """Resolve rel_path inside wiki_root, refusing traversal.

    Mirrors write_wiki_page.py::safe_target.
    """
    candidate = (wiki_root / rel_path).resolve()
    if not candidate.is_relative_to(wiki_root):
        raise PermissionError(
            f"Path {rel_path!r} escapes the wiki root ({wiki_root})."
        )
    return candidate


def sanitize_title(title: str) -> str:
    """Apply Obsidian filename sanitization rules.

    Mirrors triage-inbox::sanitize_title to keep filename conventions
    consistent across the ingest pipeline.
    """
    result = title.replace(":", " - ")
    result = _FORBIDDEN_RE.sub("-", result)
    result = re.sub(r"-{2,}", "-", result)
    result = result.strip("- ")
    if result.startswith("."):
        result = "-" + result[1:]
    return result


def raw_source_filename(d: _date, title: str, kind: str) -> str:
    """Build the canonical raw-source filename.

    Pattern: "YYYY-MM-DD — <Title> (<kind>).md"
        d:     Date of the source/capture.
        title: Source title (will be sanitized).
        kind:  Short descriptor like "YouTube transcript", "image OCR".
    """
    safe = sanitize_title(title)
    return f"{d.isoformat()} — {safe} ({kind}).md"


def _yaml_str(value: str | None) -> str:
    """Render a string YAML scalar — quoted only when needed."""
    if value is None:
        return "null"
    needs_quote = any(c in value for c in ':#"\n[]{},&*?|<>=!%@`')
    if needs_quote or value.strip() != value:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _yaml_list(values: list[str]) -> str:
    if not values:
        return "[]"
    inner = ", ".join(_yaml_str(v) for v in values)
    return f"[{inner}]"


def _linked_from_value(stub_title: str | None) -> str:
    if stub_title is None:
        return "null"
    return f"[[{stub_title}]]"


def build_video_frontmatter(
    *,
    source_url: str,
    title: str,
    creator: str | None,
    duration_s: int,
    platform: str,
    captured_via: str,
    transcriber: str,
    extraction_mode: str,
    extracted_by: str,
    created: _date | None = None,
    extra_tags: list[str] | None = None,
    stub_title: str | None = None,
) -> str:
    """Assemble the YAML frontmatter block for a video-transcript raw-source.

    Returns the full block including the leading and trailing '---' lines and a
    trailing newline. Callers concatenate this with the transcript body.
    """
    d = created or _date.today()
    iso_now = _iso_utc_now()
    base_tags = ["transcript", "raw-source"]
    if platform and platform not in base_tags:
        base_tags.append(platform)
    tags = base_tags + (extra_tags or [])

    lines = [
        "---",
        "bucket: RAW",
        f"created: {d.isoformat()}",
        f"updated: {d.isoformat()}",
        f"source: {_yaml_str(platform)}",
        f"source_url: {_yaml_str(source_url)}",
        f"source_title: {_yaml_str(title)}",
        f"source_creator: {_yaml_str(creator)}",
        f"source_duration_seconds: {duration_s}",
        f"captured_via: {_yaml_str(captured_via)}",
        f"transcribed_by: {_yaml_str(transcriber)}",
        f"transcribed_at: {iso_now}",
        f"extracted_by: {_yaml_str(extracted_by)}",
        f"extraction_mode: {_yaml_str(extraction_mode)}",
        f"tags: {_yaml_list(tags)}",
        f"linked_from: {_linked_from_value(stub_title)}",
        "---",
        "",
    ]
    return "\n".join(lines)


def build_image_frontmatter(
    *,
    source_filename: str,
    mime: str,
    captured_via: str,
    ocr_by: str,
    extraction_mode: str,
    extracted_by: str,
    extraction_context: str | None = None,
    created: _date | None = None,
    extra_tags: list[str] | None = None,
    stub_title: str | None = None,
) -> str:
    """Assemble YAML frontmatter for an image-OCR sidecar raw-source."""
    d = created or _date.today()
    iso_now = _iso_utc_now()
    tags = ["ocr", "raw-source", "image"] + (extra_tags or [])

    lines = [
        "---",
        "bucket: RAW",
        f"created: {d.isoformat()}",
        f"updated: {d.isoformat()}",
        "source: image",
        f"source_filename: {_yaml_str(source_filename)}",
        f"source_mime: {_yaml_str(mime)}",
        f"captured_via: {_yaml_str(captured_via)}",
        f"ocr_by: {_yaml_str(ocr_by)}",
        f"ocr_at: {iso_now}",
        f"extracted_by: {_yaml_str(extracted_by)}",
        f"extraction_mode: {_yaml_str(extraction_mode)}",
        f"extraction_context: {_yaml_str(extraction_context)}",
        f"tags: {_yaml_list(tags)}",
        f"linked_from: {_linked_from_value(stub_title)}",
        "---",
        "",
    ]
    return "\n".join(lines)


def build_keep_frontmatter(
    *,
    title: str,
    created: _date,
    updated: _date,
    captured_via: str,
    extracted_by: str,
    extraction_mode: str,
    color: str | None = None,
    pinned: bool = False,
    archived: bool = False,
    labels: list[str] | None = None,
    annotation_count: int = 0,
    attachment_count: int = 0,
    audio_pending: bool = False,
    extra_tags: list[str] | None = None,
    stub_title: str | None = None,
) -> str:
    """Assemble YAML frontmatter for a Google Keep note raw-source.

    `source` is fixed to google_keep (the transport); `captured_via` carries
    the SCHEMA source enum value of the bulk import (default manual). Keep
    metadata that has no IDEA-bucket equivalent — color, pinned/archived,
    labels — is preserved here so the downstream enrich stage can use it for
    bucket mapping. `audio_pending` marks notes whose audio attachments still
    need a Whisper pass via extract-video-transcript.
    """
    iso_now = _iso_utc_now()
    tags = ["keep", "raw-source"]
    if archived:
        tags.append("archived")
    if pinned:
        tags.append("pinned")
    tags += (extra_tags or [])

    lines = [
        "---",
        "bucket: RAW",
        f"created: {created.isoformat()}",
        f"updated: {updated.isoformat()}",
        "source: google_keep",
        f"captured_via: {_yaml_str(captured_via)}",
        f"source_title: {_yaml_str(title)}",
        f"keep_color: {_yaml_str(color)}",
        f"keep_pinned: {str(pinned).lower()}",
        f"keep_archived: {str(archived).lower()}",
        f"keep_labels: {_yaml_list(labels or [])}",
        f"annotation_count: {annotation_count}",
        f"attachment_count: {attachment_count}",
        f"audio_pending_transcription: {str(audio_pending).lower()}",
        f"extracted_by: {_yaml_str(extracted_by)}",
        f"extraction_mode: {_yaml_str(extraction_mode)}",
        f"extracted_at: {iso_now}",
        f"tags: {_yaml_list(tags)}",
        f"linked_from: {_linked_from_value(stub_title)}",
        "---",
        "",
    ]
    return "\n".join(lines)


def set_linked_from(raw_source_path: Path, stub_title: str | None) -> None:
    """Rewrite the linked_from: line in an existing raw-source file's frontmatter.

    Used by triage-inbox to backfill the reference after Haiku names the stub.
    Idempotent. Raises FileNotFoundError if the path doesn't exist; raises
    ValueError if the file has no recognizable frontmatter.
    """
    if not raw_source_path.exists():
        raise FileNotFoundError(raw_source_path)
    text = raw_source_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"No frontmatter in {raw_source_path}")
    # Find end of frontmatter block.
    end_match = re.search(r"\n---\s*\n", text)
    if end_match is None:
        raise ValueError(f"Unterminated frontmatter in {raw_source_path}")
    front = text[: end_match.start()]
    rest = text[end_match.start():]
    new_value = _linked_from_value(stub_title)
    if re.search(r"(?m)^linked_from:", front):
        new_front = re.sub(
            r"(?m)^linked_from:.*$",
            f"linked_from: {new_value}",
            front,
        )
    else:
        new_front = front.rstrip("\n") + f"\nlinked_from: {new_value}"
    raw_source_path.write_text(new_front + rest, encoding="utf-8")


def _iso_utc_now() -> str:
    """ISO 8601 UTC timestamp matching the log.md convention (Z suffix)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
