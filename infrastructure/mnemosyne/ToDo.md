# Mnemosyne: Project Task Tracker

**PM:** Mnemosyne Project  
**Last Updated:** 2026-05-20 (Layer 3 work tracked separately — see below)

> ⚠️ **Active session pickup:** see `LAYER-3-PICKUP.md` for the Layer 3 ingest evaluation work in progress. Phase 0 (Gemini bridge for image OCR/VLM + URL extraction in `Mnemosyne Ingest v1` n8n workflow) is awaiting James's approval to start.
**Status:** Phase 0 mostly done; Phase 1 complete; Phase 2 complete via interim path
(inbox-receiver); Phase 4 Daily Digest live; target-path migration (Phase 2T) and
Phase 3 retrieval queued at the 2026-06-01 Decide gate

---

## Project Summary

Mnemosyne is a personal knowledge management system built as a persistent, compounding
wiki stored in a private git repository of markdown files. Knowledge is organized into
7 semantic buckets (IDEA, ADMIN, REFERENCE, JOURNAL, PERSON, PROJECT, PURSUIT). Capture
runs today through two paths: Claude Code direct (`/mneme`, `/mneme-ask` skills) and a
cron-based n8n pipeline (Telegram text/voice/file → inbox-receiver → `claude -p` sweep
→ wiki). The Hermes-routed target path (replacing `claude -p` with `[[Project - Hermes]]`
autonomous execution) is queued at the 2026-06-01 Decide gate.

Mnemosyne is a **peer subsystem** that requests services from Hermes — it is not strictly
downstream. The wiki is the long-term store; Hermes and Claude Code are alternative
execution surfaces against it. There is no Postgres, no pgvector, and no dedicated
Proxmox host.

---

## Active Gates

| Gate | Date | Decides |
|------|------|---------|
| Decide First Mnemosyne and Hermes Build Sprint | 2026-06-01 | Whether the next sprint is Phase 2T (Hermes-routed ingest), Daily Digest LLM swap, GeminiClient refactor, or ReAct-loop scope reduction |

See `[[Decide First Mnemosyne and Hermes Build Sprint]]` for the candidate list.

---

## Phase 0 — Architecture & Design
**Status:** Mostly complete; 0.4–0.6 open

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

- [ ] **0.5** Architect the Calendar + Google Tasks integration for User ADMIN tasks  
  *Triggered by the daily-digest Google Calendar block (landed 2026-05-19) retiring the
  manual `due:` advancement on recurring-event pages. Decided: Google Tasks is the mechanism
  for one-off User to-dos; the n8n pipeline gets built up to standardize ingestion/retrieval.
  Not yet decided: the n8n / Python division of labor, the Google credential read/write
  split, whether the digest renders Tasks as obligations, and the wiki-bucket vs
  scheduling-layer framing. See THOUGHTS.md "Recurring & User ADMIN Tasks" for the proposals,
  reasoning, and open questions. Output of this pass: the ratified architecture plus concrete
  build tasks (`gtasks.py`, digest wiring, n8n ingestion routing for `task_type: user`)
  slotted into Phase 2.*  
  **Depends on:** Nothing

- [ ] **0.6** Re-mint the Google OAuth refresh token with `tasks.readonly` added  
  *The token minted 2026-05-19 is `calendar.readonly` only; reading Google Tasks needs
  `tasks.readonly`. Change `gcal-authorize`'s `CALENDAR_SCOPE` constant to a scope list and
  re-run the consent flow. Firm regardless of 0.5's outcome — the digest must read Tasks.*  
  **Depends on:** 0.5 (confirm the final scope list first)

---

## Phase 1 — Foundation (Wiki Repo + Obsidian)
**Status:** Complete

- [x] **1.1** Create private GitHub repo for the wiki and push initial scaffold  
  *Done: local repo at `~/mneme/wiki/` pushed to private GitHub remote.*

- [x] **1.2** Create initial wiki directory structure and scaffold files  
  *Done: `~/mneme/wiki/` with 11 bucket dirs, SCHEMA.md, index.md, log.md.*

- [x] **1.3** Configure Obsidian vault pointing at the wiki repo (local clone)

- [x] **1.4** Install and configure the Obsidian git plugin

- [x] **1.5** Install Obsidian Dataview plugin

- [x] **1.6** Grant Hermes LXC access to the wiki repo  
  *Done: deploy key on GitHub; private key in Ansible Vault; Hermes service user can
  `git pull` and `git push` from 10.0.50.17.*

---

## Phase 2 — Ingest Pipeline (Interim, Complete)
**Status:** Complete via interim path — Telegram → n8n → inbox-receiver LXC (10.0.50.19)
→ `wiki/inbox/` → `inotifywait` + hourly cron `claude -p` → wiki. Workflow exported to
`infrastructure/mnemosyne/n8n/mnemosyne-ingest-v1.json` (built 2026-04-29).

- [x] **2.1** Build n8n Telegram webhook trigger workflow *(interim path, 2026-04-29)*

- [x] **2.2** Implement text note ingest flow *(interim path, 2026-04-29)*  
  *n8n → inbox-receiver LXC → `wiki/inbox/` → `claude -p` sweep. Bypasses Hermes.*

- [x] **2.3** Implement voice memo ingest flow *(interim path, 2026-04-29)*  
  *n8n → Whisper LXC (10.0.50.12) → MinIO for audio → text ingest.*

- [x] **2.4** Implement file attachment ingest flow *(interim path, 2026-04-29)*  
  *Route by MIME type: text/pdf/docx → text ingest; audio → Whisper; binary → MinIO stub.*

- [x] **2.5** End-to-end test: Telegram note → wiki page → Obsidian *(interim path, 2026-04-29)*

---

## Phase 2T — Ingest Pipeline (Target, Hermes-routed)
**Status:** Not started — one of four candidates at the 2026-06-01 Decide gate.

The interim path bypasses Hermes via the inbox-receiver LXC. The architectural target is
to route ingest through `POST http://10.0.50.17:8765/task` and let Hermes execute the
classify-and-write loop, retiring the inbox-receiver LXC and the `claude -p` sweep cron.

- [ ] **2T.1** Swap n8n target URL from `10.0.50.19:8080/inbox` to `10.0.50.17:8765/task`  
  *Update both the inbox-receiver POST node and any conditional routing in
  `mnemosyne-ingest-v1.json`. Add Bearer token from Ansible Vault.*

- [ ] **2T.2** Validate Hermes wiki skill invocation against the IngestItem envelope  
  *Confirm Hermes `lib/skills/wiki.py` handles the n8n-shaped payload; resolve any schema
  drift between the interim path's expected fields and Hermes's expected fields.*

- [ ] **2T.3** End-to-end validation against target path  
  *Same test matrix as 2.5; confirm parity with interim path output (page placement,
  index.md update, log.md update, git commit + push).*

- [ ] **2T.4** Retire the inbox-receiver LXC + `inotifywait` daemon + hourly sweep cron  
  *Only after target path runs cleanly for 7+ days. Tear-down is reversible by reverting
  the n8n URL swap.*

- [ ] **2T.5** Update `apps/hermes/THOUGHTS.md` Phase 3 single-shot architecture section  
  *If the target-path build adopts single-shot dispatch (vs. ReAct), update the rationale
  in place. Pure ReAct routing for ingest is unlikely the right choice.*

**Depends on:** Decide gate selection of 2T as the next sprint; or, independently, of
the ReAct-loop scope reduction candidate.

---

## Phase 3 — Retrieval (Telegram via n8n + Claude Code Direct)
**Status:** Not started — buildable now. Architecture viable (Gemini billing live;
n8n owns the Telegram surface; Hermes off hold).

- [ ] **3.1** Implement `/search {query}` command via n8n  
  *n8n Telegram Trigger → POST to Hermes `/task` with `{task: "query"}` (or `claude -p`
  in the interim) → Hermes/Claude reads index.md, selects relevant pages, synthesizes
  answer with citations → return to Telegram. Redis cache: key `query:{hash}`, TTL 1h.*

- [ ] **3.2** Implement `/ask {question}` command (RAG Q&A)  
  *Reads index.md → selects 5–8 relevant pages → reads those pages → synthesizes answer
  with citations → returns answer + page references to Telegram. File substantial answers
  back to wiki as new pages.*  
  **Depends on:** 3.1

- [ ] **3.3** Implement entity lookup commands (`/find`, `/project`, `/pursuit`)  
  *PERSON: relationship, last contact, open follow-ups. PROJECT: status, next action.
  PURSUIT: current milestone, next milestone.*

- [ ] **3.4** Implement `/remind` command  
  *Query ADMIN pages with `status: Pending` and `due_date <= today + 48h`. Return formatted
  list to Telegram. Use a Dataview-equivalent frontmatter scan.*

- [ ] **3.5** Configure n8n Chat Trigger as secondary retrieval interface  
  *Does NOT route through Hermes for Read operations. n8n Chat Trigger connects directly
  to Gemini (`gemini-3.5-flash`) with the wiki repo accessible as context. Much simpler
  than going through the Telegram → Hermes path. Possible future direction: an embedded
  Android app fronting the same n8n Chat workflow. Create/Update operations on the wiki
  may route through Hermes; Read operations go direct.*  
  **Depends on:** Nothing (independent of 3.1–3.4)

---

## Phase 4 — Scheduled Reports
**Status:** Daily Digest live; remaining reports not started

- [x] **4.1** Daily Digest *(live as of 2026-05-19 with Google Calendar block)*  
  *Cron `claude -p` reads log.md (yesterday's entries) + ADMIN pages (due within 48h,
  overdue) + PERSON pages (follow-up due) + Google Calendar block. Composes and sends
  digest. Currently runs `claude -p` (~31k tokens overhead per run); swap to direct
  `gemini-3.5-flash` is a Decide-gate candidate.*

- [ ] **4.2** Serendipity Engine (n8n cron, 7:05 AM, opt-in)  
  *Reads log.md for yesterday's IDEAs, picks one as anchor, selects 3 semantically
  adjacent pages from across the wiki, generates unexpected connection, sends to Telegram.
  Files substantial connections back as new IDEA pages.*

- [ ] **4.3** Weekly Summary (n8n cron, Sunday 6:00 PM)  
  *Week's captures by bucket, active PROJECT next actions, ADMIN due next week,
  1–2 LLM-observed patterns from the week.*

- [ ] **4.4** Idea Synthesis Report (n8n cron, Sunday 6:05 PM)  
  *This week's IDEA pages cross-referenced against the full wiki. Ranked connections with
  reasoning. Filed as synthesis page. Candidate for `gemini-3.1-pro-preview` escalation.*  
  **Depends on:** 4.3

- [ ] **4.5** Monthly Trend Report (n8n cron, 1st of month 8:00 AM)  
  *Topic clusters, recurring themes, IDEAs stale >30 days, inactive projects, emerging
  clusters. Filed as report page. Delivered via Telegram.*  
  **Depends on:** 4.4

---

## Phase 5 — Extended Ingestion Sources
**Status:** Not started — additive sources beyond Telegram

- [ ] **5.1** Email ingestion via forwarding address  
  *Dedicated ingestion address on PurelyMail (e.g., `mneme@...`). n8n IMAP trigger watches
  the mailbox. Normalize email body + attachments to IngestItem.*

- [ ] **5.2** Email ingestion via Gmail label  
  *n8n Gmail trigger watching label `Mneme/Inbox`. Useful for newsletters (likely REFERENCE
  bucket) and research emails.*  
  **Depends on:** 5.1

- [ ] **5.3** URL / link capture via Telegram  
  *n8n detects URLs in Telegram messages. Fetches page content (Jina Reader API or
  equivalent → clean markdown). Routes to standard ingest → typically REFERENCE bucket.*

- [ ] **5.4** Obsidian Web Clipper → wiki inbox processing  
  *Web Clipper saves to `wiki/inbox/`. n8n scheduled trigger (every 30 min) or on-demand
  Telegram command processes contents: classify each file, integrate into wiki, move to
  `wiki/raw-sources/`.*

---

## Phase 6 — Bulk Import
**Status:** Not started

- [ ] **6.1** Google Keep bulk import  
  *n8n scheduled workflow via Google Keep API. For each note: normalize to IngestItem,
  run through standard ingest pipeline, mark as migrated. Supervised mode first.*

- [ ] **6.2** Google Drive selective import  
  *One-time + periodic delta sync. PDFs → text extraction. Docs → Google Docs API pull.
  Selective, not bulk — curate what is worth ingesting.*  
  **Depends on:** 5.3 (URL handling pattern)

---

## Phase 7 — Maintenance Workflows
**Status:** Partial — 12 standalone check scripts already exist in
`infrastructure/mnemosyne/scripts/maintenance/`. Remaining work is wiring them into a
scheduled Lint report and a fix-and-stub-create execution loop.

### Built — standalone scripts (`scripts/maintenance/`)

| Script | Covers |
|--------|--------|
| `check-ghost-links` | Broken wikilinks (referenced but no page exists) |
| `check-orphan-files` | Pages with no inbound wikilinks |
| `check-stub-pages` | Pages with negligible content |
| `check-person-followups` | PERSON pages with overdue follow-ups |
| `check-overdue-tasks` | ADMIN pages past `due_date` |
| `triage-stale-projects` | PROJECT/PURSUIT pages with no activity 90+ days |
| `check-index-completeness` | Pages on disk but missing from `index.md` |
| `check-log-coverage` | Activity gaps in `log.md` |
| `check-updated-drift` | Frontmatter `updated` vs. last git-touch divergence |
| `check-frontmatter-types` | Schema violations across bucket frontmatter |
| `check-inbox-drain` | `wiki/inbox/` items not yet processed |
| `audit-required-fields` | Missing required frontmatter per bucket type |

### Remaining work

- [ ] **7.1** Wire scripts into a scheduled Lint report (n8n cron, Sunday before Weekly
  Summary, or on-demand `/lint`)  
  *Run all `check-*` and `audit-*` scripts; collate output; render a single health report;
  send to Telegram. Surface counts + worst N items per category.*  
  **Depends on:** Phase 4 cadence established

- [ ] **7.2** Build the fix-and-stub-create execution loop  
  *On user confirmation from the 7.1 report: Hermes (or interim `claude -p`) creates stub
  pages for ghost links, repairs broken links where target is unambiguous, prompts user for
  ambiguous cases. The check scripts already identify the issues; this phase is the
  remediation loop.*  
  **Depends on:** 7.1

- [ ] **7.3** Periodic entity consolidation  
  *Scans PERSON/PROJECT/PURSUIT pages for likely duplicates (near-identical names or
  summaries). Presents candidates to user via Telegram with merge/rename/keep options.
  Runs Sunday before Weekly Summary, after Lint.*  
  **Depends on:** 7.1, 7.2

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

## Path Map

There is no single linear critical path. Two ingest paths run in parallel today; the
Decide gate chooses where to invest next.

```
Phase 0 (Design) ──┐
                   │
Phase 1 ──────────┤
                   │
                   ├─► Phase 2 (Interim — complete) ─► Phase 4 Daily Digest (live)
                   │                                              │
                   │                                              ▼
                   │   ┌── Phase 4.2–4.5 reports (open)
                   │   │
                   └──►├── Phase 2T (target — Decide candidate)
                       │
                       ├── Phase 3 (retrieval — buildable now)
                       │
                       └── Phase 5/6/7 (additive)
```

The 2026-06-01 Decide gate selects the next sprint from a candidate set that spans
multiple of these branches; sprints are picked one at a time.

---

*For Hermes requirements and status: see `apps/hermes/ToDo.md`*  
*For full system design: see `docs/mnemosyne-design-doc-v1.1.md`*  
*For the orientation rationale: see `[[2026-05-20 — Hermes Off Hold and Orient Inventory]]`*
