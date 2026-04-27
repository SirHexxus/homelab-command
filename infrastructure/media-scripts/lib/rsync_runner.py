"""Shared rsync wrapper used by all media-scripts bin/ entry points.

Streams rsync output directly to the terminal (suitable for tmux sessions)
and writes a native rsync log file alongside. Returns True on success.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

LOGS_DIR = Path(__file__).parent.parent / "logs"

# Base rsync flags applied to every transfer:
#   -a  archive mode (recursive, preserve perms/times/symlinks/owner/group)
#   -h  human-readable sizes
#   --partial  keep partially-transferred files so reruns resume mid-file
#   --info=progress2  single-line transfer progress (cleaner in tmux than --progress)
#   --stats  print transfer summary at the end
#   -O / --omit-dir-times  skip syncing directory timestamps — NFS rejects these
#   --inplace  write directly to destination instead of temp+rename — avoids
#              mkstemp permission errors on NFS shares with restrictive ACLs
BASE_FLAGS = ["-ahO", "--inplace", "--partial", "--info=progress2", "--stats"]


# ── Public API ─────────────────────────────────────────────────────────────────


def run_rsync(
    src: Path,
    dest: Path,
    *,
    label: str,
    dry_run: bool = False,
    delete: bool = False,
    verbose: bool = False,
) -> bool:
    """Run rsync from src to dest, streaming output to the terminal.

    Writes a native rsync log to logs/<label>-<timestamp>.log.
    Returns True if rsync exits 0, False otherwise.

    Args:
        src: Source directory. A trailing slash is added automatically so rsync
            copies the *contents* of src into dest (not src itself).
        dest: Destination directory. Created if it does not exist (unless dry_run).
        label: Short name used in log filename and printed headers (e.g. "gba").
        dry_run: If True, passes --dry-run to rsync — no files are transferred.
        delete: If True, passes --delete — removes files in dest absent from src.
        verbose: If True, passes -v for per-file output.
    """
    if not src.exists():
        print(f"  [ERROR] source does not exist: {src}", file=sys.stderr)
        return False

    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    log_path = _log_path(label, dry_run)

    cmd = _build_cmd(src, dest, log_path=log_path, dry_run=dry_run, delete=delete, verbose=verbose)

    _print_header(label, src, dest, dry_run, delete)
    print(f"  log  → {log_path}")
    print(f"  cmd  → {' '.join(str(t) for t in cmd)}\n")

    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("  [ERROR] rsync not found — install rsync and retry.", file=sys.stderr)
        return False

    success = result.returncode == 0
    status = "OK" if success else f"FAILED (exit {result.returncode})"
    print(f"\n  [{label}] {status}\n")
    return success


# ── Internal helpers ───────────────────────────────────────────────────────────


def _build_cmd(
    src: Path,
    dest: Path,
    *,
    log_path: Path,
    dry_run: bool,
    delete: bool,
    verbose: bool,
) -> list[str]:
    """Return the rsync command as a list of strings."""
    # Ensure trailing slash on src so rsync copies contents, not the dir itself.
    src_str = str(src).rstrip("/") + "/"

    cmd = ["rsync"] + BASE_FLAGS + [f"--log-file={log_path}"]

    if dry_run:
        cmd.append("--dry-run")
    if delete:
        cmd.append("--delete")
    if verbose:
        cmd.append("-v")

    cmd += [src_str, str(dest)]
    return cmd


def _log_path(label: str, dry_run: bool) -> Path:
    """Return a timestamped log file path under logs/."""
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = "-dryrun" if dry_run else ""
    return LOGS_DIR / f"{label}{suffix}-{ts}.log"


def _print_header(label: str, src: Path, dest: Path, dry_run: bool, delete: bool) -> None:
    dry_tag = "  [DRY RUN]" if dry_run else ""
    del_tag = "  --delete" if delete else ""
    print(f"{'─' * 60}")
    print(f"  {label}{dry_tag}{del_tag}")
    print(f"  src  → {src}")
    print(f"  dest → {dest}")
