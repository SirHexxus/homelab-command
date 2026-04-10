# Mnemosyne: Project Task Tracker

**PM:** Mnemosyne Project  
**Last Updated:** 2026-04-10 (updated)
**Status:** Phase 0 largely complete; Phase 1 foundation scaffolded; Claude Code direct path live

---

## Project Summary

Mnemosyne is a personal knowledge management system built as a persistent, compounding wiki
stored in a private git repository of markdown files. Knowledge is organized into 7 semantic
buckets (IDEA, ADMIN, REFERENCE, JOURNAL, PERSON, PROJECT, PURSUIT). Capture is via Telegram
(text, voice, file attachments) and eventually email, web clipper, and n8n Chat. Retrieval is
via Telegram bot commands and scheduled reports. The Hermes AI agent reads and writes the wiki.
The user browses it in Obsidian on desktop. There is no dedicated database or Proxmox host —
Mnemosyne is schema + agent + wiki repo on shared infrastructure.

---

## Current Blockers

These items are blocked on external teams or infrastructure and cannot be started until
the dependency is resolved.

| Blocker | Owned By | Blocks |
|---------|----------|--------|
| Hermes LLM Router (Gemini + Claude) | Hermes team | All wiki write operations |
| Hermes wiki skill (`wiki.py`) | Hermes team | All wiki operations |
| Hermes HTTP endpoint (`/task`) | Hermes team | All n8n automated flows |
| Hermes LXC deployed (10.0.50.17) | Hermes team | All live testing |
| Hermes Telegram bot (personal) | Hermes team | User-facing capture and retrieval |

See `apps/hermes/ToDo.md` for the full Hermes requirements spec.

---

## Tasks That Can Start Today

The following tasks have no external dependencies and can be worked immediately.

- [x] Write `SCHEMA.md` — wiki governance document (see Phase 0, Task 3)
- [x] Create wiki git repo and initial directory structure (see Phase 1, Task 1)
- [x] Update Mnemosyne design doc to reflect wiki model architecture (see Phase 0, Task 1)
- [x] Write `/mneme` and `/mneme-ask` Claude Code skills (direct path — no Hermes needed)
- [ ] Configure Obsidian vault pointing at wiki repo (see Phase 1, Task 2)
- [ ] Install and configure Obsidian git plugin (see Phase 1, Task 3)
- [ ] Create private GitHub remote for wiki repo and push initial scaffold (see Phase 1, Task 1)
- [ ] Draft n8n workflow designs for ingest and retrieval (can design before Hermes is live)

---

## Phase 0 — Architecture & Design
**Status:** In progress  
**Blocked by:** Nothing — all Phase 0 tasks are independent

- [x] **0.1** Update `docs/mnemosyne-design-doc-v1.1.md` to reflect the wiki model  
  *Replace all Postgres/pgvector references. Document the new architecture: git wiki repo,
  Obsidian UI, Hermes as wiki agent, 7 buckets as directories, index.md + log.md, YAML
  frontmatter for structured fields. Retire the Notion database IDs section.*  
  **Depends on:** Nothing

- [x] **0.2** Define the `IngestItem` interface spec in the design doc  
  *Document the normalized ingestion envelope that all sources produce. This spec will be
  handed to Hermes as a requirement and used by the Mnemosyne n8n workflows.*  
  **Depends on:** 0.1

- [x] **0.3** Write `SCHEMA.md` — the wiki governance document  
  *This is the most important Mnemosyne artifact. Hermes reads it at the start of every wiki
  operation. Must define: directory structure for 7 buckets, page naming conventions,
  frontmatter schema for each bucket, [[wikilink]] syntax requirements, index.md entry format
  (compact — one line per page), log.md entry format (parseable with grep), cross-reference
  rules, and page creation vs. update decision logic. Location: `wiki/SCHEMA.md` in the wiki
  repo root.*  
  **Depends on:** 0.1

- [ ] **0.4** Finalize multi-source ingestion architecture  
  *Document how each planned ingestion source normalizes to IngestItem: Telegram text, voice,
  file attachments (by type: txt/md, pdf, docx, image, audio, other), email via IMAP/forwarding
  address, web clipper inbox folder, n8n Chat Trigger, future sources. Document the inbox
  staging folder pattern for async sources.*  
  **Depends on:** 0.2

---

## Phase 1 — Foundation (Wiki Repo + Obsidian)
**Status:** Not started  
**Blocked by:** Nothing — all Phase 1 tasks are local/desktop work, no Hermes dependency

- [ ] **1.1** Create private GitHub repo for the wiki and push initial scaffold  
  *Local repo initialized at `~/mneme/wiki/` with initial commit. Needs GitHub remote + push.*  
  *Name: `mnemosyne-wiki` (or similar). Initialize with a `README.md` only. Private repo.
  This is the persistent knowledge store — treat it with appropriate care.*  
  **Depends on:** 0.3 (need the schema before creating structure)

- [x] **1.2** Create initial wiki directory structure and scaffold files  
  *Done: `~/mneme/wiki/` with 11 bucket dirs, SCHEMA.md, index.md, log.md — initial commit made.*  
  *Directories: `wiki/ideas/`, `wiki/admin/`, `wiki/reference/`, `wiki/journal/`,
  `wiki/people/`, `wiki/projects/`, `wiki/pursuits/`, `wiki/raw-sources/`, `wiki/reports/`,
  `wiki/synthesis/`, `wiki/inbox/`*  
  *Files: `wiki/index.md` (blank, with header), `wiki/log.md` (blank, with header),
  `wiki/SCHEMA.md` (from Phase 0 Task 3)*  
  *Add `.gitkeep` to all empty directories.*  
  **Depends on:** 1.1, 0.3

- [ ] **1.3** Configure Obsidian vault pointing at the wiki repo (local clone)  
  *Clone the wiki repo to a local path. Open as an Obsidian vault. Confirm that `[[wikilinks]]`
  resolve correctly, graph view is functional, and Dataview plugin is installed.*  
  **Depends on:** 1.2

- [ ] **1.4** Install and configure the Obsidian git plugin  
  *Configure: auto-pull interval (5 min), auto-commit on change, push on commit. Confirm that
  changes pushed from Hermes (once deployed) appear in Obsidian without manual intervention.*  
  **Depends on:** 1.3

- [ ] **1.5** Install Obsidian Dataview plugin  
  *Required for structured queries over YAML frontmatter (ADMIN due dates, PERSON follow-up
  dates). Confirm a test query over frontmatter works.*  
  **Depends on:** 1.3

- [ ] **1.6** Grant Hermes LXC access to the wiki repo  
  *Generate a deploy key for the wiki repo. Add as a write-access deploy key on GitHub.
  Store private key in Ansible Vault for the Hermes LXC. Confirm that the Hermes service
  user can `git pull` and `git push` from 10.0.50.17.*  
  **Depends on:** 1.1  
  **Blocked by:** Hermes LXC deployed (Blocker 4)

---

## Phase 2 — Core Ingest Pipeline (Telegram Text + Voice)
**Status:** Not started  
**Blocked by:** Hermes wiki skill, Hermes LLM router, Hermes HTTP endpoint, Hermes LXC

- [ ] **2.1** Build n8n Telegram webhook trigger workflow  
  *Receives all incoming messages from `sirhexxus_hermes_bot`. Routes to ingest path for
  text/voice/file messages. Routes to query path for slash command messages. Sends
  confirmation or response back to the user.*  
  **Depends on:** Phase 1 complete  
  **Blocked by:** Hermes HTTP endpoint, Hermes Telegram bot

- [ ] **2.2** Implement text note ingest flow  
  *n8n: receive text → dedup check (Redis hash, 24h TTL) → POST to Hermes `/task` with
  `{workflow: "mnemosyne", task: "ingest", payload: IngestItem}` → receive confirmation →
  send Telegram confirmation to user.*  
  **Depends on:** 2.1  
  **Blocked by:** Hermes wiki skill, Hermes LLM router

- [ ] **2.3** Implement voice memo ingest flow  
  *n8n: receive voice OGG → download file → upload to MinIO (`/voice/{year}/{month}/{uuid}.ogg`)
  → POST audio to Whisper LXC (10.0.50.12) → receive transcribed text → continue as text
  ingest (2.2). Set `file_ref` in IngestItem to MinIO path.*  
  **Depends on:** 2.2  
  **Blocked by:** Same as 2.2

- [ ] **2.4** Implement file attachment ingest flow  
  *n8n: receive file attachment → route by MIME type:*  
  - *`.txt`, `.md` → read text directly → text ingest (2.2)*  
  - *`.pdf` → text extraction (pdfplumber or equivalent) → text ingest (2.2)*  
  - *`.docx` → text extraction → text ingest (2.2)*  
  - *`.ogg`, `.mp3`, `.m4a` → Whisper transcription → text ingest (2.2)*  
  - *Images → upload to MinIO → create stub wiki page with `file_ref` + manual title prompt*  
  - *Other → upload to MinIO → create stub wiki page with `file_ref`*  
  **Depends on:** 2.3  
  **Blocked by:** Same as 2.2

- [ ] **2.5** End-to-end test: Telegram note → wiki page → Obsidian  
  *Send a test note for each bucket type. Confirm: wiki page created correctly, `[[wikilinks]]`
  resolve, index.md updated, log.md updated, Obsidian reflects changes within 5 minutes.*  
  **Depends on:** 2.2, Phase 1 complete

---

## Phase 3 — Retrieval (Telegram Bot Commands)
**Status:** Not started  
**Blocked by:** Phase 2 complete, Hermes Telegram bot, Hermes wiki skill

- [ ] **3.1** Implement `/search {query}` command  
  *n8n: receive slash command → POST to Hermes `/task` with `{task: "query"}` → Hermes reads
  index.md, selects relevant pages, synthesizes answer with citations → return to Telegram.*  
  *Redis cache: key `query:{hash}`, TTL 1h.*  
  **Depends on:** Phase 2 complete

- [ ] **3.2** Implement `/ask {question}` command (RAG Q&A)  
  *Hermes reads index.md → selects 5–8 relevant pages → reads those pages → synthesizes answer
  with citations → returns answer + page references to Telegram. File substantial answers back
  to wiki as new pages.*  
  **Depends on:** 3.1

- [ ] **3.3** Implement entity lookup commands (`/find`, `/project`, `/pursuit`)  
  *Hermes reads index.md → finds entity page → reads entity page in full → formats summary
  for Telegram. PERSON: relationship, last contact, open follow-ups. PROJECT: status, next
  action. PURSUIT: current milestone, next milestone.*  
  **Depends on:** Phase 2 complete

- [ ] **3.4** Implement `/remind` command  
  *Query ADMIN pages with `status: Pending` and `due_date <= today + 48h`. Return formatted
  list to Telegram. Hermes reads relevant pages or uses a Dataview-equivalent frontmatter
  scan.*  
  **Depends on:** Phase 2 complete

- [ ] **3.5** Configure n8n Chat Trigger as secondary interface  
  *Set up n8n's built-in Chat Trigger as an alternative web-based capture/retrieval interface.
  Routes to the same Hermes `/task` endpoint as Telegram. Short messages → ingest path. Messages
  starting with `/ask` or phrased as questions → query path.*  
  **Depends on:** 3.1, 3.2  
  **Blocked by:** Hermes HTTP endpoint

---

## Phase 4 — Scheduled Reports
**Status:** Not started  
**Blocked by:** Phase 2 complete, Phase 3 complete, Hermes wiki skill, capable LLM

- [ ] **4.1** Daily Digest (n8n cron, 7:00 AM)  
  *Hermes reads log.md (yesterday's entries) + ADMIN pages (due within 48h, overdue) + PERSON
  pages (follow-up due). Composes and sends digest to Telegram.*  
  **Depends on:** Phase 2 complete, Phase 3 complete

- [ ] **4.2** Serendipity Engine (n8n cron, 7:05 AM, opt-in)  
  *Hermes reads log.md for yesterday's IDEAs, picks one as anchor, selects 3 semantically
  adjacent pages from across the wiki, generates unexpected connection, sends to Telegram.
  Files substantial connections back as new IDEA pages.*  
  **Depends on:** 4.1

- [ ] **4.3** Weekly Summary (n8n cron, Sunday 6:00 PM)  
  *Week's captures by bucket, active PROJECT next actions, ADMIN due next week,
  1–2 LLM-observed patterns from the week.*  
  **Depends on:** 4.1

- [ ] **4.4** Idea Synthesis Report (n8n cron, Sunday 6:05 PM)  
  *This week's IDEA pages cross-referenced against the full wiki. Ranked connections with
  reasoning. Filed as synthesis page.*  
  **Depends on:** 4.3

- [ ] **4.5** Monthly Trend Report (n8n cron, 1st of month 8:00 AM)  
  *Topic clusters, recurring themes, IDEAs stale >30 days, inactive projects, emerging
  clusters. Filed as report page. Delivered via Telegram.*  
  **Depends on:** 4.4

---

## Phase 5 — Extended Ingestion Sources
**Status:** Not started  
**Blocked by:** Phase 2 complete (these are additive sources, not replacements)

- [ ] **5.1** Email ingestion via forwarding address  
  *Set up dedicated ingestion address on PurelyMail (e.g., `mneme@...`). Configure n8n IMAP
  trigger watching that mailbox. Normalize email body + attachments to IngestItem. Route
  through standard ingest pipeline. Attachments follow file attachment path (Phase 2, Task 4).*  
  **Depends on:** Phase 2 complete

- [ ] **5.2** Email ingestion via Gmail label  
  *Configure n8n Gmail trigger watching label `Mneme/Inbox`. Any email labelled by the user
  gets ingested. Particularly useful for newsletters (likely REFERENCE bucket) and research
  emails.*  
  **Depends on:** 5.1 (same pipeline, different trigger)

- [ ] **5.3** URL / link capture via Telegram  
  *n8n detects URLs in Telegram messages. Fetches page content (Jina Reader API or equivalent
  → clean markdown). Normalizes to IngestItem with `source_url` in metadata. Routes to
  standard ingest → typically REFERENCE bucket.*  
  **Depends on:** Phase 2 complete

- [ ] **5.4** Obsidian Web Clipper → wiki inbox processing  
  *Install Obsidian Web Clipper browser extension. Configure save path to `wiki/inbox/`.
  Set up n8n scheduled trigger (every 30 min) or on-demand Telegram command to process
  `wiki/inbox/` contents: classify each file, integrate into wiki, move to `wiki/raw-sources/`.*  
  **Depends on:** Phase 2 complete, Phase 1 complete

---

## Phase 6 — Bulk Import
**Status:** Not started  
**Blocked by:** Phase 2 complete

- [ ] **6.1** Google Keep bulk import  
  *n8n scheduled workflow via Google Keep API. For each note: normalize to IngestItem, run
  through standard ingest pipeline, mark as migrated. Run in supervised mode first (review
  first 20 items before full run). Estimated volume: TBD.*  
  **Depends on:** Phase 2 complete

- [ ] **6.2** Google Drive selective import  
  *One-time + periodic delta sync. PDFs → text extraction. Docs → Google Docs API pull.
  Originals remain in Drive; summaries + wiki pages written to Mnemosyne. Selective, not
  bulk — curate what is worth ingesting.*  
  **Depends on:** Phase 2 complete, 5.3 (URL handling pattern)

---

## Phase 7 — Maintenance Workflows
**Status:** Not started  
**Blocked by:** Phase 2 complete (wiki must have content before maintenance is meaningful)

- [ ] **7.1** Wiki Lint (n8n cron, Sunday before Weekly Summary, or on-demand `/lint`)  
  *Hermes reads index.md in full. Checks for: orphan pages (no inbound wikilinks), broken
  wikilinks (referenced but not in index), stale PERSON/PROJECT/PURSUIT (no activity 90+ days),
  IDEA pages with no outbound links, concepts mentioned 3+ times without their own page.
  Sends health report to Telegram. On confirmation: fixes broken links, creates stub pages.*  
  **Depends on:** Phase 4 complete

- [ ] **7.2** Periodic entity consolidation  
  *Hermes scans PERSON/PROJECT/PURSUIT pages for likely duplicates (near-identical names or
  summaries). Presents candidates to user via Telegram with merge/rename/keep options.
  Runs Sunday before Weekly Summary, after Lint.*  
  **Depends on:** 7.1

---

## Parking Lot — Future Consideration

These items have been identified but are not scheduled. Revisit after Phase 3 is complete.

- **Obsidian Dataview dashboards** — dynamic tables for ADMIN tasks, PERSON follow-ups,
  PROJECT status. Requires consistent YAML frontmatter from Hermes wiki writes.
- **Apple Shortcuts / iOS capture** — shortcut that sends text to the Telegram bot for
  capture. No backend work required; purely a device-side setup task.
- **qmd search integration** — local hybrid BM25/vector search over wiki markdown files.
  Relevant when wiki exceeds ~500 pages and index.md-based navigation becomes slow.
  See: https://github.com/tobi/qmd
- **Argus integration** — incidents stored as JOURNAL/REFERENCE entries in Mnemosyne.
  Coordination with Argus project required. Defer until Argus Phase 3.
- **Umami analytics ingestion** — weekly analytics snapshots as REFERENCE entries.
  Originally designed for n8n HTTP Request node. Revisit when Mnemosyne ingest is stable.

---

## Dependency Map (Visual)

```
Phase 0 (Design) ─────────────────────────────────────┐
    │                                                   │
    ▼                                                   │
Phase 1 (Foundation — no Hermes needed) ──────────────┤
    │                                                   │
    ▼  [BLOCKED: Hermes wiki skill + LLM + HTTP + LXC] │
Phase 2 (Core Ingest) ────────────────────────────────┤
    │                                                   │
    ├──► Phase 3 (Retrieval) ───────────────────────── ┤
    │        │                                          │
    │        ▼                                          │
    └──► Phase 4 (Reports) ─────────────────────────── ┤
             │                                          │
             ├──► Phase 5 (Extended Sources) ────────── ┤
             │        │                                  │
             │        ▼                                  │
             └──► Phase 6 (Bulk Import) ─────────────── ┤
                       │                                 │
                       ▼                                 │
                  Phase 7 (Maintenance) ─────────────────┘
```

The critical path is: Phase 0 → Phase 1 → **[Hermes delivers]** → Phase 2 → Phase 3/4/5/6/7.
Phases 0 and 1 are the only Mnemosyne work that can proceed today.

---

*For Hermes requirements: see `apps/hermes/ToDo.md`*  
*For full system design: see `docs/mnemosyne-design-doc-v1.1.md`*
