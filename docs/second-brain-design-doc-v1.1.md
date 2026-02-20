# Second Brain Design Doc
**Version:** 1.1
**Last Updated:** February 2026
**Status:** Living Document — implementation will surface unknowns not captured here

---

## 1. Purpose & Philosophy

The Second Brain is a personal knowledge management system designed to solve a specific problem: ADHD executive function failures cause valuable thoughts, information, and context to evaporate before they can be acted on. The system's job is to make capture frictionless, storage automatic, and retrieval intelligent.

**Design principles:**
- Capture must be faster than the thought can escape — minimum friction at point of entry
- Classification and organization happen after capture, never during
- Retrieval must be semantic, not just keyword-based — the system should find what you mean, not just what you typed
- Every piece of information should be connected to related context automatically
- No information is ever deleted — only archived or superseded

---

## 2. System Overview

```
INGESTION LAYER
(Telegram, Email, Voice, Web, Bulk Import)
         |
         v
  n8n PROCESSING LAYER
  (AI classify, entity resolve, enrich, embed, route)
         |
    _____|______________________________________
    |           |              |           |
    v           v              v           v
POSTGRES    POSTGRES        MINIO       NOTION
second_brain argus_logs     Objects     UI Layer
(pgvector)  (TimescaleDB)
         |
         v
  RETRIEVAL LAYER
  (Telegram bot, Scheduled reports, Notion views)
```

---

## 3. Bucket Definitions

Buckets fall into two structural categories that drive different ingestion and storage behavior.

**Atomic buckets** — each entry is independent. New entries are always new records. No reconciliation needed.

**Compound buckets** — many entries may refer to the same real-world entity. New entries must be reconciled against existing entities before storage.

| Bucket | Type | Purpose | Key Distinction |
|--------|------|---------|----------------|
| IDEA | Atomic | Abstract thoughts, opinions, insights, interpretations, and questions — including questions about concrete or verifiable things. The question itself is the idea; a verified answer becomes a REFERENCE. Generally not verifiable in their current form. | Your inner world; subjective |
| ADMIN | Atomic | Tasks and errands with due dates | Actionable, time-bound |
| REFERENCE | Atomic | Concrete facts, sources, data, information — verifiable and/or quantifiable | External, objective reality |
| JOURNAL | Atomic | Reflective entries; experiences, decisions, observations, growth. Log-style factual entries (meetings, deployments, events) are equally welcome alongside deeper reflection | Time-anchored experience |
| PERSON | Compound | Individuals; context, follow-ups, relationship notes, interaction history | About *who* |
| PROJECT | Compound | Multi-step work with a defined end state; status, next actions, accumulated notes | Has a finish line |
| PURSUIT | Compound | Ongoing endeavors without a terminal end state; evolving intermediate goals, accumulated history and context | No finish line |

**IDEA vs. REFERENCE disambiguation note for AI classifier:** The boundary between IDEA and REFERENCE can be ambiguous (e.g. a half-formed thought *about* a verifiable fact, or a question about a concrete thing). When confidence is below threshold at this specific boundary, the classifier should always ask for clarification rather than guess. Misclassification here produces the most disorienting retrieval experience.

---

## 4. Data Storage Architecture

### 4.1 Postgres: second_brain database

Primary knowledge store. All structured data, vector embeddings, and entity records live here.

**Extensions required:** pgvector, pg_trgm, fuzzystrmatch

**Core schema:**

```sql
-- Entity table for Compound buckets (PERSON, PROJECT, PURSUIT)
CREATE TABLE entities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket      VARCHAR(20),        -- PERSON, PROJECT, PURSUIT
    name        TEXT NOT NULL,
    aliases     TEXT[],             -- alternate names/spellings
    summary     TEXT,               -- AI-maintained rolling summary
    embedding   vector(768),        -- embedding of summary; used for similarity search
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Master resource table
CREATE TABLE resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    original_text   TEXT,
    summary         TEXT,           -- AI-generated, ~200 words
    source_type     VARCHAR(50),    -- telegram, email, web, voice, bulk
    source_url      TEXT,
    bucket          VARCHAR(20),    -- IDEA, ADMIN, REFERENCE, JOURNAL,
                                    -- PERSON, PROJECT, PURSUIT
    entity_id       UUID REFERENCES entities(id),  -- NULL for Atomic buckets
    slug            TEXT UNIQUE,
    object_path     TEXT,           -- MinIO path if file attached
    embedding       vector(768),    -- nomic-embed-text via Ollama
    confidence      INTEGER,        -- AI classification confidence 0-100
    metadata        JSONB,          -- bucket-specific structured fields
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ     -- soft delete only; nothing is ever hard deleted
);

-- Vector similarity indexes
CREATE INDEX ON resources
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX ON entities
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Full-text search
CREATE INDEX ON resources
    USING GIN (to_tsvector('english',
        title || ' ' || COALESCE(summary, '')));

-- Ingestion log (permanent audit trail; never modified after write)
CREATE TABLE ingestion_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id     UUID REFERENCES resources(id),
    entity_id       UUID REFERENCES entities(id),
    original_text   TEXT,
    summary         TEXT,
    bucket          VARCHAR(20),
    source          VARCHAR(50),
    confidence      INTEGER,
    reconciliation  VARCHAR(20),    -- new_entity, appended, user_confirmed,
                                    -- auto_matched
    notion_url      TEXT,
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Tags
CREATE TABLE tags (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name    TEXT UNIQUE NOT NULL
);

CREATE TABLE resource_tags (
    resource_id UUID REFERENCES resources(id) ON DELETE CASCADE,
    tag_id      UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (resource_id, tag_id)
);
```

**Bucket-specific metadata (stored in JSONB `metadata` field):**

| Bucket | Key Fields |
|--------|-----------|
| PERSON | name, relationship, last_contact, follow_up_date, follow_up_needed |
| PROJECT | goal, status (Not Started/Active/Blocked/Done), next_action, deadline |
| PURSUIT | current_milestone, next_milestone, season_or_phase, notes |
| IDEA | one_liner, tags, themes, elaboration |
| ADMIN | task, due_date, status (Pending/Done), recurrence |
| REFERENCE | source_url, author, publication_date, key_takeaways, credibility_notes |
| JOURNAL | mood, related_entities, decision_made, outcome_known |

### 4.2 Postgres: argus_logs database

Time-series security log storage. See Argus Design Doc for full schema.

### 4.3 Redis

Ephemeral and session storage:
- Query result cache — key: `query:{hash}`, TTL: 1 hour
- Deduplication — key: `dedup:{content_hash}`, TTL: 24 hours
- Multi-turn Telegram conversation session state
- AI Q&A context chains
- Model routing usage counters — Gemini daily requests, Claude monthly spend

### 4.4 MinIO (S3-compatible object storage)

Binary and raw content. Path structure:
```
/{source_type}/{year}/{month}/{uuid}.{ext}
```
Examples: `/voice/2026/02/abc123.ogg`, `/web/2026/02/def456.pdf`

Referenced from Postgres via `resources.object_path`. Accessed via presigned URLs.

### 4.5 Notion (Human UI Layer)

Notion is not the primary data store — Postgres is. Notion is the human-browsable interface. Seven bucket databases plus the ingestion log:

| Database | Notion ID | Type |
|----------|-----------|------|
| PERSON | 2fbf688b-b4c5-80c6-ae26-ee5a70effbcf | Compound |
| PROJECT | 2fbf688b-b4c5-80ae-95d2-f330d2acbf43 | Compound |
| IDEA | 2fbf688b-b4c5-801c-875c-fd29cd7baecd | Atomic |
| ADMIN | 2fbf688b-b4c5-8009-9a03-ed66c6403309 | Atomic |
| LOG-FILES | 2fbf688b-b4c5-807a-9e86-d2febaefd89d | Audit log |
| REFERENCE | *(to be created — update ID after creation)* | Atomic |
| JOURNAL | *(to be created — update ID after creation)* | Atomic |
| PURSUIT | *(to be created — update ID after creation)* | Compound |

**LOG-FILES schema:**

| Field | Type | Notes |
|-------|------|-------|
| Slug | Title | URL-friendly identifier |
| Original Text | Text | Raw input as received |
| Summary | Text | AI-generated brief summary |
| Bucket | Select | All 7 buckets |
| Notion Link | URL | Link to created/updated page in bucket DB |
| Source | Select | Telegram, Email, Web, Voice, Bulk |
| Timestamp | Date | When received |
| Confidence | Number | AI classification confidence score |
| Reconciliation | Select | New Entity, Appended, User Confirmed, Auto Matched |

---

## 5. Ingestion Layer

### 5.1 Ingestion Sources

| Source | Method | Priority | Status |
|--------|--------|----------|--------|
| Telegram text note | Webhook trigger → n8n | HIGH | Needs redeploy to VLAN 50 |
| Telegram voice memo | Voice → Whisper → n8n | HIGH | Needs rebuild |
| Telegram link forward | URL → scrape → n8n | MEDIUM | Planned |
| Email newsletter | Gmail label → n8n trigger | MEDIUM | Planned |
| Google Keep archive | Scheduled API poll → n8n | MEDIUM | Planned |
| Google Drive archive | One-time bulk + delta sync | LOW | Planned |
| Web content | Telegram URL forward or bookmarklet | LOW | Planned |

### 5.2 Primary Workflow: Telegram Note Capture

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
Normalize Input
(extract text, chatId, userId, timestamp, source)
    |
    v
Dedup Check (Redis: dedup:{content_hash}, TTL 24h)
    |-- [Duplicate] --> Notify user, discard
    |
    v
Split Detection
(AI: does this contain multiple distinct items? >90% confidence to split)
    |-- [Yes] --> Split into sub-items --> process each independently
    |
    v
AI Classification (see Section 6 for model routing)
Returns: bucket, confidence, reasoning, needs_clarification,
         clarification_question, extracted fields
    |
    |-- [confidence < 70 OR needs_clarification]
    |       --> Ask user for clarification via Telegram
    |           Wait 10 min → [No reply] → default to IDEA
    |           [Reply received] → merge + re-classify
    |
    v
Branch by Bucket Type
    |
    |-- [ATOMIC: IDEA / ADMIN / REFERENCE / JOURNAL]
    |       --> Extract bucket-specific fields (AI)
    |       --> Generate embedding (nomic-embed-text via Ollama)
    |       --> Write to Postgres: resources
    |       --> Write to Notion: bucket database (new page)
    |       --> Write to Postgres: ingestion_log
    |       --> Write to Notion: LOG-FILES
    |
    |-- [COMPOUND: PERSON / PROJECT / PURSUIT]
    |       --> Extract entity name/identifier (AI)
    |       --> Entity Resolution (see Section 5.3)
    |       --> Generate embedding
    |       --> Write to Postgres: resources (with entity_id)
    |       --> Update entity summary (AI rolling summary)
    |       --> Write to Notion: append to existing page OR create new
    |       --> Write to Postgres: ingestion_log
    |       --> Write to Notion: LOG-FILES
    |
    v
[Has date/appointment?] --> Create Google Calendar event
    |
    v
Telegram confirmation: "Saved as [BUCKET] ✓"
(Compound: "Added to [Entity Name] — now has N entries ✓")
```

### 5.3 Entity Resolution Workflow (Compound Buckets)

```
Extract entity name from new entry
    |
    v
Search Postgres entities table:
    - Fuzzy name match (pg_trgm)
    - Vector similarity (embedding <=> query_vector)
    |
    |-- [Match found, confidence >85%]
    |       --> Telegram: "This looks like it's about [Name].
    |           Add to existing entry? (Yes / No / New)"
    |           [Yes] --> append to entity
    |           [No]  --> create new entity
    |           [New] --> create new entity with disambiguation note
    |
    |-- [Match found, confidence 60-85%]
    |       --> Always ask user — ambiguity too high to assume
    |
    |-- [No match]
            --> Create new entity record
```

**Append vs. Replace logic — once entity confirmed:**

```
AI determines update type:
    |
    |-- New fact about entity
    |       --> Add to metadata JSONB
    |
    |-- Status change (PROJECT/PURSUIT)
    |       --> Update status field; log previous state in ingestion_log
    |
    |-- Follow-up resolved (PERSON)
    |       --> Mark previous follow_up as complete; log outcome
    |
    |-- Contradicts existing data
            --> Flag conflict; present both versions to user via Telegram
                User resolves; both versions preserved in ingestion_log
```

Ingestion_log is never modified after write — full history is always preserved regardless of how the entity record evolves.

### 5.4 Voice Memo Flow

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
Transcribed text → rejoin primary classification pipeline
resources.object_path = MinIO path
```

### 5.5 Email Newsletter Processing (Planned)

```
Gmail label: "SecondBrain/Newsletters"
    |
    v
n8n Gmail trigger (watch label)
    |
    v
Extract: sender, subject, body, links
    |
    v
Jina Reader API or Mercury Parser → clean article text
    |
    v
AI: summarize, extract key concepts → classify (likely REFERENCE)
    |
    v
Standard ingestion pipeline
```

### 5.6 Bulk Import (Planned)

- **Google Keep:** n8n scheduled workflow via Google Keep API; mark as migrated after successful transfer
- **Google Drive:** One-time bulk ingestion + periodic delta sync; PDFs → text extraction; Docs → direct API pull; originals stay in Drive; summaries + embeddings written to Postgres

---

## 6. AI Processing Stack

### 6.1 Model Routing Architecture

Tasks are routed based on complexity. Mistral 7B (local) handles the majority of work; cloud APIs are only invoked when genuinely needed, minimizing cost and latency.

```
Incoming task
    |
    v
Complexity Classification (Mistral 7B self-assesses)
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

Usage counters stored in Redis. Gemini tracked by daily requests; Claude tracked by monthly spend. Alerts triggered at 80% of budget thresholds.

### 6.2 Model Assignments by Task

| Task | Primary | Escalation | Notes |
|------|---------|------------|-------|
| Classification (bucket routing) | Mistral 7B | Gemini Flash | Simple categorization; local first |
| Field extraction (bucket metadata) | Mistral 7B | Gemini Flash | Structured extraction; usually simple |
| Entity resolution | Mistral 7B | Gemini Flash | Name matching + similarity; usually simple |
| Summarization | Mistral 7B | Gemini Flash | Routine summarization; local first |
| Embedding generation | nomic-embed-text | — | Local only; no cloud fallback |
| Voice transcription | Whisper | — | Local only; no cloud fallback |
| RAG Q&A synthesis | Mistral 7B | Gemini Flash → Claude Sonnet | Escalate on complex reasoning |
| Idea Synthesis Report | Gemini Flash | Claude Sonnet | Synthesis = complex by default |
| Serendipity Engine connections | Gemini Flash | Claude Sonnet | Creative connection-finding = complex |
| Conflict resolution (contradicts existing data) | Claude Sonnet | — | Judgment call; premium from the start |
| Monthly Trend Report | Gemini Flash | Claude Sonnet | Pattern analysis = complex by default |

### 6.3 Models Reference

| Model | Host | Role |
|-------|------|------|
| Mistral 7B | Ollama (10.0.50.10) | Default workhorse for simple tasks |
| nomic-embed-text | Ollama (10.0.50.10) | All embedding generation; 768-dim vectors |
| Whisper | LXC 102 (10.0.50.12) | Voice transcription |
| Gemini 2.0 Flash | Google API (free tier) | Complex tasks; cost-effective escalation |
| Claude Sonnet | Anthropic API (paid) | Strategic/judgment tasks; final escalation tier |

---

## 7. Retrieval Layer

### 7.1 Telegram Bot Commands

| Command | Function |
|---------|----------|
| `/note {text}` | Primary capture — runs full ingestion pipeline |
| `/search {query}` | Semantic search via pgvector; returns top 5 results |
| `/ask {question}` | RAG Q&A — vector search → retrieve context → Mistral 7B synthesis → answer |
| `/find {name}` | Look up a PERSON entity; returns full accumulated summary |
| `/project {name}` | Look up a PROJECT entity |
| `/pursuit {name}` | Look up a PURSUIT entity |
| `/remind` | List upcoming ADMIN items with due dates |
| `/connect {query}` | On-demand Connection Recommender — semantic search across all buckets for non-obvious links |

**Semantic search flow (`/search`):**
```
Receive query
    |
    v
Check Redis cache (key: query:{hash}, TTL: 1h)
    |-- [Hit]  --> return cached results
    |-- [Miss] --> continue
    |
    v
Generate query embedding (nomic-embed-text via Ollama)
    |
    v
Postgres vector search:
    SELECT id, title, summary, bucket,
           embedding <=> query_vector AS distance
    FROM resources
    WHERE deleted_at IS NULL
    ORDER BY embedding <=> query_vector
    LIMIT 10
    |
    v
If object_path exists --> generate MinIO presigned URL
    |
    v
Cache results in Redis (1h TTL)
    |
    v
Format and send to Telegram
```

**RAG Q&A flow (`/ask`):**
```
Receive question
    |
    v
Vector search: top 5 relevant resources
    |
    v
Build prompt:
    "Context: {resource 1 content}
     Context: {resource 2 content}
     ...
     Question: {user question}
     Answer based only on context provided."
    |
    v
Route via Section 6 model logic
(Mistral 7B default → escalate if complex)
    |
    v
Return answer + source references to Telegram
```

### 7.2 Scheduled Reports

| Report | Schedule | Delivery | Contents |
|--------|----------|----------|----------|
| Daily Digest | Daily, 7:00 AM | Telegram | Yesterday's captures by bucket; ADMIN items due within 48h; overdue PERSON follow-ups |
| Serendipity Engine | Daily, 7:05 AM (opt-in) | Telegram | 1+ IDEA from yesterday as anchor; 2 randomly selected notes from other buckets; AI-generated unexpected connection between them |
| Argus Security Digest | Daily, 7:05 AM | Telegram | Yesterday's notable security events; unresolved high-severity incidents; SIEM health check — see Argus Design Doc for full detail |
| Weekly Summary | Sunday, 6:00 PM | Telegram | Week's captures by bucket; AI-identified connections; open PROJECT next actions; ADMIN due next week |
| Idea Synthesis Report | Sunday, 6:05 PM | Telegram | Last week's IDEAs as index; AI searches full knowledge base for connections to those fresh ideas; ranked by relevance and potential value |
| Monthly Trend Report | 1st of month, 8:00 AM | Telegram + Notion page | Topic clusters; most active projects; recurring themes; IDEAs sitting >30 days without follow-up |

### 7.3 On-Demand Reports

| Command | Function |
|---------|----------|
| `/connect {query}` | Connection Recommender — surfaces semantically related notes across all buckets |
| `/project {name}` | Full PROJECT entity summary — accumulated notes, current status, next action |
| `/pursuit {name}` | Full PURSUIT entity summary — history, current milestone, next milestone |
| `/find {name}` | Full PERSON entity summary — relationship context, interaction history, open follow-ups |

---

## 8. Periodic Entity Consolidation

A background cleanup workflow runs weekly, Sunday before the Weekly Summary, to catch duplicate entities that slipped through real-time reconciliation.

```
Query Postgres:
    SELECT candidate pairs of PERSON/PROJECT/PURSUIT entities
    WHERE embedding <=> embedding < 0.15 (cosine distance)
    AND NOT already reviewed or linked
    |
    v
For each candidate pair:
    AI evaluates: same entity or genuinely distinct?
    |
    |-- [Likely same]
    |       --> Telegram: "These look like duplicates:
    |           [Marcus Chen] and [Marcus from IT]
    |           Merge? (Yes / No / Rename)"
    |
    |-- [Distinct]
            --> Flag as reviewed; skip in future consolidation runs
```

Consolidation runs before the Weekly Summary so any merges are reflected in that report.

---

## 9. Workflow Status

| Workflow | Status | Notes |
|----------|--------|-------|
| Telegram text capture | Needs redeploy | Was working on TrueNAS n8n; rebuild on VLAN 50 |
| AI classification (model routing) | Needs redeploy | Confirmed working previously; update for new routing logic |
| Notion bucket saves (PERSON/PROJECT/IDEA/ADMIN) | Needs redeploy | Database IDs confirmed |
| Notion LOG-FILES logging | Needs redeploy | Schema confirmed |
| Google Calendar event creation | Needs redeploy | Was working |
| Telegram confirmation | Needs redeploy | Was working |
| Entity resolution (Compound buckets) | Build fresh | New architecture |
| Voice memo → Whisper → pipeline | Build fresh | Whisper now has dedicated LXC |
| Vector embedding → pgvector | Build fresh | Replacing Qdrant with pgvector |
| Email newsletter processing | Build fresh | Planned |
| Semantic search (/search) | Build fresh | Planned |
| RAG Q&A (/ask) | Build fresh | Planned |
| Daily Digest | Build fresh | Planned |
| Serendipity Engine | Build fresh | Planned |
| Weekly Summary | Build fresh | Planned |
| Idea Synthesis Report | Build fresh | Planned |
| Monthly Trend Report | Build fresh | Planned |
| Periodic Entity Consolidation | Build fresh | Planned |
| Google Keep bulk import | Build fresh | Planned |

---

## 10. Infrastructure Requirements

| Service | IP | Notes |
|---------|----|-------|
| n8n | 10.0.50.13 | Workflow engine; IaC redeploy required first |
| Postgres | 10.0.50.14 | second_brain + argus_logs; pgvector + TimescaleDB |
| Redis | 10.0.50.15 | Session, cache, and model routing counters |
| MinIO | 10.0.50.16 | Object storage |
| Ollama | 10.0.50.10 | nomic-embed-text + Mistral 7B inference |
| Whisper | 10.0.50.12 | Voice transcription; LXC 102 |

All services on VLAN 50 (Lab Services). All IaC-deployed via Terraform + Ansible.

---

## 11. Deployment Order

Follows Phase 1 and Phase 2 of the Project Roadmap.

1. Deploy n8n via IaC (10.0.50.13)
2. Deploy Postgres with pgvector + TimescaleDB (10.0.50.14)
3. Deploy Redis (10.0.50.15)
4. Deploy MinIO (10.0.50.16)
5. Verify Whisper operational (10.0.50.12)
6. Verify Ollama + nomic-embed-text + Mistral 7B (10.0.50.10)
7. Create REFERENCE, JOURNAL, PURSUIT Notion databases; update IDs in this doc
8. Rebuild Telegram capture + classification workflow with model routing logic
9. Add Entity Resolution step for Compound buckets
10. Rebuild Notion database writes (all 7 buckets)
11. Add pgvector embedding step to ingestion pipeline
12. Test end-to-end: Telegram note → Postgres → Notion → confirmation
13. Build `/search` and `/ask` Telegram commands
14. Build Daily Digest and Serendipity Engine
15. Build Weekly Summary and Idea Synthesis Report
16. Add voice memo path (Telegram → Whisper → pipeline)
17. Add email newsletter ingestion
18. Build Periodic Entity Consolidation workflow
19. Plan Google Keep bulk import

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.1 · Network & Services Architecture v1.4 · Project Roadmap v1.2 · IaC Runbook v1.1 · Argus Design Doc v1.1 · Media Stack Design Doc v1.1 · Ariadne Design Doc v1.0*
