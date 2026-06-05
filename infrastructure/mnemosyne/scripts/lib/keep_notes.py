"""Parse Google Keep Takeout note JSON into a normalized KeepNote.

Pure library shared by extract-keep-note (inbox-item emitter / raw-source
writer). No prints, no sys.exit, no network — callers handle I/O and errors.

Handles the Keep-specific gotchas so nothing is silently dropped:
- text notes (textContent) vs checklists (listContent rendered as task lists)
- microsecond timestamps (createdTimestampUsec / userEditedTimestampUsec)
- isTrashed / empty filtering surfaced as a SkipReason, not a silent drop
- attachments [{filePath, mimetype}] with audio flagged for a Whisper pass
- annotation (saved-link) URLs captured separately so a consumer can keep them
  out of any field that would trigger URL-based extractors
- labels / color / pinned / archived preserved for downstream bucket mapping

Not yet handled (intentionally, noted not silently ignored): Keep reminders
(`tasks`) and collaborators (`sharees`).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime, timezone


class SkipReason(enum.Enum):
    """Why a note was not materialized (None return carries one of these)."""

    TRASHED = "trashed"
    EMPTY = "empty"


@dataclass
class Attachment:
    """A Keep attachment: a sibling binary file referenced by the note JSON."""

    file_path: str
    mimetype: str

    @property
    def is_audio(self) -> bool:
        return self.mimetype.startswith("audio/")

    @property
    def is_image(self) -> bool:
        return self.mimetype.startswith("image/")


@dataclass
class Annotation:
    """A saved-link card extracted by Keep (url + scraped title/description)."""

    url: str
    title: str
    description: str


@dataclass
class KeepNote:
    """Normalized view of a single Keep note, ready for emit/synthesis."""

    title: str
    text: str                       # plain text body (textContent), may be ""
    checklist: list[tuple[str, bool]]   # (item_text, is_checked); empty for text notes
    created: date
    updated: date
    labels: list[str] = field(default_factory=list)
    color: str | None = None        # None when DEFAULT (not meaningful)
    pinned: bool = False
    archived: bool = False
    attachments: list[Attachment] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)

    @property
    def annotation_urls(self) -> list[str]:
        return [a.url for a in self.annotations]

    @property
    def has_audio(self) -> bool:
        return any(a.is_audio for a in self.attachments)

    def render_text(self) -> str:
        """Render the note's own content (no links, no attachments) as markdown.

        Used as the inbox-item `text`: deliberately excludes annotation URLs so
        triage's URL detector never fires on it.
        """
        if self.text:
            return self.text
        if self.checklist:
            lines = []
            for item_text, checked in self.checklist:
                box = "[x]" if checked else "[ ]"
                lines.append(f"- {box} {item_text}")
            return "\n".join(lines)
        return ""

    def render_links_block(self) -> str:
        """Render a markdown `## Links` block from annotations, or "" if none."""
        if not self.annotations:
            return ""
        lines = ["## Links", ""]
        for a in self.annotations:
            label = a.title or a.url
            line = f"- [{label}]({a.url})"
            if a.description:
                line += f" — {a.description}"
            lines.append(line)
        return "\n".join(lines)


def usec_to_date(value: object) -> date:
    """Convert a Keep microsecond-since-epoch timestamp to a date.

    Keep stores timestamps in MICROSECONDS; dividing by 1e6 yields Unix
    seconds. Falls back to today on unparseable input.
    """
    try:
        seconds = int(value) / 1_000_000
        return datetime.fromtimestamp(seconds, tz=timezone.utc).date()
    except (TypeError, ValueError, OverflowError, OSError):
        return date.today()


def _derive_title(note: dict, text: str, checklist: list[tuple[str, bool]]) -> str:
    """Pick a human title — never trust the on-disk filename."""
    title = (note.get("title") or "").strip()
    if title:
        return title
    if text:
        first = text.splitlines()[0].strip()
        return (first[:60] + "…") if len(first) > 60 else first
    for item_text, _ in checklist:
        if item_text:
            return (item_text[:60] + "…") if len(item_text) > 60 else item_text
    return "Untitled Keep note"


def parse_note(note: dict, *, include_trashed: bool = False) -> KeepNote | SkipReason:
    """Normalize a raw Keep note dict into a KeepNote, or a SkipReason.

    Returns SkipReason.TRASHED for isTrashed notes (unless include_trashed) and
    SkipReason.EMPTY for notes with no text, no checklist, and no attachments.
    """
    if note.get("isTrashed") and not include_trashed:
        return SkipReason.TRASHED

    text = (note.get("textContent") or "").strip()
    checklist: list[tuple[str, bool]] = []
    for item in note.get("listContent") or []:
        item_text = (item.get("text") or "").strip()
        if not item_text:
            continue
        checklist.append((item_text, bool(item.get("isChecked"))))

    attachments = [
        Attachment(file_path=a["filePath"], mimetype=a.get("mimetype") or "")
        for a in (note.get("attachments") or [])
        if a.get("filePath")
    ]

    if not text and not checklist and not attachments:
        return SkipReason.EMPTY

    annotations = [
        Annotation(
            url=(a.get("url") or "").strip(),
            title=(a.get("title") or "").strip(),
            description=(a.get("description") or "").strip(),
        )
        for a in (note.get("annotations") or [])
        if (a.get("url") or "").strip()
    ]

    labels = [
        (lab.get("name") or "").strip()
        for lab in (note.get("labels") or [])
        if (lab.get("name") or "").strip()
    ]

    color = note.get("color")
    if color == "DEFAULT":
        color = None

    return KeepNote(
        title=_derive_title(note, text, checklist),
        text=text,
        checklist=checklist,
        created=usec_to_date(note.get("createdTimestampUsec")),
        updated=usec_to_date(note.get("userEditedTimestampUsec")),
        labels=labels,
        color=color,
        pinned=bool(note.get("isPinned")),
        archived=bool(note.get("isArchived")),
        attachments=attachments,
        annotations=annotations,
    )
