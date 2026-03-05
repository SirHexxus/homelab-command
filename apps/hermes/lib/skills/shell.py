"""Shell skill — whitelisted command execution for Hermes.

Only commands explicitly listed in context.allowed_commands may be run.
The whitelist is checked against the first token of the command string.
No shell interpolation is used — subprocess runs with shell=False.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from lib.core.context import Context
from lib.core.skill_registry import register_skill

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_TIMEOUT_SECONDS = 60


# ── Security helpers ──────────────────────────────────────────────────────────

def _check_command_allowed(command_parts: list[str], context: Context) -> None:
    """Verify the command's base executable is in the allowed_commands whitelist.

    Args:
        command_parts: The command split into a list (e.g. ["ls", "-la"]).
        context: Active context whose allowed_commands list is checked.

    Raises:
        PermissionError: If the base command is not whitelisted.
    """
    if not command_parts:
        raise ValueError("Empty command")

    base_cmd = Path(command_parts[0]).name  # strip any path prefix

    if base_cmd not in context.allowed_commands:
        allowed_display = ", ".join(context.allowed_commands) or "(none)"
        raise PermissionError(
            f"Command '{base_cmd}' is not in the allowed_commands list for "
            f"context '{context.name}'. Allowed: {allowed_display}"
        )


def _split_command(command: str) -> list[str]:
    """Split a command string into parts using shlex-style splitting.

    Uses the stdlib shlex module to handle quoted arguments correctly without
    invoking a shell.
    """
    import shlex
    return shlex.split(command)


# ── Skills ────────────────────────────────────────────────────────────────────

@register_skill()
def run_command(
    command: str,
    context: Context,
    dry_run: bool = False,
    working_dir: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Run a whitelisted shell command and return its output.

    The command's base executable must appear in context.allowed_commands.
    The command is run without a shell (no interpolation, no injection risk).

    Args:
        command: The command string to execute (e.g. "ls -la /tmp").
        context: Active context (used for whitelist check).
        dry_run: If True, describe the command without running it.
        working_dir: Optional working directory for the command.
        timeout: Maximum seconds to wait (default 60).

    Returns:
        Combined stdout + stderr from the command.

    Raises:
        PermissionError: If the command is not whitelisted.
        subprocess.TimeoutExpired: If the command exceeds the timeout.
        RuntimeError: If the command exits with a non-zero status.
    """
    parts = _split_command(command)
    _check_command_allowed(parts, context)

    cwd = Path(working_dir).expanduser().resolve() if working_dir else None

    if dry_run:
        cwd_note = f" (cwd: {cwd})" if cwd else ""
        return f"[dry-run] Would run: {' '.join(parts)}{cwd_note}"

    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        raise subprocess.TimeoutExpired(parts, timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Command not found: {parts[0]}") from exc

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += result.stderr

    if result.returncode != 0:
        raise RuntimeError(
            f"Command exited with code {result.returncode}:\n{output}"
        )

    return output.strip() if output.strip() else "(no output)"


@register_skill()
def run_ansible(
    playbook: str,
    inventory: str,
    context: Context,
    dry_run: bool = False,
    extra_vars: str = "",
) -> str:
    """Run an Ansible playbook via ansible-playbook.

    'ansible-playbook' must be in context.allowed_commands.

    Args:
        playbook: Path to the playbook YAML file.
        inventory: Path to the inventory file or hostname.
        context: Active context (whitelist check).
        dry_run: If True, adds --check flag (Ansible dry-run mode).
        extra_vars: Optional --extra-vars string.

    Returns:
        Ansible output.
    """
    parts = ["ansible-playbook", playbook, "-i", inventory]
    if dry_run:
        parts.append("--check")
    if extra_vars:
        parts.extend(["--extra-vars", extra_vars])

    _check_command_allowed(parts, context)

    if dry_run:
        return f"[dry-run] Would run: {' '.join(parts)}"

    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=300,  # Ansible plays can take a while
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ansible-playbook not found in PATH") from exc

    output = result.stdout + result.stderr

    if result.returncode != 0:
        raise RuntimeError(
            f"Ansible exited with code {result.returncode}:\n{output}"
        )

    return output.strip() if output.strip() else "(no output)"
