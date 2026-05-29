#!/usr/bin/env python3
"""Stage, commit, pull --rebase, and push the Mnemosyne wiki.

Standalone port of git_commit_push from apps/hermes/lib/skills/wiki.py.
The git sequence (add → commit → pull --rebase → push) is pulled from
the proven inbox_receiver.py:125-134 pattern that has been running in
production via the interim cron path.

Why pull --rebase before push:
    The laptop's Obsidian Git plugin pushes `mneme: vault sync <ts>`
    commits on a ~5 min cadence. The LXC has its own working copy.
    A naive `git push` from the LXC after a laptop push gets rejected
    as non-fast-forward. Rebasing the LXC's commit on top of the
    laptop's resolves this without manual intervention.

Concurrency:
    A file lock at <wiki>/.git/mnemosyne.lock (30s timeout) serializes
    concurrent LXC writers. Today only Haley writes from the LXC, but
    when Margot/Quinn personas come online they share the lock. The
    lock does NOT defend against the laptop — that's the rebase's job.
    If the `filelock` package is unavailable, we proceed without the
    lock (single-writer assumption) and warn on stderr.

Wiki root is resolved from $MNEME_WIKI_PATH; fallback ~/mneme/wiki.

Usage:
    git_commit_push.py <message> [--dry-run]

Example:
    git_commit_push.py "mneme: ingest IDEA — Smoke Test"
    git_commit_push.py "mneme: update PROJECT — Project - Hermes" --dry-run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_WIKI = 5
EXIT_LOCK_TIMEOUT = 6
EXIT_GIT_FAILED = 7

LOCK_TIMEOUT_SEC = 30
RETRY_SLEEP_SEC = 2


def resolve_wiki_root() -> Path:
    env_path = os.environ.get('MNEME_WIKI_PATH')
    if env_path:
        root = Path(env_path).expanduser().resolve()
    else:
        root = (Path.home() / 'mneme' / 'wiki').resolve()
    if not root.exists():
        raise FileNotFoundError(
            f"Wiki root does not exist: {root}\n"
            "Set $MNEME_WIKI_PATH or ensure ~/mneme/wiki exists."
        )
    if not (root / '.git').exists():
        raise FileNotFoundError(f"Wiki root is not a git repository: {root}")
    return root


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `git -C <cwd> <args>` and return the completed process."""
    return subprocess.run(
        ['git', '-C', str(cwd), *args],
        capture_output=True,
        text=True,
    )


def git_or_raise(args: list[str], cwd: Path) -> str:
    """Like git() but raise RuntimeError on non-zero exit."""
    result = git(args, cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n"
            f"{result.stdout}{result.stderr}".strip()
        )
    return (result.stdout + result.stderr).strip()


def run_sequence(wiki_root: Path, message: str) -> str:
    """add → commit → pull --rebase → push. Single retry on push rejection."""
    add_out = git_or_raise(['add', '-A'], wiki_root)

    status = git(['diff', '--cached', '--quiet'], wiki_root)
    if status.returncode == 0:
        return "Nothing to commit (working tree matches index)."

    commit_out = git_or_raise(['commit', '-m', message], wiki_root)
    rebase_out = git_or_raise(['pull', '--rebase'], wiki_root)

    push = git(['push'], wiki_root)
    if push.returncode != 0:
        print(
            f"warning: first push attempt failed, retrying after {RETRY_SLEEP_SEC}s:\n"
            f"{push.stdout}{push.stderr}",
            file=sys.stderr,
        )
        time.sleep(RETRY_SLEEP_SEC)
        git_or_raise(['pull', '--rebase'], wiki_root)
        push_out = git_or_raise(['push'], wiki_root)
    else:
        push_out = (push.stdout + push.stderr).strip()

    return '\n'.join(s for s in (add_out, commit_out, rebase_out, push_out) if s)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Commit and push the Mnemosyne wiki.',
    )
    parser.add_argument('message', help='Git commit message.')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print the four git commands without executing them.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        wiki_root = resolve_wiki_root()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_NO_WIKI

    if args.dry_run:
        print(f"[dry-run] In {wiki_root}, would run:")
        print(f"  git add -A")
        print(f"  git commit -m {args.message!r}")
        print(f"  git pull --rebase")
        print(f"  git push  # retry once after {RETRY_SLEEP_SEC}s on rejection")
        return EXIT_OK

    lock_path = wiki_root / '.git' / 'mnemosyne.lock'
    try:
        from filelock import FileLock, Timeout  # type: ignore[import]
    except ImportError:
        print(
            "warning: python 'filelock' not installed; running without "
            "concurrent-writer protection. Install with: pip install filelock",
            file=sys.stderr,
        )
        try:
            output = run_sequence(wiki_root, args.message)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_GIT_FAILED
        print(output)
        return EXIT_OK

    lock = FileLock(str(lock_path), timeout=LOCK_TIMEOUT_SEC)
    try:
        with lock:
            try:
                output = run_sequence(wiki_root, args.message)
            except RuntimeError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return EXIT_GIT_FAILED
    except Timeout:
        print(
            f"error: could not acquire wiki git lock after {LOCK_TIMEOUT_SEC}s. "
            "Another writer is in progress.",
            file=sys.stderr,
        )
        return EXIT_LOCK_TIMEOUT

    print(output)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
