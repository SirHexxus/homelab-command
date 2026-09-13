# Hermes

Local AI agent for homelab automation and personal productivity. Receives tasks
via CLI (Phase 1), Telegram (Phase 3), or web UI (Phase 4). Executes shell
commands, manages files, browses the web, handles email, and interfaces with
Mnemosyne for long-term knowledge storage.

**Part of the Homelab Command ecosystem** — alongside Argus, Ariadne, Orpheus,
and Mnemosyne.

---

## Quick Start

```bash
# 1. Clone and enter the project
cd ~/projects/homelab-command/apps/hermes

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Copy and edit config
cp config/config.example.yml config/config.yml
cp config/contexts/personal.example.yml config/contexts/personal.yml
cp config/contexts/professional.example.yml config/contexts/professional.yml

# 4. Edit config files with your paths, commands, and credentials

# 5. Run
bin/hermes "list files in ~/personal/downloads"
```

---

## Usage

```bash
# One-shot task (uses default_context from config.yml)
bin/hermes "list files in ~/personal/downloads"

# Specify context
bin/hermes --context professional "summarise open projects"

# Dry-run (describe actions without executing)
bin/hermes --context professional --dry-run "move all PDFs to archive"

# Interactive REPL
bin/hermes --interactive
bin/hermes --context personal -i

# Usage summary (per-model call counts for today)
bin/hermes --usage
```

---

## Configuration

### Global: `config/config.yml`

- `default_context` — context used when `--context` is not specified
- `ollama_base_url` — Ollama server address

### Contexts: `config/contexts/<name>.yml`

| Field | Description |
|-------|-------------|
| `display_name` | Human-readable context name |
| `tone` | `casual` or `professional` |
| `allowed_paths` | Filesystem paths Hermes may read/write |
| `allowed_commands` | Shell commands Hermes may execute |
| `style_guides` | Paths to style/brand guide files injected into every prompt |
| `model.ollama_model` | Ollama model to use |
| `model.force_tier` | Force LLM tier (1=Ollama, 2=Gemini, 3=Claude) |
| `email` | PurelyMail IMAP/SMTP credentials |

### Style and Brand Guides

Hermes injects your style/brand guides directly into every system prompt,
ensuring responses follow your tone and formatting rules. Add guide paths to
`style_guides` in your context YAML:

```yaml
style_guides:
  - ~/notes/brand/sirhexxus-style-guide.md
  - ~/notes/brand/writing-tone.md
```

The full content of each file is prepended to every task with the instruction
to follow those guidelines. Keep guides focused — very long guides consume
context window space.

---

## Mnemosyne Integration

Any information that needs to be persisted long-term (notes, tasks, references,
project updates) is saved to Mnemosyne via `lib/skills/mneme.py`.

**Requires**: Mnemosyne Postgres (`mnemosyne` DB at 10.0.50.14 with
pgvector) to be running. See `mnemosyne-design-doc.md`.

Configure in `config/config.yml`:
```yaml
mnemosyne:
  postgres_host: 10.0.50.14
  postgres_port: 5432
  postgres_db: mnemosyne
  postgres_user: hermes
  postgres_password: ""   # use Ansible Vault in production
```

---

## Project Structure

```
hermes/
├── bin/hermes                  # CLI entry point
├── lib/
│   ├── core/
│   │   ├── agent_loop.py       # ReAct loop
│   │   ├── audit.py            # JSONL audit log
│   │   ├── context.py          # Context dataclass + config loading
│   │   ├── llm.py              # LLM clients + router
│   │   └── skill_registry.py   # Skill registration
│   ├── skills/
│   │   ├── filesystem.py       # Scoped file operations
│   │   ├── shell.py            # Whitelisted shell execution
│   │   ├── email.py            # PurelyMail IMAP/SMTP (Phase 2)
│   │   ├── web.py              # fetch_url, web_search (Phase 2)
│   │   ├── mneme.py            # Long-term memory (Phase 2)
│   │   └── n8n_mcp.py          # n8n MCP client (Phase 5)
│   └── interfaces/
│       ├── cli.py              # (future: rich interactive UI)
│       ├── telegram_bot.py     # Telegram bots (Phase 3)
│       └── web_app.py          # FastAPI web UI (Phase 4)
├── config/
│   ├── config.example.yml
│   └── contexts/
│       ├── personal.example.yml
│       └── professional.example.yml
├── tests/
├── logs/                       # audit.jsonl (gitignored)
└── requirements.txt
```

---

## Build Phases

| Phase | Status | Contents |
|-------|--------|----------|
| 1 | ✅ Done | CLI + Ollama + filesystem + shell |
| 2 | Planned | LLM router (Gemini + Claude) + web + email + Mnemosyne |
| 3 | Planned | Telegram bots (requires @BotFather setup — see below) |
| 4 | Planned | FastAPI web UI |
| 5 | Blocked | n8n MCP integration (blocked on n8n NAS→Proxmox migration) |

### Phase 3 Pre-requisite: Register Telegram Bots

Before implementing Phase 3, register two bots via [@BotFather](https://t.me/BotFather):

1. `/newbot` → name: `Hermes Personal` → username: `sirhexxus_hermes_bot`
2. `/newbot` → name: `Hermes Professional` → username: `hexxusweb_hermes_bot`

Save the tokens to `config/contexts/personal.yml` and `config/contexts/professional.yml`
under `telegram_token`.

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
pytest tests/ -v --cov=lib
```

---

## Audit Log

Every tool call and LLM invocation is appended to `logs/audit.jsonl`.
View today's summary:

```bash
bin/hermes --usage
```

Raw log:
```bash
tail -f logs/audit.jsonl | python3 -c "import sys,json; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin]"
```
