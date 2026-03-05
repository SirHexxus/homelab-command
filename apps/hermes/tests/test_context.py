"""Tests for lib/core/context.py."""

import sys
from pathlib import Path

import pytest
import yaml

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.context import Context, ModelPreferences, load_context, get_default_context_name


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _write_config(tmp_path: Path, content: dict) -> Path:
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.dump(content))
    return config_path


def _write_context(config_path: Path, name: str, content: dict) -> None:
    ctx_dir = config_path.parent / "contexts"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    (ctx_dir / f"{name}.yml").write_text(yaml.dump(content))


# ── Tests: load_context ───────────────────────────────────────────────────────

def test_load_context_minimal(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {"default_context": "personal"})
    _write_context(config_path, "personal", {
        "display_name": "Test",
        "tone": "casual",
        "allowed_paths": [str(tmp_path)],
        "allowed_commands": ["ls"],
    })
    ctx = load_context("personal", config_path)
    assert ctx.name == "personal"
    assert ctx.display_name == "Test"
    assert ctx.tone == "casual"
    assert str(tmp_path) in ctx.allowed_paths
    assert "ls" in ctx.allowed_commands


def test_load_context_default_model_preferences(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {})
    _write_context(config_path, "personal", {
        "allowed_paths": [],
        "allowed_commands": [],
    })
    ctx = load_context("personal", config_path)
    assert ctx.model.ollama_model == "llama3.2"
    assert ctx.model.force_tier is None


def test_load_context_custom_model(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {})
    _write_context(config_path, "personal", {
        "allowed_paths": [],
        "allowed_commands": [],
        "model": {"ollama_model": "mistral", "force_tier": 1},
    })
    ctx = load_context("personal", config_path)
    assert ctx.model.ollama_model == "mistral"
    assert ctx.model.force_tier == 1


def test_load_context_style_guides(tmp_path: Path) -> None:
    guide = tmp_path / "brand.md"
    guide.write_text("# Brand Guide")
    config_path = _write_config(tmp_path, {})
    _write_context(config_path, "personal", {
        "allowed_paths": [],
        "allowed_commands": [],
        "style_guides": [str(guide)],
    })
    ctx = load_context("personal", config_path)
    assert str(guide) in ctx.style_guides


def test_load_context_missing_file_exits(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {})
    with pytest.raises(SystemExit):
        load_context("nonexistent", config_path)


# ── Tests: get_default_context_name ──────────────────────────────────────────

def test_get_default_context_name(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {"default_context": "professional"})
    assert get_default_context_name(config_path) == "professional"


def test_get_default_context_name_fallback(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, {})
    assert get_default_context_name(config_path) == "personal"
