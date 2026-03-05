"""Skill registry — discovers and surfaces available tools to the agent loop.

Skills are plain Python functions decorated with @register_skill. The registry
collects their names and docstrings so the LLM can be told what tools exist.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

# ── Types ─────────────────────────────────────────────────────────────────────
SkillFn = Callable[..., Any]

# ── Registry state ────────────────────────────────────────────────────────────
_SKILLS: dict[str, SkillFn] = {}


def register_skill(name: str | None = None) -> Callable[[SkillFn], SkillFn]:
    """Decorator that registers a function as a named Hermes skill.

    Args:
        name: Override the skill name. Defaults to the function name.

    Usage::

        @register_skill()
        def read_file(path: str, context: Context) -> str:
            ...

        @register_skill(name="fs.list")
        def list_dir(path: str, context: Context) -> str:
            ...
    """
    def decorator(fn: SkillFn) -> SkillFn:
        skill_name = name or fn.__name__
        _SKILLS[skill_name] = fn
        return fn
    return decorator


def get_skill(name: str) -> SkillFn | None:
    """Return the skill function for the given name, or None if not found."""
    return _SKILLS.get(name)


def list_skills() -> list[dict[str, str]]:
    """Return a list of all registered skills with name and description.

    Returns:
        List of dicts with keys "name" and "description".
    """
    result = []
    for skill_name, fn in sorted(_SKILLS.items()):
        doc = inspect.getdoc(fn) or ""
        # Use only the first sentence of the docstring as a short description
        short_doc = doc.split(".")[0].strip() if doc else "(no description)"
        result.append({"name": skill_name, "description": short_doc})
    return result


def skills_prompt_block() -> str:
    """Format registered skills as a compact block for injection into prompts.

    Returns:
        Multi-line string listing each skill and its one-line description.
    """
    skills = list_skills()
    if not skills:
        return "No skills registered."
    lines = ["Available tools:"]
    for skill in skills:
        lines.append(f"  {skill['name']}: {skill['description']}")
    return "\n".join(lines)
