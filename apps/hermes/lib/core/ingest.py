"""Normalized ingestion envelope for Hermes.

All ingest sources (Telegram, email, web clipper, n8n Chat, API) produce an IngestItem
before handing off to the wiki integration pipeline. This keeps the pipeline source-agnostic
from the point of "raw content + metadata" onward.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IngestItem:
    """Normalized ingestion envelope produced by all ingest sources.

    Attributes:
        raw_content_type: Content category — "text" | "file" | "url" | "email".
        source: Originating system — "telegram" | "email" | "web_clipper" |
                "n8n_chat" | "api".
        text: Extracted text content (None for binary-only items).
        file_ref: MinIO path for binary content (None for text-only items).
        metadata: Source-specific fields (filename, url, sender, subject, etc.).
        bucket_hint: Optional pre-classification hint from the source system.
    """

    raw_content_type: str
    source: str
    text: str | None = None
    file_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    bucket_hint: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IngestItem:
        """Construct an IngestItem from a raw dict (e.g. a parsed JSON payload).

        Args:
            d: Dict containing at minimum "raw_content_type" and "source".

        Returns:
            Populated IngestItem.

        Raises:
            KeyError: If a required field is absent — callers should surface this as a 400.
        """
        return cls(
            raw_content_type=d["raw_content_type"],
            source=d["source"],
            text=d.get("text"),
            file_ref=d.get("file_ref"),
            metadata=d.get("metadata", {}),
            bucket_hint=d.get("bucket_hint"),
        )
