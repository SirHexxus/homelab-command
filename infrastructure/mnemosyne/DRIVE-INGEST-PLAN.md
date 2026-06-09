# Drive → Mneme Ingestion Plan (phased, usage-throttled)

**Status:** Planning — no ingestion started. Mirror inspected & cleaned 2026-06-08.
**Author:** Claude (custodian) for James.
**Related:** `LAYER-3-PICKUP.md`, `scripts/EMBEDDINGS-SETUP.md`, the Keep import
(homelab-command 73b07af), memory `project_google_media_migration`.

## Context

The Google Drive baseline mirror lives at `~/mneme/drive-baseline/{jamesmichaelstacy,piperofthewinds}/`
(sibling to the vault, **not** in the git-synced wiki). Photos and Keep are already
migrated. Drive is the last workstream. James wants the *contents* selectively ingested
into Mneme — **but the enrichment pipeline is the bottleneck**, and he is still working
through the Keep backlog. The goal of this plan is a **paced, priority-ordered** ingestion
that never spikes Claude usage: small waves, drained by `enrich-stubs` between releases,
with spreadsheets and published material kept out of the synthesis path entirely.

### The usage problem (why pacing is mandatory)

`enrich-stubs` (scripts/enrich-stubs, Sonnet `claude-sonnet-4-6`, 6h cron) finds **all**
`[STUB]` lines in `index.md` and enriches **every one** per run — there is no per-run cap.
- Current pending backlog: **93 stubs** (Keep import, down from 278).
- Drive own-docs to ingest: **198 files**.
- Dumping all 198 as stubs → the next 6h run attempts ~291 Sonnet syntheses in one burst.

**Two levers fix this** and are both part of this plan:
1. **Cap `enrich-stubs` per run** (structural; protects usage regardless of queue depth).
2. **Release Drive work in priority waves** (control + highest-value-first ordering).

---

## The map — what's actually in the mirror

Mirror is **2.7 GB / 1,897 files** after Tier-1 cleanup (LeftCoastScales + piper/Work Stuff
dupe deleted; 15 ebooks moved to `~/media/ebooks/`). Categorized:

### IN — James's own writing (synthesis ingest) — **129 files** (after content audit)
The 198 own-docs were content-audited file-by-file (`/tmp/drive-doc-verdicts.md`, built by
`/tmp/drive-doc-preview` + `/tmp/drive-doc-verdicts`; previews via pandoc/pdftotext). Verdicts:
- **KEEP 129** — the actual synthesis load. Resumes flagged as a cluster to consolidate.
- **LIBRARY-ref 6** + **LIBRARY-tmpl 17** — go to the Library tier (below), not the waves.
- **MERGE 5** — the `Agent …` NPC files consolidate into one **Department 14 campaign page**
  (they're the PC handlers); not separate stubs.
- **REVIEW 11** — `.odp` slideshows (need conversion), LLM-response scraps, ambiguous items —
  James eyeballs before they're keep/drop.
- **DROP 30** — 25 exact duplicate copies (canonical kept elsewhere) + 5 genuinely empty
  (phone-number stub, blank court notes, transient shopping lists). **Nothing of value dropped.**

Audit principle (James, reinforced 3×): **default to keep / library, not drop** — published
≠ junk, templates ≠ junk; when unsure, shelve it, don't trash it.

### DEFER — spreadsheets / tabular data — **94 files** (`.ods` / `.csv`)
Finances, People "CRM", gas/grocery/cost trackers, equipment price sheets. Tabular data makes
noisy prose; James chose **defer** → a dedicated later data session (possibly register as
REFERENCE stubs with `file_ref` only, no synthesis).

### LIBRARY — long-form references & reusable templates (NOT dropped, NOT bulk-synthesized)
A first-class tier between "synthesized wiki page" and "deleted," for material that's valuable
but shouldn't be flattened into prose. Two shelves:

- **Reference shelf** — long-form knowledge mined on demand: the published RPG rulebooks
  (`Fate-Core` 136K, `Lost Laboratory of Kwalish` 259K, `Star-Wars-Fate-Edition`), the SCA
  `Book of Ceremonies`, `Essay_Writing_Guide`, the **Mead Book** (brewing/mazery pursuit — James
  explicitly wants this), the `~108` published PDFs (`Computer Science` Arduino/Python books,
  `Gaming` rulebooks), the ebooks already in `~/media/ebooks/`, the `N8N Workflow Vault` (mine
  for workflow ideas), and `rom_list.txt` (retro-ROM archive inventory).
- **Template shelf** — reusable boilerplate James fills out (all 17 `LIBRARY-tmpl`): SOW,
  contractor agreement, invoice, data-collection form, SCA court templates, etc.

**Architecture (James's design):**
- **Storage:** MinIO (already the `file_ref` backend) holds the whole files — `library/reference/…`
  and `library/templates/…` prefixes. Ebooks in `~/media` sync here too.
- **Mining on demand:** the **pgvector embeddings sidecar** (`scripts/EMBEDDINGS-SETUP.md`)
  indexes the reference shelf so a task can semantically retrieve the relevant chunk and pull it
  into the page being written (the sibling raw-source hand-off pattern already exists).
- **Lifecycle:** each item carries a state — `active` (indexed, mineable) → `exhausted` (fully
  mined / stale) → `archived` (dropped from the index, cold in MinIO, still retrievable). A
  `library_state:` frontmatter field on a thin index card per item tracks this.
- **Wiki linkage:** pursuit/idea pages reference library items by `file_ref`; mining writes
  excerpts into the consuming page, not a standalone synthesized page.

This subsumes the earlier "`~/media`, no synthesis" idea into one tiered system. **Build it in**
(James approved full design). PDF detection for the reference shelf: large/multi-chapter
`pdftotext` yield or clearly a third-party title; borderline short personal PDFs ride along as
own-docs instead.

### OUT (media) — images / transient — **~150 files**
- `jms/Archive/Marketplace-Equipment-Sale/` — 117 Amazon screenshots + equipment photos for a
  marketplace sale → transient, **skip** (keep on disk or delete later; the price-sheet `.ods`
  is the only keeper, and it's a deferred spreadsheet).
- `logos/` (3 png), scattered `.jpg/.png` → skip or route to Immich if they're real photos.

### OUT (sensitive) — flag for James — a handful
Financial / identity scans: `Voided Check.jpg`, `w9-for-indysoft.jpg`, signed contracts
(IndySoft, six_pac recycling), Finance PDFs. **Do not auto-synthesize.** James decides whether
these enter the wiki at all or stay as private file-refs only.

### HELD / DEFERRED — `Work Stuff` (both accounts)
Entire `jms/Work Stuff` deferred by James (incl. the 1.2 GB `LCS Website` WP backup, kept on
disk for now). Revisit as its own phase after the waves below.

---

## Mechanism (reuses the Keep pipeline almost wholesale)

The Keep import already proved the pattern; Drive differs only in **payload extraction**
(Keep had ready-made JSON text; Drive needs text pulled from `.odt`/`.pdf`/etc.).

### New: `scripts/extract-drive-doc` (emitter — mirrors `extract-keep-note`)
Walks a given folder set; for each own-doc file:
1. **Extract plaintext** by shape:
   - `.odt` / `.odp` / `.html` → `pandoc -f odt|html -t plain` (pandoc 3.10 at `~/.local/bin`).
   - `.md` / `.txt` → read directly.
   - `.pdf` (own, not published) → `pdftotext` (poppler 25.03 at `/usr/bin`); if yield is near-zero
     it's scanned → route to the image/OCR pass instead (don't ingest as empty text).
2. **Upload the original** to MinIO `homelab/mnemosyne/google_drive/YYYY/MM/<date>-<slug>-<hash>.<ext>`
   via `mc cp` → set `file_ref` (reuse `upload_minio`, `minio_key`, `slugify` patterns).
3. **Emit an ingestItem** to `inbox/drive-backfill/<hash>.json` — a **new staging subdir**
   that `watch-inbox` (non-recursive inotify) and the `triage-inbox` cron (`glob("*.json")`)
   both ignore, exactly like `inbox/keep-backfill/`. Payload shape identical to the Keep emitter:
   `{raw_content_type, source: "google_drive", text, file_ref, capture_ts, bucket_hint, metadata}`
   with `metadata` carrying `origin: google_drive`, original relative path, account, mtime.
4. Idempotent: hash of (relative-path + content) is the staging filename; re-runs skip emitted.

### New: `scripts/triage-drive-batch` (classifier — clone of `triage-keep-batch`)
Backfill-only, **not** wired to `watch-inbox`. One Haiku (`claude-haiku-4-5-20251001`) call per
`--batch` (default 20) classifies a wave into buckets, deterministic Python writes the stub +
`[STUB]` index line + log line and moves the consumed file to `inbox/drive-backfill/done/`.
Reuses verbatim: `BUCKET_DIR`, `BUCKET_INDEX_HEADER`, `write_stub`, `append_index_stub`,
`append_log`, `raw_source.sanitize_title/safe_target/resolve_wiki_root`. The `--batch`/
`--max-batches` flags are the **wave throttle** — one wave = one bounded run.

### Enum + schema
Add `google_drive` to `SCHEMA.md` source enum and to `VALID_SOURCES` in extract-image-data,
extract-video-transcript, triage-inbox (same one-line edits made for `google_keep`).

### Structural usage cap — `enrich-stubs --max-per-run N`
Add a `--max-per-run` cap (default **25**) that processes at most N `[STUB]` entries per
invocation (oldest-first), then exits leaving the rest for the next 6h run. Wire the flag into
the cron. Effect: **≤25 Sonnet syntheses / 6h ≈ ≤100/day hard ceiling**, regardless of how deep
the queue is. This is the single most important usage protection and also smooths the existing
Keep backlog. (Without it, wave pacing alone is fragile — one accidental big triage run still spikes.)

---

## Phased waves (priority order, ~30–40 docs each)

**Gate:** release a wave only when the pending `[STUB]` count in `index.md` is **< 15**
(`grep -c '\[STUB\]' index.md`). With the per-run cap, each wave drains in ~1–2 days.
Highest-signal first so value lands early even if later waves slip.

- **Wave 0 (prep, no Claude):** build the two scripts + enrich cap; run `extract-drive-doc`
  over the **KEEP set only** (drive the emitter from `/tmp/drive-doc-verdicts.jsonl` — 129 KEEP
  + 5 MERGE ≈ 134; library/template/review/drop excluded) to stage ingestItems into
  `inbox/drive-backfill/` and upload originals to MinIO. Staging is free — nothing becomes a
  stub until `triage-drive-batch` runs.
- **Wave 1 — Personal command center (~39):** `piper/` root loose (31) + `jms/` root loose (8).
  Homelab plans, ADHD/EFD checklists, strategy/brand docs, recipes. Densest signal.
- **Wave 2 — Learning & reference (~43):** jms Learning (26), Reference (7), AI & Automation (7),
  Cheatsheets (3).
- **Wave 3 — Career, projects, people (~41):** jms Career (17), Projects (9), People (6),
  Business (4), Customized Resumes (2), Parenting (2), Philosophy (1).
- **Wave 4 — SCA hobby (~27):** jms SCA (14) + piper SCA (13).
- **Wave 5 — Gaming & creative (~25):** jms Gaming own-docs (22) + piper Gaming (3).
- **Wave 6 — Tail (~12):** Computer Science (1 odt), piper Homebrewery (2), Old Character
  Sheets (3), School Notes (3), Private Notes (1), Writing Stuff (1), + the Department 14
  MERGE page. (Templates moved to the Library tier, not a wave.)

Wave sizes are pre-audit folder counts; the emitter actually pulls only KEEP-verdict files, so
real per-wave counts run a bit lower. After the waves: **Library build-out** (reference +
template shelves), then the **spreadsheet session**, then the **Work Stuff** phase, then
**sensitive scans** review.

---

## Audit follow-up tasks (ADMIN)

- **Template-library review** — once the 17 `LIBRARY-tmpl` files are shelved, create an ADMIN
  task that walks James through **each template one at a time** with a view mechanism (render the
  file / open in MinIO) and captures his per-file verdict: *keep as-is (reason)* / *useful only
  as a format → flesh out into a full template* / *garbage but I need something in this role →
  replace*. The task records his decision + note per file. (James's explicit ask.)
- **Department 14 campaign merge** — consolidate the 5 `Agent …` NPC files (handlers for the PCs)
  plus `Veronica (Vee) Stain` + `Department 14` setting note into one Gaming campaign page.
- **REVIEW queue (11)** — convert the 2 `.odp` slideshows to inspect; James rules on the LLM-scrap
  and ambiguous items before they're keep/drop.

## James's decisions / action items

- **Confirm the per-run enrich cap value** (default 25/run ≈ 100/day). Lower = gentler on usage,
  slower drain.
- **Wave cadence**: manual (you kick off each `triage-drive-batch` wave when ready) vs. a gated
  cron (auto-release next wave when backlog `< 15`). Recommend **manual** at first.
- **Sensitive scans**: in-wiki as private notes, or keep as MinIO file-refs only / out entirely?
- **Marketplace screenshots** (`jms/Archive`, 117 imgs): delete from mirror, or keep on disk?
- Whether to also **add the per-run cap now** to gentle-drain the remaining 93 Keep stubs.

## Verification

1. `extract-drive-doc --dry-run <folder>` lists files + extraction method, uploads nothing.
2. After Wave 0: `ls inbox/drive-backfill/*.json | wc -l` ≈ 198; `mc ls homelab/mnemosyne/google_drive/`
   shows originals; **no** new `[STUB]` lines yet.
3. `triage-drive-batch --dry-run` prints classifications without writing.
4. Per wave: stub count rises by the wave size, then `grep -c '\[STUB\]' index.md` falls ≤25 per
   enrich run; spot-check 2–3 enriched pages resolve their `[[wikilink]]` and `file_ref`.
5. `enrich-stubs --max-per-run 1 --dry-run` (or equivalent) confirms the cap stops after N.
6. Confirm `inbox/drive-backfill/` is invisible to live triage (no watch-inbox firing during Wave 0).
