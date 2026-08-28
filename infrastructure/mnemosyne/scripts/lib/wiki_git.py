#!/usr/bin/env python3
"""Commit a worker's own wiki changes, under the shared commit lock.

Every mneme-* worker commits the files it touched; only mneme-sync talks to
the remote. Two rules make that safe when workers overlap (seven units fire
at 07:00:00):

  1. Stage only your own paths -- never `git add -A`. A worker that staged
     everything would sweep up another worker's half-written files and
     commit them under its own message.
  2. Hold the shared lock across stage+commit only. Never hold it around
     slow work such as LLM enrichment, or the whole 07:00 cohort blocks.

Shell callers use the CLI form and get identical behaviour:

    python3 lib/wiki_git.py --action sweep \\
        --summary "archived 12 pages" -- archive/a.md archive/b.md
"""

from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

DEFAULT_WIKI = Path(os.environ.get("MNEME_WIKI_PATH", "/opt/inbox-receiver/wiki"))
LOCK_NAME = "mneme-commit.lock"
LOCK_TIMEOUT = 120.0
LOCK_POLL = 0.2


def _git(wiki_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess:
    """Run a git command in wiki_root without raising."""
    return subprocess.run(
        ["git", "-C", str(wiki_root), *args],
        capture_output=True,
        text=True,
    )


def _tracked(wiki_root: Path, rel: str) -> bool:
    """True if git already knows this path (tracked or staged)."""
    found = _git(wiki_root, ["ls-files", "--error-unmatch", "--", rel])
    return found.returncode == 0


def _relative(wiki_root: Path, path: Path) -> str:
    """Path as git wants it: relative to the repo root."""
    try:
        return str(Path(path).resolve().relative_to(wiki_root.resolve()))
    except ValueError:
        # Already relative, or outside the repo -- let git decide.
        return str(path)


def commit_wiki_changes(wiki_root: Path, paths: Sequence[Path],
                        action: str, summary: str,
                        timeout: float = LOCK_TIMEOUT) -> bool:
    """Stage the given paths and commit them. True if a commit was made.

    Returns False -- without raising -- when there is nothing to commit, so
    callers that run on a timer (render-log rewrites log.md every 30
    minutes) do not create empty commits.
    """
    if not paths:
        return False
    if not (wiki_root / ".git").exists():
        print(f"Warning: not a git repository: {wiki_root}", file=sys.stderr)
        return False

    rel_paths = [_relative(wiki_root, Path(p)) for p in paths]
    lock_path = wiki_root / ".git" / LOCK_NAME
    deadline = time.monotonic() + timeout

    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o644)
    except OSError as exc:
        print(f"Warning: cannot open commit lock ({exc})", file=sys.stderr)
        return False

    try:
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    print(f"Warning: commit lock busy after {timeout:.0f}s; "
                          f"leaving changes for mneme-sync", file=sys.stderr)
                    return False
                time.sleep(LOCK_POLL)

        # Drop paths git cannot match: a caller that used `git mv` has
        # already staged the rename, so the old name is gone from both the
        # working tree and the index, and `git add` would abort on it.
        stageable = [p for p in rel_paths
                     if (wiki_root / p).exists() or _tracked(wiki_root, p)]

        # -A so deletions are staged too, but scoped to this worker's own
        # pathspec -- never a bare `git add -A`.
        if stageable:
            added = _git(wiki_root, ["add", "-A", "--", *stageable])
            if added.returncode != 0:
                print(f"Warning: git add failed ({added.stderr.strip()})",
                      file=sys.stderr)
                return False

        staged = _git(wiki_root, ["diff", "--cached", "--quiet"])
        if staged.returncode == 0:
            return False  # nothing changed -- not an error

        message = f"mneme: {action} — {summary}"
        done = _git(wiki_root, ["commit", "-q", "-m", message])
        if done.returncode != 0:
            print(f"Warning: git commit failed ({done.stderr.strip()})",
                  file=sys.stderr)
            return False
        return True
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI,
                    help="wiki checkout (default: $MNEME_WIKI_PATH)")
    ap.add_argument("--action", required=True,
                    help="short verb for the subject, e.g. 'sweep'")
    ap.add_argument("--summary", required=True,
                    help="what changed and why, with counts")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be committed, changing nothing")
    ap.add_argument("paths", nargs="+", type=Path,
                    help="paths this worker created, modified or deleted")
    args = ap.parse_args()

    if args.dry_run:
        print(f"[dry-run] would commit as: mneme: {args.action} — "
              f"{args.summary}")
        for p in args.paths:
            print(f"[dry-run]   {p}")
        return 0

    commit_wiki_changes(args.wiki_root, args.paths, args.action, args.summary)
    return 0  # always 0 -- fail-soft, mneme-sync is the safety net


if __name__ == "__main__":
    sys.exit(main())
