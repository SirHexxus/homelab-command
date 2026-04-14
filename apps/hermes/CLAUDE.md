# Hermes (Application)

**Claude's role in this directory: Project Manager for the Hermes application.**
Read `ToDo.md` for the current task backlog. Read `Mnemosyne-Hand-Off.md` for the
requirements spec from the Mnemosyne project. Read `THOUGHTS.md` for the user's design
rationale and open questions. Do not implement features not in the backlog without checking.

Python application code for the Hermes AI agent — a ReAct (Reason + Act) loop that receives
tasks in natural language and executes them autonomously. For the LXC provisioning IaC, see
`infrastructure/hermes/CLAUDE.md`.

See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.

## Components

The application runs on a single LXC (VMID 110, 10.0.50.17, VLAN 50).

| Interface | Phase | Notes |
|-----------|-------|-------|
| CLI (`bin/hermes`) | 1 — done | `hermes "do something"` |
| HTTP endpoint (`/task`, `/health`) | 2 — done | n8n integration; internal VLAN 50 only |
| Telegram bots | 2 | Personal bot first; professional bot later |
| FastAPI web UI | 4 | Domain-based context routing — do not build early |

## App Structure

```
apps/hermes/
  bin/
    hermes             ← CLI entrypoint
    hermes-api         ← API server entrypoint (Phase 2)
  config/
    contexts/          ← YAML per context (personal, professional)
  lib/
    core/
      agent_loop.py    ← ReAct loop — thinks, picks tool, acts, observes
      context.py       ← Context dataclass; loads + validates context YAML
      ingest.py        ← IngestItem dataclass — normalized ingestion envelope (Phase 2)
      llm.py           ← LLM clients + tier router (Ollama → Gemini → Claude)
      skill_registry.py
      audit.py         ← logs/audit.jsonl (every tool call + LLM invocation)
    interfaces/
      api.py           ← Minimal HTTP endpoint: POST /task, GET /health (Phase 2)
      telegram_bot.py  ← Personal Telegram bot (Phase 2 — not yet built)
    skills/
      _archive/        ← Deprecated skills (mneme_postgres.py lives here)
      wiki.py          ← Mnemosyne wiki read/write skills (7 skills registered)
      filesystem.py
      shell.py
  tests/
  requirements.txt
  README.md
```

Note: `lib/skills/mneme_postgres.py` (Postgres/pgvector) is archived to `_archive/`.
Do not use or adapt it. The replacement is `lib/skills/wiki.py`.

## Runtime Dependencies

| Service | Address | Purpose |
|---------|---------|---------|
| Ollama | 10.0.50.10:11434 | Tier 1 LLM inference (Qwen3-8B default) |
| Whisper | 10.0.50.12 | Audio transcription — fixed destination, never routed to cloud |
| n8n | 10.0.50.13:5678 | Multi-step workflow orchestration |
| Mnemosyne wiki repo | git clone on LXC | Markdown wiki — read/written by `wiki.py` skill |

External APIs: Gemini Flash (wiki writes, synthesis), Claude Sonnet (judgment tasks)

## LLM Tier Routing

Routing is task_type-driven, not complexity-score-driven. Config lives in `config/config.yml`
under `model_routing:`. See `THOUGHTS.md` for the full routing table design.

| Task type | Default tier |
|-----------|-------------|
| `classify`, `wiki_read` | local (Ollama) |
| `wiki_write`, `synthesis`, `report` | gemini |
| `judgment` | claude |
| `embed` | nomic-embed-text on Ollama — never cloud |
| `transcribe` | Whisper LXC — never cloud |

## Design Doc

`docs/hermes-design-doc-v1.0.md` — full ReAct loop architecture, context system, skills
framework, LLM tier routing, Phase 1–5 build plan.

## Notes

- Each context (personal/professional) has its own allowed paths, whitelisted commands,
  LLM preferences, and email credentials — switching context changes all of these at once
- Long-term state lives in the Mnemosyne wiki (git repo of markdown), not Postgres
- Audit log at `logs/audit.jsonl` — every tool call and LLM invocation is recorded
- `HERMES_API_TOKEN` env var must be set before starting `bin/hermes-api` — Ansible Vault
  injects it on the LXC; for local dev, export it manually
- Phase 1 (CLI) is complete. Phase 2 HTTP endpoint is complete — see `ToDo.md`
- Do NOT build Phase 4 (web UI) features ahead of schedule
