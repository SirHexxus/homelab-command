"""Wiki skill — git-backed Markdown wiki operations for Hermes (Mnemosyne project).

All operations are scoped to the wiki_path configured under mnemosyne: in config/config.yml.
The wiki root must exist and be a valid git repository before any skill can run.

Config (config/config.yml):
    mnemosyne:
      wiki_path: ~/wiki
      wiki_remote: git@github.com:SirHexxus/wiki.git

Requires: filelock>=3.13,<4
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.core.context import Context, load_global_config
from lib.core.skill_registry import register_skill

# ── Config helpers ────────────────────────────────────────────────────────────

def _wiki_config() -> dict[str, Any]:
    """Load and validate the mnemosyne config block from config.yml.

    Returns:
        Dict with keys 'wiki_path' (Path, expanded) and 'wiki_remote' (str).

    Raises:
        RuntimeError: If the mnemosyne block or wiki_path is missing from config.
    """
    global_cfg = load_global_config()
    raw = global_cfg.get("mnemosyne", {})
    if not raw:
        raise RuntimeError(
            "mnemosyne: section is missing from config.yml. "
            "Copy config/config.example.yml and fill in wiki_path."
        )
    wiki_path_raw = raw.get("wiki_path")
    if not wiki_path_raw:
        raise RuntimeError("mnemosyne.wiki_path is required in config.yml.")
    return {
        "wiki_path": Path(wiki_path_raw).expanduser().resolve(),
        "wiki_remote": raw.get("wiki_remote", "origin"),
    }


def _ensure_wiki(wiki_path: Path) -> None:
    """Raise RuntimeError if wiki_path does not exist or is not a git repo."""
    if not wiki_path.exists():
        raise RuntimeError(
            f"Wiki path does not exist: {wiki_path}\n"
            "Run 'git clone <remote> <wiki_path>' to initialise it."
        )
    if not (wiki_path / ".git").exists():
        raise RuntimeError(
            f"Wiki path is not a git repository: {wiki_path}\n"
            "Run 'git init' or 'git clone' to initialise it."
        )


def _safe_target(wiki_path: Path, rel_path: str) -> Path:
    """Resolve a relative path within the wiki and guard against traversal.

    Args:
        wiki_path: Absolute wiki root.
        rel_path: Caller-supplied relative path.

    Returns:
        Resolved absolute path inside the wiki root.

    Raises:
        PermissionError: If the resolved path escapes the wiki root.
    """
    target = (wiki_path / rel_path).resolve()
    if not target.is_relative_to(wiki_path):
        raise PermissionError(
            f"Path '{rel_path}' escapes the wiki root ({wiki_path}). "
            "Only paths within the wiki directory are allowed."
        )
    return target


def _git(args: list[str], cwd: Path) -> str:
    """Run a git subcommand in cwd and return stdout.

    Args:
        args: git subcommand and arguments (without the leading 'git').
        cwd: Working directory.

    Returns:
        Stripped stdout + stderr from git.

    Raises:
        RuntimeError: If git exits with a non-zero status.
    """
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n{output}"
        )
    return output


# ── Skills ────────────────────────────────────────────────────────────────────

@register_skill()
def read_wiki_page(path: str, context: Context, dry_run: bool = False) -> str:
    """Read a wiki page by path relative to the wiki root.

    Args:
        path: Relative path to the Markdown file (e.g. "journal/2024-01.md").
        context: Active context.
        dry_run: Unused for reads; present for interface consistency.

    Returns:
        File contents as a string.

    Raises:
        RuntimeError: If wiki is not configured or inaccessible.
        FileNotFoundError: If the page does not exist.
        PermissionError: If path escapes the wiki root.
    """
    cfg = _wiki_config()
    wiki_path: Path = cfg["wiki_path"]
    _ensure_wiki(wiki_path)

    target = _safe_target(wiki_path, path)
    if not target.exists():
        raise FileNotFoundError(f"Wiki page not found: {target}")
    if not target.is_file():
        raise IsADirectoryError(f"Path is a directory, not a page: {target}")

    return target.read_text(encoding="utf-8", errors="replace")


@register_skill()
def write_wiki_page(
    path: str,
    content: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Write or overwrite a wiki page. Creates parent directories as needed.

    Args:
        path: Relative path to the Markdown file (e.g. "ideas/new-idea.md").
        content: Full Markdown content to write.
        context: Active context.
        dry_run: If True, describe the write without performing it.

    Returns:
        Confirmation message with byte count and resolved path.

    Raises:
        RuntimeError: If wiki is not configured.
        PermissionError: If path escapes the wiki root.
    """
    cfg = _wiki_config()
    wiki_path: Path = cfg["wiki_path"]
    _ensure_wiki(wiki_path)

    target = _safe_target(wiki_path, path)

    if dry_run:
        return f"[dry-run] Would write {len(content.encode())} bytes to wiki:{path}"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content.encode())} bytes to {target}"


@register_skill()
def read_wiki_index(context: Context, dry_run: bool = False) -> str:
    """Read the wiki root index.md in full.

    Args:
        context: Active context.
        dry_run: Unused for reads.

    Returns:
        Contents of index.md.

    Raises:
        RuntimeError: If wiki is not configured.
        FileNotFoundError: If index.md does not exist.
    """
    return read_wiki_page("index.md", context=context, dry_run=dry_run)


@register_skill()
def append_wiki_log(
    entry: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Append a timestamped entry to log.md in the wiki root.

    Creates log.md if it does not yet exist. Prepends an ISO 8601 UTC timestamp.

    Args:
        entry: The log entry text (one or more lines).
        context: Active context.
        dry_run: If True, show what would be appended without writing.

    Returns:
        Confirmation message with the timestamp used.

    Raises:
        RuntimeError: If wiki is not configured.
    """
    cfg = _wiki_config()
    wiki_path: Path = cfg["wiki_path"]
    _ensure_wiki(wiki_path)

    log_path = wiki_path / "log.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    formatted = f"\n## {now}\n\n{entry.strip()}\n"

    if dry_run:
        return f"[dry-run] Would append to wiki:log.md:\n{formatted}"

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(formatted)

    return f"Appended entry to log.md at {now}"


@register_skill()
def list_wiki_pages(
    bucket: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """List all Markdown files in a named bucket directory within the wiki.

    Args:
        bucket: Subdirectory name (e.g. "ideas", "journal", "reference").
        context: Active context.
        dry_run: Unused for reads.

    Returns:
        Newline-separated relative paths, or a message if the bucket is empty.

    Raises:
        RuntimeError: If wiki is not configured.
        FileNotFoundError: If the bucket directory does not exist.
        PermissionError: If bucket escapes the wiki root.
    """
    cfg = _wiki_config()
    wiki_path: Path = cfg["wiki_path"]
    _ensure_wiki(wiki_path)

    bucket_path = _safe_target(wiki_path, bucket)
    if not bucket_path.exists():
        raise FileNotFoundError(f"Wiki bucket not found: {bucket_path}")
    if not bucket_path.is_dir():
        raise NotADirectoryError(f"Wiki bucket is not a directory: {bucket_path}")

    md_files = sorted(bucket_path.rglob("*.md"))
    if not md_files:
        return f"No Markdown files found in wiki:{bucket}/"

    return "\n".join(str(f.relative_to(wiki_path)) for f in md_files)


_GIT_LOCK_TIMEOUT = 30


@register_skill()
def git_commit_push(
    message: str,
    context: Context,
    dry_run: bool = False,
) -> str:
    """Stage all wiki changes, commit, and push to the configured remote.

    Acquires an exclusive file lock before git operations to prevent concurrent
    commits from racing (e.g. two simultaneous n8n ingest flows).

    Args:
        message: Git commit message.
        context: Active context.
        dry_run: If True, describe the git operations without running them.

    Returns:
        Output from git commit and push.

    Raises:
        RuntimeError: If wiki is not configured, git fails, or lock times out.
    """
    from filelock import FileLock, Timeout  # type: ignore[import]

    cfg = _wiki_config()
    wiki_path: Path = cfg["wiki_path"]
    wiki_remote: str = cfg["wiki_remote"]
    _ensure_wiki(wiki_path)

    lock_path = wiki_path / ".git" / "mnemosyne.lock"

    if dry_run:
        return (
            f"[dry-run] Would run in {wiki_path}:\n"
            f"  git add -A\n"
            f"  git commit -m {message!r}\n"
            f"  git push {wiki_remote}"
        )

    lock = FileLock(str(lock_path), timeout=_GIT_LOCK_TIMEOUT)
    try:
        with lock:
            _git(["add", "-A"], cwd=wiki_path)
            commit_out = _git(["commit", "-m", message], cwd=wiki_path)
            push_out = _git(["push", wiki_remote], cwd=wiki_path)
            return f"{commit_out}\n{push_out}".strip()
    except Timeout:
        raise RuntimeError(
            f"Could not acquire wiki git lock after {_GIT_LOCK_TIMEOUT}s. "
            "Another process may be running a concurrent commit."
        )


@register_skill()
def scan_wiki_inbox(context: Context, dry_run: bool = False) -> str:
    """List files in the wiki/inbox/ staging folder.

    The inbox is where raw items land before Hermes processes and files them
    into the appropriate wiki bucket.

    Args:
        context: Active context.
        dry_run: Unused for reads.

    Returns:
        Newline-separated filenames in wiki/inbox/, or a message if empty/absent.

    Raises:
        RuntimeError: If wiki is not configured.
    """
    cfg = _wiki_config()
    wiki_path: Path = cfg["wiki_path"]
    _ensure_wiki(wiki_path)

    inbox_path = wiki_path / "inbox"
    if not inbox_path.exists():
        return "wiki/inbox/ does not exist (no staged items)."

    entries = sorted(inbox_path.iterdir())
    if not entries:
        return "wiki/inbox/ is empty."

    lines = []
    for entry in entries:
        indicator = "/" if entry.is_dir() else ""
        lines.append(f"{entry.name}{indicator}")
    return "\n".join(lines)
