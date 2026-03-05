"""Filesystem skill — scoped file operations for Hermes.

All operations are constrained to the allowed_paths whitelist defined in the
active Context. Any path that resolves outside the whitelist is rejected with
an error (no side effects, no leakage).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from lib.core.context import Context
from lib.core.skill_registry import register_skill

# ── Security helpers ──────────────────────────────────────────────────────────

def _resolve_and_check(raw_path: str, context: Context) -> Path:
    """Resolve `raw_path` to an absolute path and verify it is whitelisted.

    Args:
        raw_path: Raw path string from the LLM (may contain ~ or ..).
        context: Active context whose allowed_paths whitelist is used.

    Returns:
        Resolved absolute Path.

    Raises:
        PermissionError: If the resolved path is outside every allowed root.
    """
    resolved = Path(raw_path).expanduser().resolve()
    allowed_roots = [Path(p).expanduser().resolve() for p in context.allowed_paths]

    for root in allowed_roots:
        # is_relative_to handles the case where resolved == root exactly
        if resolved == root or resolved.is_relative_to(root):
            return resolved

    allowed_display = ", ".join(str(r) for r in allowed_roots)
    raise PermissionError(
        f"Path '{resolved}' is outside all allowed paths for context "
        f"'{context.name}'. Allowed: {allowed_display}"
    )


# ── Skills ────────────────────────────────────────────────────────────────────

@register_skill()
def read_file(path: str, context: Context, dry_run: bool = False) -> str:
    """Read and return the text contents of a file.

    Args:
        path: Path to the file to read.
        context: Active context (used for path validation).
        dry_run: Unused for reads; present for interface consistency.

    Returns:
        File contents as a string.
    """
    resolved = _resolve_and_check(path, context)

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")
    if not resolved.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {resolved}")

    return resolved.read_text(encoding="utf-8", errors="replace")


@register_skill()
def write_file(
    path: str,
    content: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Write text content to a file, creating parent directories if needed.

    Args:
        path: Destination file path.
        content: Text to write.
        context: Active context (path validation).
        dry_run: If True, describe the action without writing.

    Returns:
        Confirmation message.
    """
    resolved = _resolve_and_check(path, context)

    if dry_run:
        return f"[dry-run] Would write {len(content)} bytes to {resolved}"

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {resolved}"


@register_skill()
def list_dir(path: str, context: Context, dry_run: bool = False) -> str:
    """List the contents of a directory.

    Args:
        path: Directory to list.
        context: Active context (path validation).
        dry_run: Unused for reads.

    Returns:
        Newline-separated list of filenames with type indicators (/ for dirs).
    """
    resolved = _resolve_and_check(path, context)

    if not resolved.exists():
        raise FileNotFoundError(f"Directory not found: {resolved}")
    if not resolved.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {resolved}")

    entries = sorted(resolved.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = []
    for entry in entries:
        indicator = "/" if entry.is_dir() else ""
        lines.append(f"{entry.name}{indicator}")

    return "\n".join(lines) if lines else "(empty directory)"


@register_skill()
def move_file(
    src: str,
    dst: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Move or rename a file within the allowed paths.

    Args:
        src: Source path.
        dst: Destination path.
        context: Active context (both paths are validated).
        dry_run: If True, describe the action without moving.

    Returns:
        Confirmation message.
    """
    src_resolved = _resolve_and_check(src, context)
    dst_resolved = _resolve_and_check(dst, context)

    if not src_resolved.exists():
        raise FileNotFoundError(f"Source not found: {src_resolved}")

    if dry_run:
        return f"[dry-run] Would move {src_resolved} → {dst_resolved}"

    dst_resolved.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_resolved), str(dst_resolved))
    return f"Moved {src_resolved} → {dst_resolved}"


@register_skill()
def delete_file(
    path: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Delete a file (not a directory) within the allowed paths.

    Args:
        path: Path to the file to delete.
        context: Active context (path validation).
        dry_run: If True, describe the action without deleting.

    Returns:
        Confirmation message.
    """
    resolved = _resolve_and_check(path, context)

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")
    if resolved.is_dir():
        raise IsADirectoryError(
            f"'{resolved}' is a directory. Use a more specific operation."
        )

    if dry_run:
        return f"[dry-run] Would delete {resolved}"

    resolved.unlink()
    return f"Deleted {resolved}"
