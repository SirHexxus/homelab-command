# Mnemosyne Design Doc
**Version:** 1.2
**Last Updated:** April 2026
**Status:** Living Document - implementation will surface unknowns not captured here

> **Architecture Note (April 2026):** This document reflects the wiki model architecture.
> The original design (v1.0) used Postgres/pgvector as the primary store with Notion as the
> UI layer. That design was superseded - see Section 4 for the rationale and a full comparison.
> All Postgres schema references in prior versions are retired.

---

## 1. Purpose & Philosophy

See `docs/homelab-philosophy-v1.0.md` for the broader goals this service supports. Mnemosyne serves the skill-building and personal productivity goals - and directly addresses the ADHD executive function challenges called out in the philosophy doc's documentation section.

Mnemosyne is a personal knowledge management system designed to solve a specific problem: ADHD executive function failures cause valuable thoughts, information, and context to evaporate before they can be acted on. The system's job is to make capture frictionless, storage automatic, and retrieval intelligent.

**Design principles:**
- Capture must be faster than the thought can escape - minimum friction at point of entry
- Classification and organization happen after capture, never during
- Every ingest operation makes the wiki richer - connections compound over time
- Retrieval must be semantic, not just keyword-based - the system should find what you mean, not just what you typed
- The knowledge store must be human-readable without any tooling - it's just markdown files
- No information is ever deleted - only archived or superseded

---

## 2. System Overview

```
INGESTION LAYER
(Telegram, Email, Voice, Web, Bulk Import)
(Claude Code /mneme skill - direct path)
         |
         v
  PROCESSING LAYER
  (AI classify → bucket → write wiki page → update index.md + log.md)
         |
    _____|_______________________________________
    |           |              |                |
    v           v              v                v
 WIKI REPO   REDIS          MINIO           OBSIDIAN
~/mneme/wiki  Session/cache  Voice + files   Human UI
(git repo)    dedup          attachments     (reads wiki)
         |
         v
  RETRIEVAL LAYER
  (Telegram bot commands, Claude Code /mneme-ask, Scheduled reports)
```

**Two paths into the wiki:**
- **Automated path (Hermes + n8n):** Telegram → n8n webhook → Hermes classifies → wiki write
- **Direct path (Claude Code):** `/mneme` or `/mneme-ask` skill - Claude reads SCHEMA.md,
  navigates index.md, reads/writes pages directly. No Hermes dependency.

Both paths produce identical output - the wiki format defined in `SCHEMA.md` is the contract.

---

## 3. Bucket Definitions

Buckets fall into two structural categories that drive different ingestion and storage behavior.

**Atomic buckets:** each entry is independent. New entries are always new pages. No reconciliation needed.

**Compound buckets:** many entries may refer to the same real-world entity. New entries must be reconciled against the existing entity page before deciding whether to update or create.

| Bucket | Type | Directory | Purpose | Key Distinction |
|--------|------|-----------|---------|----------------|
| IDEA | Atomic | `ideas/` | Abstract thoughts, opinions, insights, interpretations, and questions - your take on the world | Your inner world; subjective |
| ADMIN | Atomic | `admin/` | Tasks and errands with due dates | Actionable, time-bound |
| REFERENCE | Atomic | `reference/` | Concrete facts, sources, data, information - verifiable and/or quantifiable | External, objective reality |
| JOURNAL | Atomic | `journal/` | Dated personal entries, reflections, daily notes | Time-anchored experience |
| PERSON | Compound | `people/` | Individuals - contact info, relationship context, interaction history | About *who* |
| PROJECT | Compound | `projects/` | Multi-step work with a defined end state | Has a finish line |
| PURSUIT | Compound | `pursuits/` | Ongoing endeavors without a terminal end state | No finish line |

**IDEA vs. REFERENCE disambiguation:** This is the highest-risk classification boundary. When
confidence is below threshold at this specific boundary, the classifier must ask rather than
guess. If the user declines to clarify, **default to IDEA** - a subjective framing of an
objective fact is a less disorienting misclassification than an objective fact filed as a
personal insight. See `SCHEMA.md` for worked examples.

---

## 4. Data Storage Architecture

### 4.1 Wiki Repo: Primary Knowledge Store

The primary store is a private git repository of markdown files at `~/mneme/wiki/`.

**Why the wiki model over Postgres/pgvector:**

| Dimension | Original Design (v1.0) | Wiki Model (v1.2) |
|-----------|----------------------|-------------------|
| Primary store | Postgres (pgvector) | Git repo of markdown files |
| Retrieval | Vector similarity search | index.md + LLM reads pages |
| Entity resolution | Confidence-scored n8n workflow | LLM reads entity page, updates it |
| UI | Notion (sync'd from Postgres) | Obsidian (reads git repo directly) |
| Ingest pipeline | ~15-node n8n workflow | Classify → write markdown → commit |
| Knowledge growth | Retrieval-time RAG | Ingest-time synthesis (compounding) |
| Human-readable | Only via Notion UI | Always - it's just markdown |

The wiki model optimizes for *compounding knowledge* - each new note makes the wiki richer,
not just bigger. For an ADHD capture system where the goal is to reduce friction and increase
discoverability, ingest-time synthesis is a better fit than retrieval-time reconstruction.

**Governance:** `~/mneme/wiki/SCHEMA.md` is the single source of truth for all write operations.
Any agent or tool that writes to the wiki must read SCHEMA.md first.

**Key files:**
- `wiki/SCHEMA.md` - governance, naming conventions, frontmatter schema, wikilink rules
- `wiki/index.md` - catalog of all pages, organized by bucket (one compact entry per page)
- `wiki/log.md` - append-only event log (ISO timestamp, operation, bucket, title, source)

**Symlink:** `infrastructure/mnemosyne/wiki → ~/mneme/wiki` - allows monorepo to reference
the schema location without tracking personal data.

### 4.2 Redis: Ephemeral and Session Storage

- Multi-turn Telegram conversation session state - key: `session:{chat_id}`, TTL: 600s (10 min)
- Clarification timeout tracking - when session key expires, automated path defaults to IDEA
- Deduplication - key: `dedup:{content_hash}`, TTL: 24 hours
- Query result cache - key: `query:{hash}`, TTL: 1 hour
- Model routing usage counters - Gemini daily requests, Claude monthly spend

### 4.3 MinIO: Object Storage

Binary and raw content (voice memos, file attachments).

**Bucket:** `mnemosyne` (created 2026-04-16)

**Path structure within bucket:**
```
/{source_type}/{year}/{month}/{uuid}.{ext}
```
Examples: `/voice/2026/02/abc123.ogg`, `/web/2026/02/def456.pdf`, `/claude_code/2026/04/abc123.pdf`

**Source types:**
- `voice` — Telegram voice memos (OGG)
- `telegram` — Telegram file attachments
- `email` — Email attachments
- `claude_code` — Files processed via Claude Code `/mneme` skill
- `web` — Web clipper attachments

Referenced from wiki pages via `file_ref` frontmatter field (e.g. `file_ref: mnemosyne/claude_code/2026/04/uuid.pdf`). Accessed via presigned URLs.

### 4.4 Obsidian: Human UI

Obsidian reads the wiki repo directly from the local clone. No sync required beyond the
Obsidian git plugin (auto-pull on interval, auto-commit on change).

Key Obsidian features in use:
- **Graph view** - powered by `[[wikilinks]]`; requires consistent wikilink syntax from all writers
- **Dataview plugin** - queries YAML frontmatter; used for ADMIN due dates, PERSON follow-ups,
  PROJECT status tables. Field names in frontmatter must exactly match SCHEMA.md - inconsistent
  names break Dataview queries silently.

---

## 5. IngestItem Interface

All ingestion sources normalize to a common `IngestItem` envelope before processing. This is
the contract between the ingestion layer (n8n / Claude Code) and the processing layer (Hermes / Claude).

```
IngestItem:
  source:            telegram | email | web_clipper | n8n_chat | claude_code | manual
  source_url:        string | null        # original URL if web-sourced
  raw_text:          string               # full text content to classify and store
  file_ref:          string | null        # MinIO path if file attached
  suggested_bucket:  string | null        # hint from the source (user can tag inline)
  capture_ts:        ISO8601 timestamp    # when captured, not when processed
  chat_id:           string | null        # Telegram chat_id for session tracking
```

**Source-specific normalization:**

| Source | raw_text | file_ref | chat_id |
|--------|----------|----------|---------|
| Telegram text | Message body | null | chat_id |
| Telegram voice | Whisper transcript | MinIO OGG path | chat_id |
| Telegram file | Extracted text | MinIO file path | chat_id |
| Telegram URL | Jina Reader markdown | null | chat_id |
| Email | Body + subject | MinIO attachment paths | null |
| Web clipper (inbox/) | File contents | null | null |
| Claude Code (`/mneme`) | User input text | null | null |

---

## 6. Ingestion Layer

### 6.1 Ingestion Sources

| Source | Method | Priority | Status |
|--------|--------|----------|--------|
| Telegram text note | Webhook trigger → n8n → Hermes | HIGH | Phase 2 |
| Telegram voice memo | Voice → Whisper → n8n → Hermes | HIGH | Phase 2 |
| Telegram URL forward | URL → Jina Reader → n8n | MEDIUM | Phase 5 |
| Email newsletter | Gmail label → n8n trigger | MEDIUM | Phase 5 |
| Obsidian Web Clipper | `inbox/` folder → n8n scheduled | MEDIUM | Phase 5 |
| Claude Code `/mneme` | Direct skill - no Hermes needed | HIGH | Phase 1 (direct path) |
| Google Keep archive | Scheduled API poll → n8n | LOW | Phase 6 |
| Google Drive archive | One-time bulk + delta sync | LOW | Phase 6 |

### 6.2 Primary Workflow: Automated Path (Hermes + n8n)

```
Telegram Trigger
    |
    |-- [Voice?] --> Whisper (10.0.50.12) --> transcribed text
    |                    |
    |                    v
    |              Upload audio to MinIO: /voice/{year}/{month}/{uuid}.ogg
    |                    |
    |                    └──> rejoin text path
    |
    v
Normalize to IngestItem
(extract raw_text, source, capture_ts, chat_id)
    |
    v
Dedup Check (Redis: dedup:{content_hash}, TTL 24h)
    |-- [Duplicate] --> Notify user, discard
    |
    v
POST to Hermes /task:
  { workflow: "mnemosyne", task: "ingest", payload: IngestItem }
    |
    v
Hermes reads wiki/SCHEMA.md
    |
    v
Classify into bucket
    |
    |-- [Confidence < threshold OR IDEA/REFERENCE ambiguity]
    |       --> Ask user for clarification via Telegram
    |           Redis session key (TTL 600s)
    |           [No reply → TTL expires] → default to IDEA, notify user
    |           [Reply received] → merge + re-classify
    |
    v
Check index.md for existing entity page (Compound buckets: PERSON/PROJECT/PURSUIT)
    |-- [Existing page] --> Read page → merge new info → update page
    |-- [No page]       --> Create new page in correct bucket directory
    |
    v
Write wiki page (correct frontmatter, [[wikilinks]], per SCHEMA.md)
    |
    v
Update index.md (add/update compact entry under bucket section)
    |
    v
Append to log.md (ISO timestamp | operation | bucket | title | source)
    |
    v
git commit: "mneme: ingest {BUCKET} - {title}"
    |
    v
Telegram confirmation: "Saved as {BUCKET} - [[{title}]] ✓"
```

### 6.3 Direct Path (Claude Code `/mneme` skill)

When Hermes is unavailable, or during an active Claude Code session:

```
User: /mneme {note text}
    |
    v
Claude reads ~/mneme/wiki/SCHEMA.md
    |
    v
Claude reads ~/mneme/wiki/index.md (for entity dedup + cross-reference)
    |
    v
Classify note into bucket (IDEA/REFERENCE boundary: ask if ambiguous)
    |
    v
Check index.md for existing entity (Compound buckets)
    |-- [Existing] --> Read page → merge
    |-- [New]      --> Create page
    |
    v
Write wiki page, update index.md, append log.md
    |
    v
git commit: "mneme: ingest {BUCKET} - {title}"
    |
    v
Report to user: bucket assigned, page created/updated, wikilinks added
```

### 6.4 Voice Memo Flow

```
Telegram voice message (OGG format)
    |
    v
Download audio file
    |
    v
Upload to MinIO: /voice/{year}/{month}/{uuid}.ogg
    |
    v
Send to Whisper LXC (10.0.50.12) for transcription
    |
    v
Transcribed text + file_ref → build IngestItem → continue at §6.2
```

### 6.5 Web Clipper Flow

```
User saves page with Obsidian Web Clipper → lands in wiki/inbox/
    |
    v
n8n scheduled trigger (every 30 min) OR on-demand Telegram /lint
    |
    v
For each file in wiki/inbox/:
    Build IngestItem (source: web_clipper, raw_text: file contents)
    → Hermes processes → wiki page written → move file to wiki/raw-sources/
```

---

## 7. AI Processing Stack

### 7.1 Model Routing Architecture

Tasks are routed based on complexity. Local models handle the majority of work; cloud APIs are only invoked when genuinely needed.

```
Incoming task
    |
    v
Complexity Classification (Ollama self-assesses)
    |
    |-- [Simple: extraction, summarization, classification]
    |       --> Mistral 7B via Ollama (local, free, fast)
    |
    |-- [Complex: synthesis, contradiction handling,
    |    strategic analysis, pattern recognition]
    |       --> Check Gemini free tier (Redis daily counter)
    |           |-- [Available] --> Gemini 2.0 Flash (free tier)
    |           |-- [Exhausted]  --> Check Claude budget (Redis monthly counter)
    |               |-- [Available] --> Claude Sonnet (paid)
    |               |-- [Exhausted]  --> Fallback: Mistral 7B
    |
    |-- [Strategic/judgment calls only]
            --> Claude Sonnet directly (skip Gemini)
```

### 7.2 Model Assignments by Task

| Task | Primary | Escalation |
|------|---------|------------|
| Classification (bucket routing) | Mistral 7B | Gemini Flash |
| Field extraction (frontmatter) | Mistral 7B | Gemini Flash |
| Entity resolution (dedup check) | Mistral 7B | Gemini Flash |
| Summarization | Mistral 7B | Gemini Flash |
| Voice transcription | Whisper | - (local only) |
| Wiki synthesis / Q&A | Mistral 7B | Gemini Flash → Claude Sonnet |
| Idea Synthesis Report | Gemini Flash | Claude Sonnet |
| Serendipity Engine | Gemini Flash | Claude Sonnet |
| Conflict resolution | Claude Sonnet | - |
| Monthly Trend Report | Gemini Flash | Claude Sonnet |

### 7.3 Models Reference

| Model | Host | Role |
|-------|------|------|
| Mistral 7B | Ollama (10.0.50.10) | Default workhorse - simple tasks |
| Whisper | LXC 102 (10.0.50.12) | Voice transcription |
| Gemini 2.0 Flash | Google API (free tier) | Complex tasks; cost-effective escalation |
| Claude Sonnet | Anthropic API (paid) | Strategic/judgment tasks; final escalation |

*Note: nomic-embed-text (embedding model) is no longer required - index.md-based navigation
replaces vector similarity search at the scale this system will operate at.*

---

## 8. Retrieval Layer

### 8.1 Telegram Bot Commands

| Command | Function |
|---------|----------|
| `/search {query}` | Hermes reads index.md → selects relevant pages → synthesizes answer |
| `/ask {question}` | Hermes reads index.md → reads 5-8 relevant pages → synthesizes with citations |
| `/find {name}` | Hermes reads PERSON entity page in full → formats summary |
| `/project {name}` | Hermes reads PROJECT entity page → returns status, next action |
| `/pursuit {name}` | Hermes reads PURSUIT entity page → returns milestone summary |
| `/remind` | Hermes scans ADMIN pages with `status: Pending` and `due <= today+48h` |
| `/lint` | Wiki health check - orphans, broken links, stale entities, missing wikilinks |

### 8.2 Claude Code Direct Retrieval (`/mneme-ask`)

During active Claude Code sessions:
```
User: /mneme-ask {question}
    |
    v
Claude reads SCHEMA.md + index.md
    |
    v
Identifies 3-8 most relevant pages
    |
    v
Reads those pages
    |
    v
Synthesizes answer with [[page]] citations
    |
    v
Offers to file substantial answers as new IDEA or REFERENCE pages
```

### 8.3 Scheduled Reports

| Report | Schedule | Contents |
|--------|----------|----------|
| Daily Digest | Daily, 7:00 AM | Yesterday's captures by bucket; ADMIN due within 48h; PERSON follow-ups due |
| Serendipity Engine | Daily, 7:05 AM (opt-in) | 1 IDEA from yesterday + 3 adjacent pages → unexpected connection |
| Weekly Summary | Sunday, 6:00 PM | Week's captures; active PROJECT next actions; ADMIN due next week |
| Idea Synthesis Report | Sunday, 6:05 PM | Week's IDEAs cross-referenced against full wiki; filed as synthesis page |
| Monthly Trend Report | 1st of month, 8:00 AM | Topic clusters, recurring themes, stale IDEAs, inactive projects |

**Telegram message length limit: 4096 characters.** Long reports must be split across multiple
messages or truncated with a pointer to the full report page in the wiki.

---

## 9. Maintenance Workflows

### 9.1 Wiki Lint

Runs Sunday before Weekly Summary, or on-demand via `/lint`:

- Orphan pages (no inbound wikilinks)
- Broken wikilinks (referenced in index.md but page doesn't exist)
- Stale PERSON/PROJECT/PURSUIT (no activity 90+ days)
- IDEA pages with no outbound wikilinks
- Concepts mentioned 3+ times without their own page

Sends health report to Telegram. On confirmation: fixes broken links, creates stub pages.

### 9.2 Periodic Entity Consolidation

Runs Sunday after Lint, before Weekly Summary:

Hermes scans PERSON/PROJECT/PURSUIT pages for likely duplicates (near-identical names or
summaries). Presents candidates to user via Telegram with merge/rename/keep options.

---

## 10. Infrastructure Requirements

| Service | IP | Role in Mnemosyne |
|---------|----|-------------------|
| Hermes | 10.0.50.17 | AI agent - wiki reads/writes (automated path) |
| n8n | 10.0.50.13 | Workflow engine - Telegram webhook, ingestion orchestration |
| Redis | 10.0.50.15 | Session state, dedup, query cache, model routing counters |
| MinIO | 10.0.50.16 | Voice memo + file attachment object storage |
| Ollama | 10.0.50.10 | Mistral 7B inference |
| Whisper | 10.0.50.12 | Voice transcription |
| Postgres | 10.0.50.14 | Not used by Mnemosyne data layer (argus_logs co-located here) |
| Umami | 10.0.50.18 | Analytics source - weekly snapshots ingested as REFERENCE |

All services on VLAN 50 (Lab Services).

**Wiki repo:** `~/mneme/wiki/` on the local workstation. Hermes accesses via deploy key (SSH).
Remote: private GitHub repo (`mnemosyne-wiki`). Obsidian reads the local clone directly.

---

## 11. Deployment Order

### Phase 0 - Architecture & Design (no Hermes dependency)
1. Write `SCHEMA.md` ✅
2. Create wiki repo (`~/mneme/wiki/`) + scaffold ✅
3. Update this design doc ✅
4. Define IngestItem interface spec ✅
5. Configure Obsidian vault + git plugin + Dataview plugin

### Phase 1 - Foundation (no Hermes dependency)
6. Create private GitHub remote (`mnemosyne-wiki`) and push initial scaffold
7. Configure Obsidian vault pointing at local clone
8. Install Obsidian git plugin (auto-pull 5 min, auto-commit on change)
9. Install Obsidian Dataview plugin and verify frontmatter query
10. Grant Hermes LXC deploy key write access to wiki repo

### Phase 2 - Core Ingest Pipeline (requires Hermes wiki skill + LLM router + HTTP endpoint)
11. Build n8n Telegram webhook trigger workflow
12. Implement text note ingest flow (n8n → Hermes /task)
13. Implement voice memo ingest flow (Whisper → MinIO → ingest)
14. Implement file attachment ingest flow (route by MIME type)
15. End-to-end test: Telegram note → wiki page → Obsidian

### Phase 3 - Retrieval Commands
16. Implement `/search` and `/ask`
17. Implement entity lookup commands (`/find`, `/project`, `/pursuit`)
18. Implement `/remind` (ADMIN frontmatter scan)
19. Configure n8n Chat Trigger as secondary interface

### Phase 4 - Scheduled Reports
20. Build Daily Digest cron
21. Build Serendipity Engine cron
22. Build Weekly Summary + Idea Synthesis Report crons
23. Build Monthly Trend Report cron

### Phase 5 - Extended Sources
24. Email ingestion via Gmail label
25. URL capture via Telegram (Jina Reader)
26. Obsidian Web Clipper inbox processing

### Phase 6 - Bulk Import
27. Google Keep bulk import (supervised mode first)
28. Google Drive selective import

### Phase 7 - Maintenance
29. Wiki Lint workflow
30. Periodic entity consolidation

---

*Part of the Homelab Command Project. Companion documents: Network & Services Architecture v1.9 · Project Roadmap v1.4 · IaC Runbook v1.2 · Argus Design Doc v1.2 · Orpheus Design Doc v1.1 · Ariadne Design Doc v1.0*
