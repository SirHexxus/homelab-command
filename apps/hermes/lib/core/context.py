"""Context dataclass and config loading for Hermes.

A Context encapsulates everything that differs between the personal and
professional personas: allowed paths, allowed shell commands, email
credentials, tone, and model preferences. All agent behaviour is
parameterised through a Context — no separate code paths exist per persona.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yml"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class EmailConfig:
    """IMAP/SMTP credentials for one email account."""

    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_address: str


@dataclass
class ModelPreferences:
    """Per-context model routing preferences."""

    # Complexity score (0–10) at which to escalate from Tier 1 → Tier 2
    ollama_threshold: float = 3.0
    # Complexity score at which to escalate from Tier 2 → Tier 3
    gemini_threshold: float = 7.0
    # Ollama model name to use for this context
    ollama_model: str = "llama3.2"
    # Force a specific tier (1, 2, 3) — None means use routing logic
    force_tier: int | None = None


@dataclass
class Context:
    """All configuration that varies between personal and professional modes.

    Loaded from config/contexts/<name>.yml and merged with global config.
    """

    name: str
    display_name: str
    tone: str                                  # "casual" | "professional"
    allowed_paths: list[str]
    allowed_commands: list[str]
    ollama_base_url: str = "http://localhost:11434"
    model: ModelPreferences = field(default_factory=ModelPreferences)
    email: EmailConfig | None = None
    # Paths to style/brand guide files injected into every system prompt
    style_guides: list[str] = field(default_factory=list)


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_global_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and return the global config.yml as a dict.

    Args:
        config_path: Path to config.yml. Defaults to config/config.yml
                     relative to the project root.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If config_path does not exist.
        ValueError: If the YAML is malformed.
    """
    if not config_path.exists():
        print(
            f"Error: config file not found: {config_path}\n"
            f"Copy config/config.example.yml to config/config.yml and edit it.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        return yaml.safe_load(config_path.read_text()) or {}
    except yaml.YAMLError as exc:
        print(f"Error: malformed YAML in {config_path}: {exc}", file=sys.stderr)
        sys.exit(1)


def load_context(name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> Context:
    """Load a named context from config/contexts/<name>.yml.

    Args:
        name: Context name, e.g. "personal" or "professional".
        config_path: Path to global config.yml. Used to resolve the default
                     context and the config directory.

    Returns:
        A fully populated Context dataclass.

    Raises:
        SystemExit: On missing file or malformed YAML.
    """
    context_path = config_path.parent / "contexts" / f"{name}.yml"

    if not context_path.exists():
        example = context_path.with_suffix(".example.yml")
        hint = f"Copy {example} to {context_path} and edit it." if example.exists() else ""
        print(f"Error: context file not found: {context_path}. {hint}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = yaml.safe_load(context_path.read_text()) or {}
    except yaml.YAMLError as exc:
        print(f"Error: malformed YAML in {context_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    model_raw = raw.get("model", {})
    model = ModelPreferences(
        ollama_threshold=model_raw.get("ollama_threshold", 3.0),
        gemini_threshold=model_raw.get("gemini_threshold", 7.0),
        ollama_model=model_raw.get("ollama_model", "llama3.2"),
        force_tier=model_raw.get("force_tier", None),
    )

    email_raw = raw.get("email")
    email = None
    if email_raw:
        required = ["imap_host", "imap_port", "smtp_host", "smtp_port",
                    "username", "password", "from_address"]
        missing = [k for k in required if k not in email_raw]
        if missing:
            print(
                f"Error: context '{name}' email config missing keys: {', '.join(missing)}",
                file=sys.stderr,
            )
            sys.exit(1)
        email = EmailConfig(**{k: email_raw[k] for k in required})

    global_cfg = load_global_config(config_path)

    return Context(
        name=name,
        display_name=raw.get("display_name", name),
        tone=raw.get("tone", "casual"),
        allowed_paths=raw.get("allowed_paths", []),
        allowed_commands=raw.get("allowed_commands", []),
        ollama_base_url=global_cfg.get("ollama_base_url", "http://localhost:11434"),
        model=model,
        email=email,
        style_guides=raw.get("style_guides", []),
    )


def get_default_context_name(config_path: Path = DEFAULT_CONFIG_PATH) -> str:
    """Return the default_context value from global config.

    Falls back to "personal" if the key is absent.
    """
    cfg = load_global_config(config_path)
    return cfg.get("default_context", "personal")
