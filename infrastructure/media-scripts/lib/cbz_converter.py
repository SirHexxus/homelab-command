"""CBZ conversion utilities shared by sync-comics and sync-manga.

CBZ is a ZIP archive with a .cbz extension. Conversion strategy:
  .zip / .cbz  →  rename only (no repacking — ZIP is ZIP)
  .rar / .cbr  →  extract with unrar, repack as ZIP, write as .cbz

All output is written to a destination path you provide; source files are
never modified (Seagate is mounted read-only).
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


# ── Public API ─────────────────────────────────────────────────────────────────


def convert_to_cbz(src: Path, dest_dir: Path, *, dry_run: bool = False) -> Path | None:
    """Convert a comic archive at src to CBZ and write it into dest_dir.

    Returns the destination Path on success, None on failure.
    dest_dir is created if it does not exist (unless dry_run).
    """
    suffix = src.suffix.lower()
    dest_path = dest_dir / (src.stem + ".cbz")

    if dry_run:
        action = "rename" if suffix in (".zip", ".cbz") else "repack"
        print(f"    [dry-run] {action}  {src.name}  →  {dest_path}")
        return dest_path

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        return dest_path  # already converted — idempotent

    if suffix in (".zip", ".cbz"):
        return _copy_as_cbz(src, dest_path)
    elif suffix in (".rar", ".cbr"):
        return _repack_rar_as_cbz(src, dest_path)
    else:
        print(f"    [SKIP] unsupported format: {src.name}", file=sys.stderr)
        return None


def is_comic_archive(path: Path) -> bool:
    """Return True if path is a supported comic archive format."""
    return path.suffix.lower() in (".zip", ".cbz", ".rar", ".cbr")


def check_unrar() -> bool:
    """Return True if unrar is available on PATH."""
    return shutil.which("unrar") is not None


# ── Internal helpers ───────────────────────────────────────────────────────────


def _copy_as_cbz(src: Path, dest: Path) -> Path | None:
    """Copy a .zip/.cbz to dest with .cbz extension."""
    try:
        shutil.copy2(src, dest)
        return dest
    except OSError as exc:
        print(f"    [ERROR] copy failed: {src.name}: {exc}", file=sys.stderr)
        return None


def _repack_rar_as_cbz(src: Path, dest: Path) -> Path | None:
    """Extract a RAR archive and repack its contents as a CBZ at dest."""
    if not check_unrar():
        print(
            f"    [ERROR] unrar not found — cannot convert {src.name}. "
            "Install with: sudo apt install unrar",
            file=sys.stderr,
        )
        return None

    tmp_dir = dest.parent / f".cbz_tmp_{src.stem}"
    try:
        tmp_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["unrar", "e", "-y", str(src), str(tmp_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"    [ERROR] unrar failed on {src.name}: {result.stderr.strip()}", file=sys.stderr)
            return None

        pages = sorted(tmp_dir.iterdir())
        if not pages:
            print(f"    [ERROR] unrar produced no files from {src.name}", file=sys.stderr)
            return None

        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as zf:
            for page in pages:
                zf.write(page, page.name)

        return dest

    except OSError as exc:
        print(f"    [ERROR] repack failed: {src.name}: {exc}", file=sys.stderr)
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
