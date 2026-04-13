# Hermes — Agent Task List

Maintained by Claude Code (Project Manager role). Updated each session.
Source of truth: `Mnemosyne-Hand-Off.md` (requirements), `THOUGHTS.md` (design rationale).

---

## Blocking — Do These First

### 1. Archive `lib/skills/mneme.py`
**Status:** DONE (2026-04-10)  
**Risk:** ACTIVE — `save_note`, `search_memory`, and `ask_memory` are registered in the
skill registry right now. If the agent loop tries to call any of them, it gets a
psycopg2 import error or connection refused. This poisons the tool list immediately.

Steps:
- Create `lib/skills/_archive/` directory
- Move `mneme.py` → `lib/skills/_archive/mneme_postgres.py`
- Remove the import from wherever skills are loaded at startup (check `bin/hermes` and `agent_loop.py`)
- Verify `list_skills()` no longer shows `save_note`, `search_memory`, `ask_memory`

---

### 2. Resolve Terraform Provider Version Conflict
**Status:** DONE (2026-04-10) — pinned to 0.96.0, terraform init run, lock file regenerated  
**Risk:** Cannot deploy the LXC until resolved — `terraform apply` would use 0.98.1 against
a repo convention requiring 0.96.0.

Steps:
- `infrastructure/hermes/terraform/` — edit `required_providers` block to pin `bpg/proxmox = "0.96.0"`
- Delete `.terraform/` and re-run `terraform init`
- Confirm lock file shows 0.96.0

---

## Phase 2 — Core Platform (Mnemosyne Unblocked After These)

### 3. Wire Gemini + Claude into `LLMRouter`
**Status:** DONE (2026-04-10) — GeminiClient, ClaudeClient (subprocess), task_type routing  
**Spec:** `Mnemosyne-Hand-Off.md` §1  
**Design notes:** `THOUGHTS.md` — "LLM Router Needs Per-Task Routing"

Steps:
- Implement `GeminiClient.complete(prompt, system)` in `lib/core/llm.py`
- Implement `ClaudeClient.complete(prompt, system)` in `lib/core/llm.py`
- Add `task_type: str = "default"` parameter to `LLMRouter.complete()`
- Add `model_routing` section to `config/config.example.yml` (see THOUGHTS.md for shape)
- Router reads task_type → resolves tier from config → executes waterfall: local → gemini → claude
- Update `config/contexts/personal.example.yml` default model from `llama3.2` to `qwen3` (or parameterized)

---

### 4. Implement `lib/skills/wiki.py`
**Status:** DONE (2026-04-10) — 7 skills registered, filelock on git_commit_push  
**Spec:** `Mnemosyne-Hand-Off.md` §2  
**Blocks:** HTTP endpoint (item 5), all Mnemosyne live testing

Minimum viable skill set (register all with `@register_skill`):
- `read_wiki_page(path, context)` → str
- `write_wiki_page(path, content, context)` → str
- `read_wiki_index(context)` → str
- `append_wiki_log(entry, context)` → str
- `list_wiki_pages(bucket, context)` → str
- `git_commit_push(message, context)` → str  ← must acquire file lock first
- `scan_wiki_inbox(context)` → str

Config: wiki repo path + git remote pulled from `config/config.yml` under `mnemosyne:` section.
File lock: `wiki/.git/mnemosyne.lock` (use `fcntl.flock` or `filelock` library).

---

### 5. Minimal HTTP Endpoint (`/task` + `/health`)
**Status:** DONE (2026-04-11)  
**Spec:** `Mnemosyne-Hand-Off.md` §3  
**Design notes:** `THOUGHTS.md` — "HTTP Endpoint Should Be Minimal and Internal"
**Depends on:** Item 4 (wiki.py must exist to have something to route to)

This is NOT the Phase 4 web UI. It is a service-to-service channel for n8n.

- Add FastAPI (or Flask) in `lib/interfaces/api.py`
- `GET /health` → `{"status": "ok"}`
- `POST /task` → accepts `{workflow, task, payload, context_name}` → returns `{status, message, data}`
- Bearer token auth — token from env var (Ansible Vault will inject it)
- Wire into a startup entrypoint (separate from the CLI `bin/hermes`)

---

### 6. Deploy LXC (VMID 110, 10.0.50.17)
**Status:** Blocked on item 2 (provider version conflict)  
**Spec:** `Mnemosyne-Hand-Off.md` §4

After item 2 is resolved:
- `terraform apply` in `infrastructure/hermes/terraform/`
- `ansible-playbook provision.yml` in `infrastructure/hermes/ansible/`
- Verify: `curl http://10.0.50.17:8765/health` returns 200
- Verify: wiki repo cloned on LXC and accessible to service user

---

## Phase 2 — Medium Priority

### 7. `IngestItem` Dataclass
**Status:** DONE (2026-04-11)  
**Spec:** `Mnemosyne-Hand-Off.md` §7

Create `lib/core/ingest.py` with the `IngestItem` dataclass. Fields:
`raw_content_type`, `text`, `file_ref`, `source`, `metadata`, `bucket_hint`.
All ingestion skill functions should accept/produce `IngestItem`.

---

### 8. Telegram Bot (Personal Context)
**Status:** Not started  
**Spec:** `Mnemosyne-Hand-Off.md` §6
**Depends on:** Items 4, 5, 6 (wiki skill, HTTP endpoint, LXC live)

- Register `sirhexxus_hermes_bot` via @BotFather
- Implement `lib/interfaces/telegram_bot.py` for personal context only
- Handle: text, voice (→ Whisper → ingest), file attachments, slash commands
- Professional bot is out of scope for this phase

---

## Cleanup

### 9. Update `CLAUDE.md` (this directory)
**Status:** DONE (2026-04-11)  
After items 3–5 are delivered, update:
- Runtime dependencies table (remove Postgres/Mnemosyne, add wiki repo path)
- Interface phase table (HTTP endpoint is now Phase 2, not Phase 4)
- Notes section (remove Postgres state reference)
- App structure tree (add `wiki.py`, `_archive/`, `interfaces/api.py`)

### 10. Update `config/config.example.yml`
**Status:** Not started  
- Remove Postgres mnemosyne block (commented out but misleading)
- Add `mnemosyne: wiki_path:` and `wiki_remote:` config keys
- Add `model_routing:` block (see THOUGHTS.md for shape)
- Add `gemini_api_key:` and `claude_api_key:` (uncommented placeholders)
- Remove complexity-score routing section (replaced by task_type routing)

---

## Delivery Order (Parallelism Notes)

```
NOW:    Items 1 + 2  (unblock the registry and IaC — independent, do both)
NEXT:   Items 3 + 4  (LLM router and wiki.py — independent, do in parallel)
THEN:   Item 5       (HTTP endpoint — needs wiki.py to exist)
THEN:   Item 6       (LXC deploy — needs item 2 resolved first)
LATER:  Items 7, 8   (IngestItem and Telegram — needs items 4, 5, 6)
ANYTIME: Items 9, 10 (cleanup — update docs as code lands)
```
