"""ReAct agent loop for Hermes.

Implements the Reason → Act → Observe cycle:
  1. Send task + available tools to the LLM
  2. Parse any tool calls from the response
  3. Execute each tool call through the skill registry
  4. Feed results back to the LLM
  5. Repeat until the LLM produces a final answer (no tool calls)

The loop is bounded by MAX_STEPS to prevent runaway execution.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from lib.core.audit import log_llm_call, log_tool_call
from lib.core.context import Context
from lib.core.llm import LLMError, LLMRouter
from lib.core.skill_registry import get_skill, skills_prompt_block

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_STEPS = 10

# The LLM must emit tool calls in this JSON format inside a fenced code block:
#   ```tool_call
#   {"tool": "skill_name", "args": {"arg1": "value1"}}
#   ```
TOOL_CALL_PATTERN = re.compile(
    r"```tool_call\s*\n(.*?)\n```",
    re.DOTALL,
)


# ── Data ──────────────────────────────────────────────────────────────────────

@dataclass
class StepResult:
    """Result of one agent step."""

    step: int
    llm_response: str
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    model_used: str


@dataclass
class AgentResult:
    """Final result returned to the caller after the loop completes."""

    answer: str
    steps: list[StepResult] = field(default_factory=list)
    fallback_notes: list[str] = field(default_factory=list)
    model_used: str = "unknown"


# ── Prompt builder ────────────────────────────────────────────────────────────

def _load_style_guides(context: Context) -> str:
    """Load and concatenate style/brand guide files for this context.

    Returns an empty string if no guides are configured or if files are missing
    (missing files produce a warning but do not abort).
    """
    if not context.style_guides:
        return ""

    sections: list[str] = []
    for raw_path in context.style_guides:
        guide_path = Path(raw_path).expanduser().resolve()
        if not guide_path.exists():
            print(
                f"Warning: style guide not found: {guide_path}",
                file=sys.stderr,
            )
            continue
        try:
            content = guide_path.read_text(encoding="utf-8", errors="replace")
            sections.append(f"## Style/Brand Guide: {guide_path.name}\n\n{content}")
        except OSError as exc:
            print(f"Warning: could not read style guide {guide_path}: {exc}", file=sys.stderr)

    if not sections:
        return ""

    return (
        "\n\n---\n\n"
        "# Style and Brand Guidelines\n\n"
        "You MUST follow these guidelines in all responses for this context:\n\n"
        + "\n\n---\n\n".join(sections)
    )


def _build_system_prompt(context: Context) -> str:
    """Build the system prompt injected at the start of every conversation."""
    tone_instruction = (
        "You are a casual, direct assistant." if context.tone == "casual"
        else "You are a professional, precise assistant."
    )
    style_section = _load_style_guides(context)
    return f"""{tone_instruction}
You are Hermes, a personal AI agent operating in the '{context.display_name}' context.

When you need to use a tool, emit exactly one JSON object inside a ```tool_call``` fence:

```tool_call
{{"tool": "tool_name", "args": {{"key": "value"}}}}
```

You may call multiple tools across multiple turns. When you have all the information
needed to answer, reply with plain text (no tool_call fence) — that ends the loop.

{skills_prompt_block()}{style_section}
"""


def _build_observation_prompt(tool_results: list[dict[str, Any]]) -> str:
    """Format tool results as an observation message for the next LLM turn."""
    parts = []
    for res in tool_results:
        tool = res.get("tool", "unknown")
        output = res.get("output", "")
        error = res.get("error")
        if error:
            parts.append(f"Tool '{tool}' error: {error}")
        else:
            parts.append(f"Tool '{tool}' result:\n{output}")
    return "\n\n".join(parts)


# ── Tool call parsing ─────────────────────────────────────────────────────────

def _parse_tool_calls(llm_response: str) -> list[dict[str, Any]]:
    """Extract all tool_call JSON blocks from an LLM response.

    Args:
        llm_response: Raw text from the LLM.

    Returns:
        List of parsed tool call dicts, each with "tool" and "args" keys.
        Empty list if the response contains no tool calls.
    """
    calls = []
    for match in TOOL_CALL_PATTERN.finditer(llm_response):
        raw_json = match.group(1).strip()
        try:
            call = json.loads(raw_json)
            if "tool" in call:
                calls.append(call)
        except json.JSONDecodeError:
            # Malformed JSON — skip silently; the loop will treat it as no-op
            pass
    return calls


# ── Tool execution ────────────────────────────────────────────────────────────

def _execute_tool(
    tool_call: dict[str, Any],
    context: Context,
    dry_run: bool,
    model_used: str,
) -> dict[str, Any]:
    """Execute a single tool call and return a result dict.

    Args:
        tool_call: Dict with "tool" and "args" keys.
        context: The active Context.
        dry_run: Whether to suppress side effects.
        model_used: Model name for audit logging.

    Returns:
        Dict with "tool", "output" (on success), or "error" (on failure).
    """
    tool_name = tool_call.get("tool", "")
    args = tool_call.get("args", {})

    skill_fn = get_skill(tool_name)
    if skill_fn is None:
        error_msg = f"Unknown tool: '{tool_name}'"
        log_tool_call(
            context_name=context.name,
            tool=tool_name,
            args=args,
            result=f"ERROR: {error_msg}",
            model=model_used,
            dry_run=dry_run,
        )
        return {"tool": tool_name, "error": error_msg}

    try:
        output = skill_fn(context=context, dry_run=dry_run, **args)
        result_summary = str(output)[:200]
        log_tool_call(
            context_name=context.name,
            tool=tool_name,
            args=args,
            result=result_summary,
            model=model_used,
            dry_run=dry_run,
        )
        return {"tool": tool_name, "output": output}
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)
        log_tool_call(
            context_name=context.name,
            tool=tool_name,
            args=args,
            result=f"ERROR: {error_msg}",
            model=model_used,
            dry_run=dry_run,
        )
        return {"tool": tool_name, "error": error_msg}


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_agent(
    task: str,
    context: Context,
    dry_run: bool = False,
    verbose: bool = False,
) -> AgentResult:
    """Run the ReAct loop for a single task.

    Args:
        task: The natural-language task from the user.
        context: The active Hermes context.
        dry_run: If True, tool calls that modify state are skipped.
        verbose: If True, print each step's LLM response to stderr.

    Returns:
        AgentResult with the final answer and step history.
    """
    router = LLMRouter(context)
    system_prompt = _build_system_prompt(context)

    # Conversation history: list of {"role": ..., "content": ...}
    conversation: list[dict[str, str]] = [{"role": "user", "content": task}]
    steps: list[StepResult] = []
    fallback_notes: list[str] = []
    model_used = f"ollama:{context.model.ollama_model}"

    for step_num in range(1, MAX_STEPS + 1):
        # Build the prompt: system + full conversation so far
        full_prompt = "\n\n".join(msg["content"] for msg in conversation)

        try:
            llm_response, model_used = router.complete(full_prompt, system=system_prompt)
        except LLMError as exc:
            print(f"Error: LLM failed at step {step_num}: {exc}", file=sys.stderr)
            return AgentResult(
                answer=f"Error: the agent could not complete the task: {exc}",
                steps=steps,
                fallback_notes=fallback_notes,
                model_used=model_used,
            )

        log_llm_call(
            context_name=context.name,
            model=model_used,
            prompt_summary=task,
        )

        if verbose:
            print(f"\n[Step {step_num}] {model_used}\n{llm_response}", file=sys.stderr)

        tool_calls = _parse_tool_calls(llm_response)

        if not tool_calls:
            # No tool calls → this is the final answer
            step_result = StepResult(
                step=step_num,
                llm_response=llm_response,
                tool_calls=[],
                tool_results=[],
                model_used=model_used,
            )
            steps.append(step_result)
            break

        # Execute each tool call
        tool_results = [
            _execute_tool(tc, context, dry_run, model_used)
            for tc in tool_calls
        ]

        steps.append(StepResult(
            step=step_num,
            llm_response=llm_response,
            tool_calls=tool_calls,
            tool_results=tool_results,
            model_used=model_used,
        ))

        # Append assistant turn + observation to conversation
        conversation.append({"role": "assistant", "content": llm_response})
        observation = _build_observation_prompt(tool_results)
        conversation.append({"role": "user", "content": observation})
    else:
        # Exceeded MAX_STEPS
        llm_response = (
            f"[Agent reached the {MAX_STEPS}-step safety limit without a final answer. "
            "The task may be too complex or the model is in a loop.]"
        )

    prefix = ""
    if fallback_notes:
        prefix = "\n".join(f"[{note}]" for note in fallback_notes) + "\n\n"

    return AgentResult(
        answer=prefix + llm_response,
        steps=steps,
        fallback_notes=fallback_notes,
        model_used=model_used,
    )
