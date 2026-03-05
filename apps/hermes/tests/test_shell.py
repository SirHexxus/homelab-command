"""Tests for lib/skills/shell.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.context import Context, ModelPreferences
from lib.skills.shell import run_command


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_context(allowed_commands: list[str]) -> Context:
    return Context(
        name="test",
        display_name="Test",
        tone="casual",
        allowed_paths=[],
        allowed_commands=allowed_commands,
        model=ModelPreferences(),
    )


# ── run_command ───────────────────────────────────────────────────────────────

def test_run_command_allowed(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("hello")
    ctx = make_context(["ls"])
    result = run_command(f"ls {tmp_path}", context=ctx)
    assert "file.txt" in result


def test_run_command_blocked(tmp_path: Path) -> None:
    ctx = make_context(["ls"])
    with pytest.raises(PermissionError):
        run_command("rm -rf /tmp/test", context=ctx)


def test_run_command_dry_run(tmp_path: Path) -> None:
    ctx = make_context(["ls"])
    result = run_command(f"ls {tmp_path}", context=ctx, dry_run=True)
    assert "dry-run" in result


def test_run_command_nonzero_exit(tmp_path: Path) -> None:
    ctx = make_context(["ls"])
    with pytest.raises(RuntimeError):
        run_command(f"ls /nonexistent_path_xyz", context=ctx)


def test_run_command_not_in_path() -> None:
    ctx = make_context(["definitely-not-a-real-binary"])
    with pytest.raises(RuntimeError, match="not found"):
        run_command("definitely-not-a-real-binary --help", context=ctx)


def test_run_command_empty_context() -> None:
    ctx = make_context([])
    with pytest.raises(PermissionError):
        run_command("echo hello", context=ctx)
