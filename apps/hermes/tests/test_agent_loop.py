"""Tests for lib/core/agent_loop.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.agent_loop import (
    _build_observation_prompt,
    _parse_tool_calls,
    run_agent,
)
from lib.core.context import Context, ModelPreferences


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_context() -> Context:
    return Context(
        name="test",
        display_name="Test",
        tone="casual",
        allowed_paths=[],
        allowed_commands=[],
        model=ModelPreferences(),
    )


# ── _parse_tool_calls ─────────────────────────────────────────────────────────

def test_parse_tool_calls_single() -> None:
    response = '```tool_call\n{"tool": "read_file", "args": {"path": "/tmp/x"}}\n```'
    calls = _parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0]["tool"] == "read_file"
    assert calls[0]["args"]["path"] == "/tmp/x"


def test_parse_tool_calls_none() -> None:
    response = "Here is my answer: no tools needed."
    calls = _parse_tool_calls(response)
    assert calls == []


def test_parse_tool_calls_malformed_json() -> None:
    response = "```tool_call\nnot valid json\n```"
    calls = _parse_tool_calls(response)
    assert calls == []


def test_parse_tool_calls_multiple() -> None:
    response = (
        "```tool_call\n{\"tool\": \"read_file\", \"args\": {\"path\": \"/a\"}}\n```\n"
        "Some text.\n"
        "```tool_call\n{\"tool\": \"list_dir\", \"args\": {\"path\": \"/b\"}}\n```"
    )
    calls = _parse_tool_calls(response)
    assert len(calls) == 2


# ── _build_observation_prompt ─────────────────────────────────────────────────

def test_build_observation_prompt_success() -> None:
    results = [{"tool": "read_file", "output": "file contents"}]
    prompt = _build_observation_prompt(results)
    assert "read_file" in prompt
    assert "file contents" in prompt


def test_build_observation_prompt_error() -> None:
    results = [{"tool": "read_file", "error": "File not found"}]
    prompt = _build_observation_prompt(results)
    assert "error" in prompt.lower()
    assert "File not found" in prompt


# ── run_agent ─────────────────────────────────────────────────────────────────

def test_run_agent_no_tools(tmp_path: Path) -> None:
    ctx = make_context()
    with patch("lib.core.agent_loop.LLMRouter") as MockRouter:
        mock_instance = MagicMock()
        mock_instance.complete.return_value = ("The answer is 42.", "ollama:llama3.2")
        MockRouter.return_value = mock_instance

        result = run_agent("What is the answer?", ctx)
        assert result.answer == "The answer is 42."
        assert len(result.steps) == 1


def test_run_agent_llm_error_returns_error_message() -> None:
    from lib.core.llm import LLMError
    ctx = make_context()
    with patch("lib.core.agent_loop.LLMRouter") as MockRouter:
        mock_instance = MagicMock()
        mock_instance.complete.side_effect = LLMError("Connection refused")
        MockRouter.return_value = mock_instance

        result = run_agent("Do something", ctx)
        assert "error" in result.answer.lower()
