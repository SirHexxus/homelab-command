# Hermes (Application)

Python application code for the Hermes AI agent — a ReAct (Reason + Act) loop that receives
tasks in natural language and executes them autonomously. For the LXC provisioning IaC, see
`infrastructure/hermes/CLAUDE.md`.

## Components

The application runs on a single LXC (VMID 110, 10.0.50.17, VLAN 50).
In Phase 3+, it will expose additional endpoints:

| Interface | Phase | Notes |
|-----------|-------|-------|
| CLI (`bin/hermes`) | 1 — current | `hermes "do something"` |
| Telegram bots | 3 | One per context: personal, professional |
| FastAPI web UI | 4 | Domain-based context routing |

## App Structure

```
apps/hermes/
  bin/
    hermes             ← CLI entrypoint
  config/
    contexts/          ← YAML per context (personal, professional)
  lib/
    core/
      agent_loop.py    ← ReAct loop — thinks, picks tool, acts, observes
      context.py       ← Context dataclass; loads + validates context YAML
      llm.py           ← LLM clients + tier router (Ollama → Gemini → Claude)
      skill_registry.py
      audit.py         ← logs/audit.jsonl (every tool call + LLM invocation)
    skills/
      filesystem.py
      shell.py
      mneme.py         ← Mnemosyne Postgres client
      web.py
      email.py
  tests/
  requirements.txt
  README.md
```

## Runtime Dependencies

| Service | Address | Purpose |
|---------|---------|---------|
| Ollama | 10.0.50.10:11434 | Tier 1 LLM inference (Mistral 7B) |
| Postgres/Mnemosyne | 10.0.50.14:5432 | Persistent memory — knowledge base |
| n8n | 10.0.50.13:5678 | Multi-step workflow execution |
| Redis | 10.0.50.15:6379 | Ephemeral state, model routing counters |

External APIs (Tier 2/3 LLM fallback): Gemini API, Claude API

## LLM Tier Routing

1. **Ollama** (local, free) — default for all tasks
2. **Gemini API** — fallback if Ollama fails or task requires it
3. **Claude API** — fallback of last resort

## Design Doc

`docs/hermes-design-doc-v1.0.md` — full ReAct loop architecture, context system, skills
framework, LLM tier routing, Phase 1–5 build plan.

## Notes

- Each context (personal/professional) has its own allowed paths, whitelisted commands,
  LLM preferences, and email credentials — switching context changes all of these at once
- Long-term state lives in Mnemosyne (Postgres), not local files — local state is ephemeral
- Audit log at `logs/audit.jsonl` — every tool call and LLM invocation is recorded
- Phase 1 (CLI) is the current target; do not build Phase 3/4 features ahead of schedule
