# Hermes: Required Capabilities — Mnemosyne Handoff Spec

**From:** Mnemosyne Project  
**To:** Hermes Project  
**Date:** 2026-04-10  
**Status:** Awaiting Hermes delivery before Mnemosyne implementation can proceed

---

## Context

This document defines the capabilities that the Mnemosyne project requires from the Hermes
platform. It is an external requirements spec, not an implementation guide — the Hermes team
owns all implementation decisions. Items are written as requirements: what is needed, why it
is needed, and what "done" looks like from Mnemosyne's perspective.

### What Mnemosyne is building

Mnemosyne is a personal knowledge management system stored as a git repository of markdown
files — a persistent, compounding wiki. Hermes is the intelligent agent that reads and writes
that wiki. There is no database backend for Mnemosyne. The wiki files are the primary store.

Hermes's role in Mnemosyne is not "run shell commands" or "query Postgres." It is: **receive
a raw input, read the relevant wiki pages, integrate the new knowledge, write the updated
pages, and commit the result.** Every Mnemosyne workflow — ingest, retrieval, scheduled
reports, maintenance — runs through Hermes.

### What this doc does not cover

This spec covers Mnemosyne's requirements only. Hermes is an agentic platform that will serve
multiple workflows (email organization, social media scheduling, and others). The Hermes team
should design the platform for that broader scope. Mnemosyne's requirements here represent
the first tenant, not the full vision.

---

## Deliverables

### 1. Capable LLM Router — Gemini + Claude wired up

**Priority:** HIGHEST — blocks all Mnemosyne wiki work  
**Current state:** `LLMRouter` routes to Ollama only. If Ollama fails, it raises immediately.
Gemini and Claude are `# Phase 2` comments with no implementation.

**Why Mnemosyne needs this:**  
Wiki page writing requires a model that can read 5–10 existing markdown pages and produce
coherent output with `[[wikilinks]]`, consistent frontmatter, and cross-references to related
entities. Local models at the 7B–8B range (Mistral, Llama 3.2) cannot do this reliably at the
quality level required. Gemini Flash is the primary workhorse for wiki writes. Claude Sonnet
handles synthesis and judgment tasks. Without these, wiki content will be inconsistent and
degrade quickly.

**What "done" looks like for Mnemosyne:**
- `GeminiClient` implemented and wired into `LLMRouter`
- `ClaudeClient` implemented and wired into `LLMRouter`
- Waterfall fallback functional: Local → Gemini → Claude
- Per-task-type model routing supported via config (not just a single model per context)

**Per-task routing requirement:**  
Mnemosyne will pass a `task_type` hint to the router (e.g., `classify`, `wiki_write`,
`synthesis`, `judgment`). The router should resolve the appropriate model tier from a
configurable mapping. This allows cheap local models to handle classification while Gemini
handles wiki integration. The config structure is the Hermes team's decision; the interface
requirement is that `task_type` is respected.

**Note on local models:**  
The user is evaluating Qwen3 models on Ollama and may add a GPU. The routing config should
treat local model capability as a tunable parameter — hardcoding "local = low quality" into
the logic will require code changes as hardware improves. Config-driven thresholds, not
hardcoded ones.

---

### 2. Wiki Skill Module (`lib/skills/wiki.py`)

**Priority:** HIGHEST — blocks all Mnemosyne wiki work  
**Current state:** `lib/skills/mneme.py` exists but is built for Postgres/pgvector. It will
fail at runtime (psycopg2 not installed, Mnemosyne Postgres does not exist). It is dead code
for the new architecture and should be archived or removed (see Deliverable 5).

**Why Mnemosyne needs this:**  
The wiki skill is how Hermes physically interacts with the Mnemosyne wiki — reading pages,
writing updates, managing the index and log, and persisting changes to git. Without it,
Hermes has no way to read or write the knowledge base.

**Required skill functions (minimum viable set):**

| Skill | Description |
|-------|-------------|
| `read_wiki_page(path)` | Read a single page by relative path from wiki root |
| `write_wiki_page(path, content)` | Write or overwrite a wiki page |
| `read_wiki_index()` | Read `index.md` in full |
| `append_wiki_log(entry)` | Append a formatted entry to `log.md` |
| `list_wiki_pages(bucket)` | List all pages in a given bucket directory |
| `git_commit_push(message)` | Stage all changes, commit, push to remote |
| `scan_wiki_inbox()` | List files in `wiki/inbox/` staging folder |

**Configuration:**  
Wiki repo path and git remote URL must be configurable via `config/config.yml` under a
`mnemosyne` section. These must not be hardcoded. The Hermes LXC needs filesystem access to
the wiki repo (either a local clone or a mounted path).

**Concurrency requirement:**  
`git_commit_push` must acquire a file lock before committing to prevent race conditions when
multiple ingest operations arrive in quick succession. A lockfile at `wiki/.git/mnemosyne.lock`
or equivalent is sufficient. This is a personal-scale system; sophisticated queuing is not
required, but a basic lock is necessary for correctness.

---

### 3. HTTP Endpoint for n8n Integration

**Priority:** HIGH — blocks all automated ingestion and reporting flows  
**Current state:** Hermes is CLI-only. `lib/interfaces/` is an empty `__init__.py`. The
current plan places FastAPI in Phase 4, which is too late for Mnemosyne.

**Why Mnemosyne needs this:**  
n8n orchestrates all automated Mnemosyne workflows — Telegram ingestion triggers, cron-based
report generation, scheduled maintenance. n8n cannot invoke a CLI tool. It needs an HTTP
endpoint. Without this, n8n and Hermes cannot communicate, and the entire automated pipeline
is broken regardless of how well the skills are implemented.

**What "done" looks like for Mnemosyne:**

- `POST /task` — accepts `{workflow, task, payload, context_name}`; routes to the appropriate
  skill set based on `workflow`. For Mnemosyne, `workflow: "mnemosyne"` is the key.
  Response: `{status, message, data}` — synchronous for short tasks.
- `GET /health` — returns `{"status": "ok"}`. Used by Ansible verify step and Uptime Kuma.
- Bearer token auth — token stored in Ansible Vault. Internal VLAN 50 use only.

**Scope clarification:**  
This is NOT the Phase 4 FastAPI web UI. It is a minimal internal API for service-to-service
communication. Do not add user-facing features, authentication flows, or session management
to this endpoint. That work belongs in Phase 4 and is out of scope here.

---

### 4. LXC Deployment (VMID 110, 10.0.50.17)

**Priority:** HIGH — blocks all live end-to-end testing  
**Current state:** IaC is written. LXC is not deployed. There is a Terraform provider version
conflict: `.terraform/` directory contains `bpg/proxmox 0.98.1`; repo convention requires
`0.96.0`. This must be reconciled before `terraform apply`.

**What "done" looks like for Mnemosyne:**
- Provider version conflict resolved
- `terraform apply` completes successfully; LXC exists at 10.0.50.17
- `ansible-playbook provision.yml` completes successfully
- `curl http://10.0.50.17:8765/health` returns `200 OK`
- Wiki repo is cloned on the LXC and accessible to the Hermes service user

---

### 5. Archive `lib/skills/mneme.py`

**Priority:** MEDIUM — not a runtime blocker but causes developer confusion  
**Current state:** `mneme.py` implements `save_note` and `search_memory` against a Postgres/
pgvector schema that Mnemosyne is no longer using. It is registered in the skill registry
and will appear in the agent's available tools. If the agent attempts to use it, it will fail
with a psycopg2 import error or a connection refused error.

**Required action:**  
Remove from the active skill registry. Archive at `lib/skills/_archive/mneme_postgres.py` or
delete. Update any imports and skill registry references. The wiki skill (Deliverable 2) will
provide replacement functionality under different names and a completely different storage model.

**Note:** Do not attempt to adapt `mneme.py` to the new architecture. It is a different
storage paradigm. Write `wiki.py` clean.

---

### 6. Telegram Bot Interface (Personal Context)

**Priority:** MEDIUM — blocks user-facing ingest and retrieval  
**Current state:** Phase 3 in the Hermes plan. `lib/interfaces/telegram_bot.py` not
implemented. Two bots are planned; only the personal bot is required for Mnemosyne Phase 1.

**Why Mnemosyne needs this:**  
Telegram is the primary capture and retrieval interface for Mnemosyne. The user sends notes,
voice memos, and files via Telegram. The bot responds with confirmations, query answers, and
scheduled reports. Without the Telegram bot, the only way to interact with Mnemosyne is via
CLI or n8n Chat Trigger.

**What "done" looks like for Mnemosyne:**
- `sirhexxus_hermes_bot` registered via @BotFather
- `lib/interfaces/telegram_bot.py` implemented for the personal context
- Bot handles: text messages, voice memos (routes to Whisper then ingest), file attachments,
  slash commands (`/ask`, `/search`, `/find`, `/project`, `/pursuit`, `/remind`, `/lint`)
- Outgoing: text messages, formatted Telegram messages for reports

**Out of scope for Mnemosyne:**  
The professional bot (`hexxusweb_hermes_bot`) is a separate Hermes workflow. Do not block
this deliverable on professional context work.

---

### 7. IngestItem Abstraction

**Priority:** MEDIUM — required for multi-source ingestion extensibility  
**Current state:** Not implemented. No normalized ingestion envelope exists.

**Why Mnemosyne needs this:**  
Mnemosyne will receive input from multiple sources: Telegram text, Telegram voice, Telegram
file attachments, email (forwarding address or Gmail label), web clipper inbox folder, and
n8n Chat Trigger. The wiki integration pipeline must be source-agnostic from the point of
"raw content + metadata" onward. Without a normalized envelope, each new source requires
changes to the core pipeline logic.

**Required:**  
A dataclass (or equivalent) in `lib/core/` representing a normalized ingestion item:

```
IngestItem:
  raw_content_type: str   # "text" | "file" | "url" | "email"
  text:             str | None    # extracted text content
  file_ref:         str | None    # MinIO path for binary content
  source:           str   # "telegram" | "email" | "web_clipper" | "n8n_chat" | "api"
  metadata:         dict  # source-specific fields (filename, url, sender, subject, etc.)
  bucket_hint:      str | None    # optional pre-classification hint from the source
```

All ingestion skill functions should accept and produce `IngestItem`. The Hermes team may
adjust field names and structure as long as the semantics are preserved.

---

## Delivery Priority Summary

| # | Deliverable | Priority | Mnemosyne Impact if Missing |
|---|---|---|---|
| 1 | LLM Router (Gemini + Claude) | HIGHEST | Wiki writes produce low-quality, inconsistent output |
| 2 | Wiki skill (`wiki.py`) | HIGHEST | Hermes cannot read or write the wiki at all |
| 3 | HTTP endpoint (`/task`, `/health`) | HIGH | n8n cannot trigger any automated flow |
| 4 | LXC deployment | HIGH | No live environment for any testing |
| 5 | Archive `mneme.py` | MEDIUM | Developer confusion; agent may attempt broken skill calls |
| 6 | Telegram bot (personal) | MEDIUM | No user-facing capture or retrieval |
| 7 | IngestItem abstraction | MEDIUM | Multi-source ingestion requires pipeline rewrites later |

**Parallelism notes:**
- Deliverables 1, 2, and 4 can proceed in parallel
- Deliverable 3 is meaningful only after Deliverable 2 exists
- Deliverable 5 should be done alongside Deliverable 2 (same session)
- Deliverables 6 and 7 can begin after the LXC is deployed and the HTTP endpoint is live

---

## What Mnemosyne Will Provide to Hermes

In parallel with Hermes development, the Mnemosyne team will produce:

- **`SCHEMA.md`** — the wiki governance document. This is the file Hermes reads at the start
  of every wiki operation to understand page formats, frontmatter conventions, [[wikilink]]
  syntax requirements, bucket directory structure, and `index.md` entry format. Hermes cannot
  write a well-structured wiki without this document.
- **Wiki repo initial structure** — empty directories, blank `index.md`, blank `log.md`,
  and a `wiki/inbox/` staging folder. Hermes should be able to `git clone` this repo and
  find a valid, parseable structure from day one.
- **n8n workflow designs** — the ingest, query, and reporting workflows will be drafted by
  the Mnemosyne team and implemented in n8n once the Hermes HTTP endpoint is live.

---

*Questions or scope clarifications: raise with the Mnemosyne PM before implementation begins.*
