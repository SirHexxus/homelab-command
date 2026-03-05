"""LLM clients and router for Hermes.

Phase 1: OllamaClient only.
Phase 2 adds: GeminiClient, ClaudeSubprocess, LLMRouter with fallback waterfall.

All clients raise QuotaExceeded when they hit a rate/usage limit so the router
can fall back gracefully and prepend a visible note to the response.
"""

from __future__ import annotations

import sys
from typing import Any

import httpx

from lib.core.context import Context

# ── Constants ─────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TIMEOUT_SECONDS = 120


# ── Exceptions ────────────────────────────────────────────────────────────────

class QuotaExceeded(Exception):
    """Raised by any LLM client when it hits a usage/rate limit.

    The router catches this and falls back to the next tier.
    """


class LLMError(Exception):
    """Raised for unrecoverable LLM errors (not quota-related)."""


# ── Tier 1 — Ollama (local) ───────────────────────────────────────────────────

class OllamaClient:
    """Synchronous Ollama client using the /api/chat endpoint.

    Raises:
        QuotaExceeded: Never — Ollama is local and has no quota. Included for
                       interface parity; could fire if the server is down and
                       you wish to fall back to a cloud model.
        LLMError: On HTTP errors or unexpected response shape.
    """

    def __init__(self, model: str = "llama3.2", base_url: str = OLLAMA_BASE_URL) -> None:
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
            LLMError: On connection failure or unexpected response.
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
            raise LLMError(f"Ollama HTTP error {exc.response.status_code}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise LLMError(f"Ollama request timed out after {OLLAMA_TIMEOUT_SECONDS}s") from exc

        try:
            data = response.json()
            return data["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise LLMError(f"Unexpected Ollama response shape: {exc}") from exc

    def __repr__(self) -> str:
        return f"OllamaClient(model={self.model!r})"


# ── Router (Phase 1: single-tier) ─────────────────────────────────────────────

class LLMRouter:
    """Routes prompts to the appropriate LLM tier based on context preferences.

    Phase 1: always uses Ollama (Tier 1). Phase 2 will add fallback waterfall.

    Attributes:
        context: The active Hermes context (determines model preferences).
        _ollama: Ollama client instance.
    """

    def __init__(self, context: Context) -> None:
        self.context = context
        self._ollama = OllamaClient(model=context.model.ollama_model)

    def complete(self, prompt: str, system: str = "") -> tuple[str, str]:
        """Route a prompt to the best available LLM and return the response.

        Args:
            prompt: The user/agent prompt.
            system: Optional system prompt.

        Returns:
            Tuple of (response_text, model_name_used).

        Raises:
            LLMError: If all tiers fail.
        """
        force = self.context.model.force_tier

        if force == 1 or force is None:
            try:
                reply = self._ollama.complete(prompt, system=system)
                return reply, f"ollama:{self._ollama.model}"
            except QuotaExceeded:
                # Phase 2: fall to Gemini here
                pass
            except LLMError as exc:
                print(f"Error: Ollama failed: {exc}", file=sys.stderr)
                raise

        raise LLMError("All LLM tiers failed or are unavailable.")

    def __repr__(self) -> str:
        return f"LLMRouter(context={self.context.name!r})"
