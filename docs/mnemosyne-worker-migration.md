# Mnemosyne Worker Migration
**Version:** 1.0
**Last Updated:** July 2026
**Status:** Draft — pending James's approval of the LLM-engine decision (§5) and slice 1 go-ahead

---

## 1. Purpose

Move all scripted Mnemosyne pipeline logic off the laptop and onto homelab infrastructure, per the architecture directive of 2026-07-10: **deterministic materialization lives in n8n; judgment and wiki writes live on an LXC; the laptop becomes an Obsidian editing surface only.**

The laptop currently runs 18 Mnemosyne cron entries. It is treated as a desktop and doesn't sleep, so the pipeline works — but pipeline availability is coupled to a personal machine, logs live in flat files under `~/mneme/`, and the arrangement contradicts both the homelab philosophy (services live on the platform) and the Mnemosyne productization intent (the engine must not assume its operator's laptop).

Lineage: this doc operationalizes the decision recorded in the wiki ADMIN task *Rebuild Payload-Shape-Aware Triage in n8n for Deterministic Inputs* (now Active) and continues the split ratified in *N8n for Document Text Extraction*. The n8n half is already shipping — photo OCR, album aggregation, and the audio route went live 2026-07-11.

## 2. Current State

### Laptop crontab (the migration surface)

| Schedule | Script | LLM | Other dependencies |
|---|---|---|---|
| hourly | `triage-inbox` | claude CLI (haiku/sonnet) | Postgres, MinIO, yt-dlp dispatch, ntfy |
| every 3 h | `enrich-stubs` | claude CLI | Postgres, Ollama embeddings, ntfy |
| daily 07:00 | `daily-digest` | claude CLI + `llm_client` (Vertex) | Postgres, gcal token, Ollama, ntfy |
| daily 06:55 | `embed-wiki` | — | Ollama (10.0.50.10), Postgres pgvector |
| :05/:35 hourly | `render-log` | — | Postgres (`mneme_log`) |
| daily 06:50 | `maintenance/sweep-closed-tasks --apply` | — | Postgres |
| daily 07:00 ×5 | `maintenance/check-*` (ghost-links, index, overdue, followups, inbox-drain) | optional haiku | — |
| weekly ×7 | `maintenance/check-*` / `audit-*` / `triage-stale-projects` | optional haiku/sonnet | — |
| every 30 min | `hermes/scripts/edge-health-probe` | — | **stays on laptop by design** (cross-VLAN probe) |

Not in cron but part of the family: `watch-inbox` (inotify daemon for near-real-time triage), `extract-video-transcript` (yt-dlp + ffmpeg + Whisper), `extract-image-data` (Vertex OCR; photo path now superseded by n8n, `--work-schedule` calendar flow still script-side), `extract-keep-note` / `triage-keep-batch` (Keep backfill), `semantic-search` (interactive, used by `/mneme-ask`), `archive-wiki`, `set-task-status`, `build-catalog`, `normalize-tags`, `prune-index`, `build-schema`, `render-digest-voice`, `gcal-authorize`.

### Dataflow today

Telegram/email → n8n (materialize: download, MinIO, OCR, transcribe) → Ingest Core (Redis dedup) → inbox-receiver (LXC 103) → commit JSON to `wiki/inbox/` → push to GitHub → **laptop** pulls, triage classifies + writes stubs, enrich fills pages, digest/maintenance run on cron → push.

### Existing seams that make this migration cheap

- **Config**: scripts read `~/.config/mnemosyne/{vertex-creds,pg-creds,gemini-creds}.json` with `MNEME_PG_*` and `MNEME_WIKI_PATH` env overrides. Nothing is hardcoded to the laptop except the crontab itself.
- **Wiki path**: resolved via the `infrastructure/mnemosyne/wiki` symlink (or `MNEME_WIKI_PATH`).
- **Wiki clone with push credentials already exists on LXC 103** at `/opt/inbox-receiver/wiki` (inbox-receiver commits and pushes today).
- **`lib/llm_client.py`** already provides the Vertex path (google-genai, SA JSON), used by `extract-image-data` and `daily-digest`.

## 3. Target Architecture

| Layer | Host | Owns |
|---|---|---|
| Materialization | n8n (LXC 107) | Download, MinIO upload, image OCR/description (Vertex), PDF/text extraction, Whisper transcription, album aggregation, Redis dedup |
| URL/article extraction | Firecrawl on Hephaestus (10.0.50.30:3002) | Fetch + markdown-ify article URLs (wire into triage's URL handler; replaces bespoke readability scripts) |
| Judgment + wiki writes | **Mnemosyne worker = LXC 103** (co-located with inbox-receiver) | triage, enrich, digest, embeddings refresh, maintenance checks, log render, archive |
| Editing surface | Laptop | Obsidian + git auto-sync; interactive scripts remain runnable here (shared-scripts principle) |

Why LXC 103: the wiki clone and push credentials are already there; intake and processing co-locate (triage can watch the clone via `watch-inbox` and run seconds after inbox-receiver commits — no polling, no GitHub round-trip wait); Chiron's blast radius stays separate per the autonomous-action boundaries.

**The scripts are not forked.** The same `infrastructure/mnemosyne/scripts/` tree runs on the worker (via a homelab-command clone) and stays runnable on the laptop for interactive use (`semantic-search`, `set-task-status`, manual extracts). Only the *cron ownership* moves.

## 4. Script Disposition

| Disposition | Scripts |
|---|---|
| **Move to worker (cron/timer)** | `triage-inbox`, `watch-inbox`, `enrich-stubs`, `daily-digest`, `embed-wiki`, `render-log`, `render-digest-voice`, all 13 `maintenance/*` |
| **Runnable everywhere, no timer** | `semantic-search`, `set-task-status`, `archive-wiki`, `normalize-tags`, `prune-index`, `build-catalog`, `build-schema`, `extract-video-transcript`, `extract-image-data --work-schedule` |
| **Dissolved into n8n (done)** | photo OCR path of `extract-image-data`, per-message transcription dispatch, PDF text extraction |
| **Stays on laptop** | `edge-health-probe` (cross-VLAN by design), `gcal-authorize` (interactive OAuth bootstrap; token is then deployed to the worker) |
| **Backfill tools (leave until needed)** | `extract-keep-note`, `triage-keep-batch` |

yt-dlp placement: stays a worker-LXC dependency (apt/pip package + ffmpeg), invoked by `triage-inbox` → `extract-video-transcript` exactly as today. A Hephaestus yt-dlp microservice is not justified — the worker is the only consumer, and the subprocess call is the existing, tested shape.

## 5. The LLM Engine Decision (blocker for slice 1)

`triage-inbox`, `enrich-stubs`, and the `--enrich` maintenance checks shell out to `claude -p` (haiku/sonnet pinned in `lib/wiki-common.sh`), which today rides the laptop's Claude Code auth.

| Option | How | Pros | Cons |
|---|---|---|---|
| **A — Port to `lib/llm_client.py` (Vertex)** ✅ recommended | Add a `call_text`-based classify/enrich path; models `gemini-2.5-flash` / `flash-lite` | Keyless SA file (already a solved deploy: same pattern as n8n/Chiron); credit-covered through 2027-05; no personal-subscription dependency (productization seam); consistent with `extract-image-data` and `daily-digest` precedent | Prompt behavior must be re-validated; classification quality vs. Claude unproven |
| B — claude CLI on the worker | `claude setup-token` long-lived OAuth, or `ANTHROPIC_API_KEY` in vault | Zero prompt changes; known-good classification | Ties the pipeline to James's personal Claude auth (or adds per-token API spend); another auth artifact to rotate; contradicts the engine/instance seam |

**Recommendation: A**, with a validation gate — before cutover, run both engines against the same ~20 historical inbox items and diff bucket assignments + stub quality. If Vertex misclassifies materially, fall back to B for triage only and revisit.

## 6. Worker Design (LXC 103)

- **Layout**: `/opt/mnemosyne/homelab-command` — read-only deploy-key clone (same pattern as Chiron S0.2); `infrastructure/mnemosyne/wiki` symlink → `/opt/inbox-receiver/wiki`. Updates = `git pull` (Ansible-managed).
- **Config**: `/root/.config/mnemosyne/{vertex-creds,pg-creds}.json` (0600) templated from vault; gcal token copied from laptop after `gcal-authorize` runs. New vault vars (convention-checked): `vault_mnemosyne_worker_deploy_key`, reuse `vault_chiron_vertex_sa_json`-style SA var or mint `vault_mnemosyne_vertex_sa_json` — **decide at implementation; do not reuse the n8n SA** (per-consumer revocation).
- **Scheduling**: systemd timers, not cron — one `timer`+`service` pair per entry, templated by Ansible from a schedule map mirroring §2. Every service gets `OnFailure=mneme-alert@%n.service` → ntfy (Iris, 10.0.10.25) so failures are loud, replacing `>> ~/mneme/*.log` with journald.
- **IaC home**: `infrastructure/mnemosyne/ansible/` (currently a placeholder) — new role `mnemosyne_worker`, playbook targeting LXC 103; `roles_path` per the 2-level convention. inbox-receiver's existing role is untouched.
- **Sizing check before slice 1**: LXC 103 is currently sized for a tiny Flask app. Whisper calls are remote, but yt-dlp + ffmpeg need disk and a CPU burst; bump to ≥2 vCPU / 2 GB / 20 GB in Terraform if below.

## 7. Sync-Race Discipline

Three writers touch the wiki repo: inbox-receiver (LXC 103), the worker scripts (LXC 103), and Obsidian Git auto-sync (laptop). Rules, all already practiced, now codified:

1. Every automated writer commits *only its own files* and runs `git pull --rebase --autostash` immediately before `push` (inbox-receiver already does; `wiki-common.sh` gains a shared `wiki_commit_push` helper so triage/enrich do identically).
2. Retry once on push rejection; on second failure, alert via ntfy and leave the commit local — never force-push, never reset.
3. Distinct-file collisions are the norm (inbox JSONs, stubs, index.md is the hotspot); index.md conflicts resolve by re-running the writer after pull, not by hand-merging.
4. Worker and inbox-receiver share one clone and one process boundary each — no concurrent triage runs (`flock` guard in `triage-inbox`, already present via lock file — verify at implementation).

## 8. Cutover Plan

| Slice | Content | Gate |
|---|---|---|
| **1** | `triage-inbox` + `watch-inbox` on worker; laptop triage cron disabled (commented, kept) | LLM engine decision (§5) + validation gate; then 1 week of clean runs |
| **2** | `enrich-stubs`, `render-log`, `sweep-closed-tasks`, all maintenance timers | Slice 1 stable |
| **3** | `daily-digest`, `embed-wiki`, `render-digest-voice` (gcal token + TTS deps move) | Slice 2 stable |
| **4** | Laptop crontab reduced to `edge-health-probe` only; doc bumped to Accepted | Slice 3 stable |

**Rollback (any slice)**: `systemctl disable --now` the worker timers, uncomment the laptop cron lines. Both sides idempotent against the same repo, so rollback is minutes, not surgery.

### Slice 1 verification (from the plan of record)

Telegram note → n8n → inbox-receiver → worker triage fires (watch-inbox, no cron wait) → stub committed and pushed from LXC 103 → appears on laptop via pull → `mneme_log` row written → laptop triage cron confirmed disabled → a deliberately malformed inbox item produces an ntfy alert, not silence.

## 9. Open Questions for James

1. **LLM engine**: accept recommendation A (Vertex port with validation gate), or keep claude CLI via setup-token (B)?
2. **Vertex SA**: mint `vertex-mnemosyne` SA (recommended, per-consumer revocation) or reuse an existing one?
3. **Timing**: slice 1 before or after the summer trip (productivity blackout July 25–Aug 12)? Slices mid-flight during the blackout are the one thing this plan should avoid.

---

*Related: `docs/mnemosyne-design-doc-v1.1.md` (system design), wiki pages [[Payload-Shape-Aware Triage and URL-Resolving Raw Enrichment]], [[N8n for Document Text Extraction]], [[Rebuild Payload-Shape-Aware Triage in n8n for Deterministic Inputs]] (Active), journal [[2026-07-11 — n8n Review Fixes, Photo OCR Pipeline, and Sales Pipeline MVP]].*
