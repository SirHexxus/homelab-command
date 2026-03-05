"""Tests for lib/skills/filesystem.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.context import Context, ModelPreferences
from lib.skills.filesystem import delete_file, list_dir, move_file, read_file, write_file


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_context(allowed_paths: list[str]) -> Context:
    return Context(
        name="test",
        display_name="Test",
        tone="casual",
        allowed_paths=allowed_paths,
        allowed_commands=[],
        model=ModelPreferences(),
    )


# ── read_file ─────────────────────────────────────────────────────────────────

def test_read_file_success(tmp_path: Path) -> None:
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    ctx = make_context([str(tmp_path)])
    result = read_file(str(f), context=ctx)
    assert result == "hello world"


def test_read_file_outside_allowed_raises(tmp_path: Path) -> None:
    f = tmp_path / "secret.txt"
    f.write_text("secret")
    ctx = make_context(["/tmp/other"])
    with pytest.raises(PermissionError):
        read_file(str(f), context=ctx)


def test_read_file_traversal_blocked(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    ctx = make_context([str(allowed)])
    # Try to escape via ../
    with pytest.raises(PermissionError):
        read_file(str(allowed / ".." / "secret.txt"), context=ctx)


def test_read_file_not_found(tmp_path: Path) -> None:
    ctx = make_context([str(tmp_path)])
    with pytest.raises(FileNotFoundError):
        read_file(str(tmp_path / "nonexistent.txt"), context=ctx)


# ── write_file ────────────────────────────────────────────────────────────────

def test_write_file_creates_file(tmp_path: Path) -> None:
    ctx = make_context([str(tmp_path)])
    result = write_file(str(tmp_path / "out.txt"), "content", context=ctx)
    assert (tmp_path / "out.txt").read_text() == "content"
    assert "out.txt" in result


def test_write_file_dry_run(tmp_path: Path) -> None:
    ctx = make_context([str(tmp_path)])
    result = write_file(str(tmp_path / "out.txt"), "content", context=ctx, dry_run=True)
    assert not (tmp_path / "out.txt").exists()
    assert "dry-run" in result


def test_write_file_outside_allowed_raises(tmp_path: Path) -> None:
    ctx = make_context(["/tmp/other"])
    with pytest.raises(PermissionError):
        write_file(str(tmp_path / "out.txt"), "content", context=ctx)


# ── list_dir ──────────────────────────────────────────────────────────────────

def test_list_dir_returns_entries(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b").mkdir()
    ctx = make_context([str(tmp_path)])
    result = list_dir(str(tmp_path), context=ctx)
    assert "b/" in result
    assert "a.txt" in result


def test_list_dir_empty(tmp_path: Path) -> None:
    ctx = make_context([str(tmp_path)])
    result = list_dir(str(tmp_path), context=ctx)
    assert "empty" in result


def test_list_dir_not_a_dir(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x")
    ctx = make_context([str(tmp_path)])
    with pytest.raises(NotADirectoryError):
        list_dir(str(f), context=ctx)


# ── move_file ─────────────────────────────────────────────────────────────────

def test_move_file_success(tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "dst.txt"
    ctx = make_context([str(tmp_path)])
    move_file(str(src), str(dst), context=ctx)
    assert not src.exists()
    assert dst.read_text() == "data"


def test_move_file_dry_run(tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "dst.txt"
    ctx = make_context([str(tmp_path)])
    result = move_file(str(src), str(dst), context=ctx, dry_run=True)
    assert src.exists()
    assert "dry-run" in result


# ── delete_file ───────────────────────────────────────────────────────────────

def test_delete_file_success(tmp_path: Path) -> None:
    f = tmp_path / "del.txt"
    f.write_text("bye")
    ctx = make_context([str(tmp_path)])
    delete_file(str(f), context=ctx)
    assert not f.exists()


def test_delete_file_dry_run(tmp_path: Path) -> None:
    f = tmp_path / "del.txt"
    f.write_text("bye")
    ctx = make_context([str(tmp_path)])
    result = delete_file(str(f), context=ctx, dry_run=True)
    assert f.exists()
    assert "dry-run" in result
