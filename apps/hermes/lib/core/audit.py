"""Append-only JSONL audit log for Hermes.

Every tool call is written as one JSON line to logs/audit.jsonl.
The --usage flag reads this file to print per-model call counts for today.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "audit.jsonl"


# ── Writing ───────────────────────────────────────────────────────────────────

def log_tool_call(
    context_name: str,
    tool: str,
    args: dict[str, Any],
    result: str,
    model: str = "unknown",
    dry_run: bool = False,
) -> None:
    """Append one audit entry to logs/audit.jsonl.

    Args:
        context_name: The active context name (e.g. "personal").
        tool: The skill/tool that was called (e.g. "filesystem.read_file").
        args: Arguments passed to the tool.
        result: Short summary of the outcome.
        model: LLM tier/model that invoked the tool.
        dry_run: Whether the call was a dry-run (no side effects).
    """
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "context": context_name,
        "model": model,
        "tool": tool,
        "args": args,
        "result": result,
        "dry_run": dry_run,
    }

    try:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:
        print(f"Warning: could not write audit log: {exc}", file=sys.stderr)


def log_llm_call(
    context_name: str,
    model: str,
    prompt_summary: str,
    fallback_note: str = "",
) -> None:
    """Log an LLM invocation (not a tool call) for --usage tracking.

    Args:
        context_name: Active context name.
        model: Model/tier used (e.g. "ollama:llama3.2", "gemini", "claude").
        prompt_summary: First 80 chars of the prompt.
        fallback_note: Non-empty if this was a fallback invocation.
    """
    log_tool_call(
        context_name=context_name,
        tool="llm.call",
        args={"prompt_summary": prompt_summary[:80], "fallback": fallback_note},
        result="invoked",
        model=model,
    )


# ── Reading ───────────────────────────────────────────────────────────────────

def read_today_counts() -> dict[str, int]:
    """Return per-model call counts for today (UTC).

    Returns:
        Dict mapping model name → call count for today's UTC date.
        Returns an empty dict if the log file does not exist.
    """
    if not AUDIT_LOG_PATH.exists():
        return {}

    today = datetime.now(timezone.utc).date().isoformat()
    counts: dict[str, int] = defaultdict(int)

    try:
        with AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("ts", "")[:10] == today:
                    model = entry.get("model", "unknown")
                    counts[model] += 1
    except OSError as exc:
        print(f"Warning: could not read audit log: {exc}", file=sys.stderr)

    return dict(counts)


def print_usage_summary() -> None:
    """Print today's per-model call counts to stdout."""
    counts = read_today_counts()
    today = datetime.now(timezone.utc).date().isoformat()

    print(f"Hermes usage summary — {today} (UTC)")
    print()

    if not counts:
        print("  No calls logged today.")
        return

    max_model_len = max(len(m) for m in counts)
    for model, count in sorted(counts.items()):
        bar = "█" * min(count, 40)
        print(f"  {model:<{max_model_len}}  {count:>4}  {bar}")
    print()
    print(f"  Total: {sum(counts.values())}")
