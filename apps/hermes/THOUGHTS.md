# Hermes: Design Thinking & Open Questions

This file captures architectural thinking, design decisions, open questions, and context
that emerged during planning — things that should inform Hermes development but aren't task
items. It is a living document, not a spec.

---

## Hermes Is a Platform, Not a Feature

The most important framing: Hermes is not the "Mnemosyne service" or the "email bot." It is
an **agentic orchestration platform** that hosts multiple semi-autonomous workflows. Current
planned workflows:

- **Mnemosyne wiki maintenance** — reads/writes the knowledge base wiki
- **Email management** — scans inbox, organizes, drafts responses, routes to Mnemosyne
- **Social media scheduling** — reads from a content table, makes scheduled posts
- Others TBD

Each workflow is a skill domain. The ReAct loop, LLM router, context system, and audit log
are the platform layer — they don't care which skills are loaded. The existing Phase 1
architecture (skill registry, context YAML, agent loop) is the right foundation. The mistake
to avoid is treating any single workflow as Hermes's "purpose." Hermes's purpose is to be
a capable, trustworthy local AI agent. The workflows are tenants.

---

## Hermes as Autonomous-Execution Subsystem (Layers 1–4)

*Added 2026-05-20 — clarification of Hermes's scope within the Five-Layer AI Stack.*

Complementary framing to "Hermes Is a Platform, Not a Feature": Hermes is the homelab's
**autonomous-execution subsystem** — the container for all automation functions that
should run without human (Layer 5) initiation. It encapsulates Layers 1–4 of the
Five-Layer AI Stack for any task given over to autonomous execution:

- **Layer 4** — Gemini for reasoning and synthesis; n8n for orchestration and workflow routing
- **Layer 3** — Whisper, nomic-embed-text, and other specialized models when invoked from autonomous flows
- **Layer 2** — scripts and workflow steps that execute as part of autonomous runs (deterministic logic, API calls, file operations)
- **Layer 1** — configuration, prompts, and documentation used exclusively by autonomous flows

Hermes does not own every component in the stack. Mnemosyne requests report generation
from Hermes; specialized models may be invoked from other paths too (e.g., a CLI tool that
calls Whisper directly). But Hermes is the subsystem that owns most of the autonomous-
execution surface, and design decisions about Hermes should privilege that role.

**Design target:** OpenClaw-style autonomy. Given a task, Hermes executes mostly
independently. The human's role is goal-setting and audit, not step-by-step direction.
See `[[AI Agents Are the Wrong Abstraction Layer]]` ("The OpenClaw Option" section) for
the architectural framing.

**Why this framing matters for design decisions:**
- Tools that exist *only* for autonomous use (e.g., scheduled prompt templates, n8n cron
  triggers, audit-log queryers) belong inside Hermes's scope.
- Tools used by both human and autonomous paths (e.g., the wiki itself, Whisper LXC, MinIO)
  live outside Hermes; Hermes invokes them but does not own them.
- When in doubt about whether something belongs in Hermes: ask "is this initiated without
  a human?" If yes, it's in scope. If a human pulls the trigger, it's likely outside.

---

## The Skill System Is Right — Keep It

The `@register_skill()` decorator pattern in `skill_registry.py` is a clean extensibility
model. New workflow domains = new skill modules. The agent loop doesn't need to know what
skills exist — it discovers them at runtime. This should be preserved and extended, not
replaced.

What needs to change: skill modules should be organized by domain, not listed flat.
Suggested structure:

```
lib/skills/
  _archive/          ← deprecated skills (mneme_postgres.py goes here)
  core/              ← cross-domain utilities (http_client, file_lock, etc.)
  wiki/              ← Mnemosyne wiki skills
  email/             ← email read/write/organize
  social/            ← social media posting
  web/               ← URL fetch, web search
  filesystem.py      ← existing (keep)
  shell.py           ← existing (keep)
```

---

## The LLM Router Needs Per-Task Routing, Not Just Per-Context

The current design has a single `ollama_model` per context and a complexity score waterfall
(0–10 scale) that escalates tiers. This is too coarse for a multi-workflow platform.

Different workflows have very different model quality requirements:

- **Bucket classification** — fast, cheap, Mistral/Qwen3-8B is fine
- **Wiki page integration** — reads 5-10 pages, writes structured markdown, needs Gemini Flash minimum
- **Entity lookup / formatting** — mostly reading + formatting, local model often fine
- **Synthesis tasks** (Serendipity Engine, Idea Synthesis) — needs Gemini Flash or Claude
- **Conflict resolution / judgment** — Claude directly, no escalation path
- **Embedding generation** — nomic-embed-text on Ollama exclusively (see model fleet section)
- **Voice transcription** — Whisper LXC exclusively (see model fleet section)

The router needs a `task_type` parameter and a config-driven mapping from task types to
model tiers. This lets the routing table be tuned without code changes as hardware and
available models improve.

Suggested config shape (in `config/config.yml`):

```yaml
model_routing:
  classify:     local
  wiki_write:   gemini
  wiki_read:    local
  synthesis:    gemini
  judgment:     claude
  report:       gemini
  embed:        nomic          # always local, always nomic-embed-text
  transcribe:   whisper        # always Whisper LXC, never routed elsewhere
```

The tier names (`local`, `gemini`, `claude`, `nomic`, `whisper`) map to the appropriate
client. `nomic` and `whisper` are fixed-destination tiers — they never escalate because
there is no cloud equivalent in the stack. Each context YAML can override specific task
types if needed.

---

## LLM Defaults After Hold Lift (2026-05-20)

The hold lift on 2026-05-20 (see `[[2026-05-20 — Hermes Off Hold and Orient Inventory]]`)
established concrete LLM defaults that the abstract tier mapping above must be reconciled
against. The tier names stay; the model pins are new.

**Primary default:** `gemini-3.5-flash` (pinned, not `-latest`). Quality-validated against
the real Mnemosyne Daily Digest prompt — caught more calendar overlaps than Sonnet, made a
synthesis connection neither Sonnet nor 2.5 Pro produced, held the secretary voice the
prompt asks for. Cost ~$0.0072/run; ~$0.22/month at 30 daily runs.

**Selective escalation candidate (deferred):** `gemini-3.1-pro-preview` for Idea Synthesis
only. ~5× the cost per run due to mandatory thinking budget, and preview status makes it
unsafe for production cron jobs without a deprecation watch. Wait until Idea Synthesis is
actually built and producing real reports before committing.

**Re-evaluation point:** Gemini 3.5 Pro GA (~June 2026). If quality is competitive and
pricing reasonable, may become the default and retire the Flash/Pro split entirely.

**Safety rail:** $5/month hard cap on the Gemini API on James's personal billing account.
DigitalOcean droplet was shut down concurrently to free ~$12/month.

**Credentials pattern:** `gemini-creds.json` (0600, JSON pointer file). Siblings:
`weather-creds.json`, `telegram-creds.json`. Replaces the env-var-only pattern from the
original Phase 2 GeminiClient. The `model` field supports a single default today;
per-report routing will need a `model_overrides` map in the same file when escalation
to Pro for Idea Synthesis becomes real.

**Token-overhead finding (worth remembering):** The current `claude -p` path for Daily
Digest costs ~31,000 input tokens per run because Claude Code wraps the 2k digest prompt
in ~29k of framework overhead. That overhead vanishes entirely on a direct API call. Any
report-style use case currently routed through `claude -p` is paying this overhead tax.

---

## Local Model Fleet Strategy

Hermes operates a fleet of local models, not a single "local tier." Each model has a
distinct role, and the routing layer should treat them as separate, specialized tools rather
than interchangeable fallbacks.

### The full local model fleet

| Model | Host | Role | Routable? |
|-------|------|------|-----------|
| Qwen3-8B (or equivalent) | Ollama (10.0.50.10) | General reasoning, classification, wiki reads, entity formatting | Yes — default local tier |
| Qwen3-14B (future, GPU) | Ollama (10.0.50.10) | Heavier local tasks: multi-page wiki writes, structured output | Yes — elevated local tier |
| nomic-embed-text | Ollama (10.0.50.10) | Embedding generation — 768-dim vectors | Fixed — never cloud |
| Whisper | LXC 102 (10.0.50.12) | Voice/audio transcription | Fixed — never cloud |

**Why nomic-embed-text is fixed:**  
Embeddings must be generated by the same model consistently. If you generate embeddings with
nomic locally and later switch to a cloud embedding model, existing embeddings become
incompatible. Nomic is the embedding model for this stack; all embedding calls go there.
There is no cloud fallback for embeddings.

**Why Whisper is fixed:**  
Whisper is a transcription service, not a reasoning model. It has no cloud equivalent in
this stack (the goal is local-first, and sending audio to a cloud API would be a privacy
regression). All audio transcription calls go to the Whisper LXC at 10.0.50.12. There is
no escalation path.

### Hermes must know about Whisper

Whisper is not just an n8n preprocessing step — Hermes should be able to call Whisper
directly from a skill. This matters for:
- Voice memo ingestion triggered via CLI or the HTTP endpoint (not just Telegram → n8n)
- Any future workflow that produces audio (meeting transcripts, etc.)

The Whisper skill should be a thin wrapper: `transcribe_audio(file_path_or_minio_ref) → str`.
It POSTs to the Whisper LXC's HTTP endpoint and returns the transcription text.

### Qwen3 vs Mistral 7B / Llama 3.2

The current `config/contexts/personal.example.yml` defaults to `llama3.2`. This should be
updated to Qwen3-8B (or whichever model proves best in ongoing benchmarking) once the
evaluation is complete. Qwen3-8B outperforms both Mistral 7B and Llama 3.2 on
instruction-following and structured output tasks — both of which matter for wiki writes.

Benchmark results from prior testing are in `test-results/` (untracked). Review before
committing to a default model name.

### GPU impact on the routing table

When GPU hardware arrives and Qwen3-14B (or larger) becomes viable:
- Elevate the local tier threshold in the routing config — more tasks stay local
- Consider a two-level local tier: `local_fast` (8B, CPU) and `local_capable` (14B, GPU)
- The config-driven routing table means this is a YAML edit, not a code change

Do not block Phase 2 on GPU acquisition. Ship with Gemini + Claude for wiki writes and
tune local upward as hardware arrives.

---

## The `mneme.py` Skill Is Dead Weight

**RESOLVED 2026-04-10** — archived to `lib/skills/_archive/mneme_postgres.py`;
deregistered. Body preserved as historical record of the pivot.

`lib/skills/mneme.py` was written for a Postgres/pgvector architecture that Mnemosyne has
pivoted away from. It:
- Tries to `import psycopg2` (not installed)
- Calls `_get_embedding()` via Ollama's embedding endpoint (nomic-embed-text)
- Does `INSERT INTO resources` with pgvector casts
- Will fail at runtime if the agent tries to use `save_note` or `search_memory`

It is registered in the skill registry and will appear in the agent's tool list, potentially
causing the agent to attempt it and fail confusingly. Archive it to `lib/skills/_archive/`
before deploying. The wiki skill (`wiki.py`) will provide replacement functionality with a
completely different interface.

Do not adapt `mneme.py`. It is a different storage paradigm. Write `wiki.py` clean.

---

## The HTTP Endpoint Should Be Minimal and Internal

The FastAPI web UI in Phase 4 is a user-facing interface. The HTTP endpoint that n8n needs
is NOT that — it is a service-to-service communication channel on VLAN 50. It should be:

- Simple: two or three routes, not a full REST API
- Internal: Bearer token auth, no public exposure, VLAN 50 only
- Lightweight: FastAPI is fine but even Flask or a bare httpx server would work

Do not let Phase 4 scope-creep into this endpoint. The risk is building a full web app
when all n8n needs is `POST /task` returning a JSON confirmation. Ship the minimal endpoint
early; build the web UI when it's actually needed.

The endpoint design should route by `workflow` field:
```json
{
  "workflow": "mnemosyne",
  "task": "ingest",
  "payload": { ... IngestItem ... },
  "context_name": "personal"
}
```
Hermes receives this, loads the `personal` context, runs the agent loop with the
`mnemosyne` skill domain active, returns `{status, message, data}`.

---

## The Context System Should Stay Lean

The `Context` dataclass is a solid design. A few things to keep in mind as it evolves:

- **`allowed_paths` and `allowed_commands`** are security constraints on the filesystem and
  shell skills. As Hermes takes on more workflows, resist the temptation to widen these
  broadly. Keep the allowlist tight per context.

- **`style_guides`** are injected into every system prompt. For wiki maintenance tasks, the
  wiki `SCHEMA.md` should be injected here (or loaded as part of the wiki skill initialization),
  not manually added to every prompt. The wiki skill should handle loading the schema.

- **Multi-context expansion**: the personal/professional split was designed for output tone
  and email credentials. As Hermes grows, there may be a desire to add more contexts (e.g.,
  a dedicated "mnemosyne" context). Resist this unless there's a real use case — two contexts
  is probably the right ceiling, and workflow routing (via `workflow` field in tasks) is a
  better mechanism than context proliferation.

---

## The Agent Loop Has One Known Limitation

`agent_loop.py` uses a custom `tool_call` JSON fencing format:

```
```tool_call
{"tool": "skill_name", "args": {"key": "value"}}
```
```

This works, but it's a custom format that every LLM (Ollama, Gemini, Claude) must be
prompted to use. Claude and Gemini generally follow this well when explicitly instructed.
However, as Hermes moves to using Claude and Gemini as primary models for wiki tasks, it's
worth evaluating whether to migrate to native tool-calling APIs (Claude's `tools` parameter,
Gemini's function calling). Native tool calling is more reliable than regex-parsed JSON fences.

This is not urgent — the current format works — but it's a known technical debt item to
evaluate before the agent is handling high-stakes wiki writes at scale.

---

## The Ingestion Interface Should Be Designed for Extensibility

Mnemosyne needs a normalized ingestion envelope (`IngestItem`) so the core wiki integration
pipeline is source-agnostic. Planned sources include:

| Source | Notes |
|--------|-------|
| Telegram text | Primary — already in Phase 2 plan |
| Telegram voice | Whisper → text, MinIO for audio |
| Telegram file attachment | By MIME type: text/pdf/docx/audio/image/other |
| Email (IMAP forwarding address) | Dedicated `mneme@...` address on PurelyMail |
| Email (Gmail label) | `Mneme/Inbox` label trigger |
| Obsidian Web Clipper | Drops files into `wiki/inbox/` staging folder |
| n8n Chat Trigger | Web-based secondary interface |
| Future: iOS Shortcut | Device-side only; sends to Telegram bot |
| Future: browser extension | Calls n8n webhook directly |

The `wiki/inbox/` staging folder pattern is worth noting: any source that can write a file
to the wiki repo (or drop into an S3 prefix in MinIO) can participate in ingestion without
real-time integration. Hermes scans inbox periodically or on demand. This decouples source
integration from processing timing.

---

## Terraform Provider Version Conflict

**RESOLVED 2026-04-10** — pinned to `0.96.0`, `terraform init` re-run, lock file
regenerated, LXC deployed. The repo-wide convention has since shifted: root `CLAUDE.md`
now describes an ongoing migration from `0.96.0` to `0.98.1`, and Hermes is already on
the new version. Body preserved as historical record.

The `.terraform/` directory in `infrastructure/hermes/terraform/` contains provider
`bpg/proxmox 0.98.1`. The repo-wide convention (root `CLAUDE.md`) requires `0.96.0`.

This needs to be resolved before `terraform apply`. Options:
1. Repin to 0.96.0 and re-initialize — safest, consistent with repo convention
2. Update the repo convention to allow 0.98.1 — requires checking all other services

Do not run `terraform apply` with this conflict unresolved. The provider version affects
API calls to Proxmox and a version mismatch can cause state drift.

---

## The Audit Log Is a Good Foundation

`audit.py` appending JSONL to `logs/audit.jsonl` is a solid design. It captures every LLM
call and tool invocation. A few thoughts as usage grows:

- The audit log should be rotated or archived periodically — an unbounded JSONL file will
  eventually become unwieldy
- For Mnemosyne, the wiki's own `log.md` serves as the human-readable activity log;
  `audit.jsonl` serves as the machine-readable debugging log. These are complementary,
  not redundant.
- Argus (the SIEM service) may eventually want to ingest Hermes audit events. Design the
  log format with that future integration in mind — structured JSONL with consistent field
  names is already the right call.

---

## Phase 3 Architecture Direction — Single-Shot Dispatch Over ReAct

*Added 2026-04-27 — from replanning session*

The ReAct loop failure during Phase 2 testing (10-step safety limit hit, Ollama timeouts at 300s) is diagnostic: the multi-step agent loop is over-engineered for most Mnemosyne ingest tasks. Classifying a note, choosing a bucket, and writing a wiki page is a deterministic routing operation, not a reasoning problem.

**Recommended Phase 3 approach:**

Replace the ReAct loop with a single-shot classification prompt for simple tasks:
- One LLM call: "Classify this note, extract title and summary, return JSON"
- n8n workflow executes the actual wiki write, git commit, MinIO upload, etc.
- Hermes becomes a thin router dispatching to n8n workflows rather than running a reasoning loop

Reserve the ReAct loop for genuinely complex judgment tasks: synthesis, conflict resolution, Argus alert triage — cases where multi-step reasoning is actually needed.

This aligns with the file-tree agent architecture principle: the agent's job is instructions + tool dispatch; n8n is the tools layer that handles branching, retries, and integrations. Adding a new capability means building an n8n workflow, not editing Hermes Python.

**Practical implication for the routing table:**

The `classify` task type (already in the routing config as `local`) becomes a single-shot call returning structured JSON. The `wiki_write` task type may not need a full agent loop — n8n can handle the write once classification output is returned.

**Update 2026-05-20:** Single-shot dispatch is now an active candidate for the
`[[Decide First Mnemosyne and Hermes Build Sprint]]` gate (2026-06-01) — listed in
`ToDo.md` under "ReAct-loop scope reduction" in the Post-Hold-Lift Candidates section. The
direction is no longer indefinite future architecture; it is one of three to four
candidates competing for the first post-hold-lift build sprint.

---

*See `ToDo.md` for actionable task list. This document is context and thinking, not tasks.*
