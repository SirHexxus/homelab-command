"""LLM clients and router for Hermes.

Three tiers:
  1. local  — OllamaClient (default; free; no network beyond VLAN 50)
  2. gemini — GeminiClient via google-generativeai SDK (wiki_write, synthesis)
  3. claude — ClaudeClient via `claude -p` subprocess (judgment tasks only)

All clients share the same interface: .complete(prompt, system) → str.
The router maps task_type strings to a starting tier and runs a waterfall
fallback (local → gemini → claude) when QuotaExceeded is raised.

Fixed tiers (nomic, whisper) bypass the waterfall entirely.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

import httpx

from lib.core.context import Context, load_global_config

# ── Constants ─────────────────────────────────────────────────────────────────
OLLAMA_TIMEOUT_SECONDS = 300

# Tier name constants
_TIER_LOCAL = "local"
_TIER_GEMINI = "gemini"
_TIER_CLAUDE = "claude"
_TIER_NOMIC = "nomic"
_TIER_WHISPER = "whisper"

# Default routing table — overridden by model_routing: in config.yml
_DEFAULT_ROUTING: dict[str, str] = {
    "classify":   _TIER_LOCAL,
    "wiki_read":  _TIER_LOCAL,
    "wiki_write": _TIER_GEMINI,
    "synthesis":  _TIER_GEMINI,
    "judgment":   _TIER_CLAUDE,
    "report":     _TIER_GEMINI,
    "embed":      _TIER_NOMIC,
    "transcribe": _TIER_WHISPER,
    "default":    _TIER_LOCAL,
}


# ── Exceptions ────────────────────────────────────────────────────────────────

class QuotaExceeded(Exception):
    """Raised when a tier hits its rate/usage limit.

    The router catches this and advances to the next tier in the waterfall.
    """


class LLMError(Exception):
    """Raised for unrecoverable LLM errors (misconfiguration, auth failure, etc.)

    Not caught by the waterfall — propagates immediately to the caller.
    """


# ── Tier 1 — Ollama (local) ───────────────────────────────────────────────────

class OllamaClient:
    """Synchronous Ollama client using the /api/chat endpoint.

    Raises:
        LLMError: On HTTP errors, connection failure, or unexpected response shape.
    """

    def __init__(self, model: str = "mistral:7b", base_url: str = "http://10.0.50.10:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, prompt: str, system: str = "") -> str:
        """Send a prompt to Ollama and return the assistant's reply.

        Args:
            prompt: The user message.
            system: Optional system prompt.

        Returns:
            The assistant's text response.

        Raises:
            LLMError: On connection failure, HTTP error, or unexpected response.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=OLLAMA_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is the Ollama server running?"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Ollama HTTP error {exc.response.status_code}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMError(
                f"Ollama request timed out after {OLLAMA_TIMEOUT_SECONDS}s"
            ) from exc

        try:
            data = response.json()
            return data["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise LLMError(f"Unexpected Ollama response shape: {exc}") from exc

    def __repr__(self) -> str:
        return f"OllamaClient(model={self.model!r})"


# ── Tier 2 — Gemini ───────────────────────────────────────────────────────────

class GeminiClient:
    """Google Gemini client via the google-generativeai SDK.

    API key resolved from env var GEMINI_API_KEY, then from the gemini_api_key
    field in config.yml (passed in at construction time).

    Raises:
        QuotaExceeded: On 429 / resource exhausted errors.
        LLMError: On missing credentials, import failure, or other API errors.
    """

    def __init__(self, model: str = "gemini-1.5-flash", api_key: str = "") -> None:
        self.model = model
        self._api_key = api_key

    def _resolve_key(self) -> str:
        key = os.environ.get("GEMINI_API_KEY", "") or self._api_key
        if not key:
            raise LLMError(
                "Gemini API key not set. "
                "Export GEMINI_API_KEY or add gemini_api_key to config.yml."
            )
        return key

    def complete(self, prompt: str, system: str = "") -> str:
        """Send a prompt to Gemini and return the assistant's reply.

        Args:
            prompt: The user message.
            system: Optional system instruction.

        Returns:
            The assistant's text response.

        Raises:
            QuotaExceeded: On rate-limit / quota errors.
            LLMError: On credential or API errors.
        """
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise LLMError(
                "google-generativeai is not installed. "
                "Run: pip install -r requirements.txt"
            ) from exc

        genai.configure(api_key=self._resolve_key())
        gen_model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system or None,
        )

        try:
            response = gen_model.generate_content(prompt)
            return response.text
        except Exception as exc:
            exc_str = str(exc).lower()
            if "quota" in exc_str or "429" in exc_str or "resource exhausted" in exc_str:
                raise QuotaExceeded(f"Gemini quota exceeded: {exc}") from exc
            raise LLMError(f"Gemini error: {exc}") from exc

    def __repr__(self) -> str:
        return f"GeminiClient(model={self.model!r})"


# ── Tier 3 — Claude (via Claude Code CLI) ─────────────────────────────────────

class ClaudeClient:
    """Claude client via `claude -p` subprocess (Claude Code CLI).

    Uses the existing Claude Pro account OAuth authentication on the host.
    No API key required — requires Claude Code installed and authenticated.

    Install on a new host:  npm install -g @anthropic-ai/claude-code
    Authenticate:           claude auth login  (one-time OAuth flow)

    Raises:
        QuotaExceeded: On rate-limit responses from Claude.
        LLMError: On missing/unauthenticated CLI, subprocess failure.
    """

    def __init__(self, model: str = "sonnet") -> None:
        self.model = model  # alias: haiku | sonnet | opus

    def _check_available(self) -> None:
        """Raise LLMError if `claude` is not installed or not authenticated."""
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise LLMError(
                "Claude Code is not installed or not authenticated on this host.\n"
                "  Install:      npm install -g @anthropic-ai/claude-code\n"
                "  Authenticate: claude auth login"
            )

    def complete(self, prompt: str, system: str = "") -> str:
        """Send a prompt to Claude via the `claude -p` CLI and return the reply.

        Args:
            prompt: The user message.
            system: Optional system prompt (appended to Claude Code's default).

        Returns:
            The assistant's text response (trailing whitespace stripped).

        Raises:
            QuotaExceeded: On rate-limit responses.
            LLMError: On CLI failure or unauthenticated state.
        """
        self._check_available()

        cmd = ["claude", "-p", prompt, "--model", self.model]
        if system:
            cmd += ["--append-system-prompt", system]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").lower()
            if "rate" in err or "limit" in err or "quota" in err or "overloaded" in err:
                raise QuotaExceeded(f"Claude rate-limited: {result.stderr.strip()}")
            raise LLMError(
                f"claude -p exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
            )

        return result.stdout.strip()

    def __repr__(self) -> str:
        return f"ClaudeClient(model={self.model!r})"


# ── Router ────────────────────────────────────────────────────────────────────

class LLMRouter:
    """Routes prompts to the appropriate LLM tier based on task_type.

    Resolution order:
      1. If context.model.force_tier is set, use that tier unconditionally.
      2. Look up task_type in the model_routing table from config.yml.
      3. Execute waterfall from the resolved starting tier: local → gemini → claude.
         Fixed tiers (nomic, whisper) are dispatched directly — no waterfall.

    Only QuotaExceeded advances the waterfall. LLMError propagates immediately.

    Attributes:
        context: The active Hermes context.
        _routing: task_type → tier name, merged from defaults + config.yml.
    """

    def __init__(self, context: Context) -> None:
        self.context = context
        self._ollama = OllamaClient(
            model=context.model.ollama_model,
            base_url=context.ollama_base_url,
        )
        # Lazy — only constructed when first needed
        self._gemini: GeminiClient | None = None
        self._claude: ClaudeClient | None = None

        global_cfg = load_global_config()
        raw_routing = global_cfg.get("model_routing", {})
        self._routing: dict[str, str] = {**_DEFAULT_ROUTING, **raw_routing}

        self._gemini_key: str = global_cfg.get("gemini_api_key", "")
        self._claude_model: str = global_cfg.get("claude_model", "sonnet")

    def _get_gemini(self) -> GeminiClient:
        if self._gemini is None:
            self._gemini = GeminiClient(api_key=self._gemini_key)
        return self._gemini

    def _get_claude(self) -> ClaudeClient:
        if self._claude is None:
            self._claude = ClaudeClient(model=self._claude_model)
        return self._claude

    def _resolve_start_tier(self, task_type: str) -> str:
        """Return the starting tier name for the given task_type."""
        return self._routing.get(task_type, self._routing.get("default", _TIER_LOCAL))

    def complete(
        self,
        prompt: str,
        system: str = "",
        task_type: str = "default",
    ) -> tuple[str, str]:
        """Route a prompt to the best available LLM and return the response.

        Args:
            prompt: The user/agent prompt.
            system: Optional system prompt.
            task_type: Logical task category (e.g. "wiki_write", "judgment").
                       Defaults to "default" — backward-compatible with existing callers.

        Returns:
            Tuple of (response_text, model_name_used).

        Raises:
            LLMError: If the chosen tier fails for a non-quota reason, or all
                      waterfall tiers are exhausted.
        """
        force = self.context.model.force_tier
        if force is not None:
            start_tier = {1: _TIER_LOCAL, 2: _TIER_GEMINI, 3: _TIER_CLAUDE}.get(
                force, _TIER_LOCAL
            )
        else:
            start_tier = self._resolve_start_tier(task_type)

        # Fixed tiers: dispatch directly, no waterfall
        if start_tier == _TIER_NOMIC:
            nomic = OllamaClient(model="nomic-embed-text", base_url=self.context.ollama_base_url)
            reply = nomic.complete(prompt, system=system)
            return reply, "ollama:nomic-embed-text"

        if start_tier == _TIER_WHISPER:
            raise LLMError(
                "Whisper transcription tier is not yet implemented. "
                "Use the transcribe_audio skill directly."
            )

        # Waterfall: local → gemini → claude, starting from start_tier
        waterfall = [_TIER_LOCAL, _TIER_GEMINI, _TIER_CLAUDE]
        try:
            start_idx = waterfall.index(start_tier)
        except ValueError:
            start_idx = 0

        quota_errors: list[str] = []

        for tier in waterfall[start_idx:]:
            try:
                if tier == _TIER_LOCAL:
                    reply = self._ollama.complete(prompt, system=system)
                    return reply, f"ollama:{self._ollama.model}"
                elif tier == _TIER_GEMINI:
                    client = self._get_gemini()
                    reply = client.complete(prompt, system=system)
                    return reply, f"gemini:{client.model}"
                elif tier == _TIER_CLAUDE:
                    client = self._get_claude()
                    reply = client.complete(prompt, system=system)
                    return reply, f"claude:{client.model}"
            except QuotaExceeded as exc:
                print(
                    f"Warning: {tier} quota exceeded, falling back: {exc}",
                    file=sys.stderr,
                )
                quota_errors.append(f"{tier}: quota exceeded")
            # LLMError re-raises immediately — do not swallow misconfiguration

        raise LLMError(
            f"All LLM tiers exhausted for task_type={task_type!r}. "
            f"Quota errors: {'; '.join(quota_errors)}"
        )

    def __repr__(self) -> str:
        return f"LLMRouter(context={self.context.name!r})"
