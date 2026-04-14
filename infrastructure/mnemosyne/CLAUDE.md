# Mnemosyne

**Claude's role in this directory: Project Manager for the Mnemosyne knowledge pipeline.**
The deliverable is a fully operational capture-to-retrieval pipeline: Telegram ingestion →
n8n classification → git wiki storage → Hermes retrieval. The Hermes wiki skills that read
and write the wiki are complete — what remains is the n8n pipeline and Telegram bot wiring.
For the wiki skills themselves, see `apps/hermes/CLAUDE.md`.

Read `infrastructure/mnemosyne/ToDo.md` for the current task backlog. Do not build pipeline
components not in the backlog without checking first.

See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.

## Architecture (Current)

Mnemosyne is not a standalone host. It is a pipeline layer across shared infrastructure.

| Component | Host | Status |
|-----------|------|--------|
| Wiki repo (git) | Cloned on Hermes LXC (10.0.50.17) | Operational |
| Hermes wiki skills | `apps/hermes/lib/skills/wiki/` | Complete — Phase 2 done |
| n8n ingestion pipelines | n8n LXC (10.0.50.13) | Planned |
| Telegram ingestion bot | External | Planned |
| Scheduled reports | n8n LXC | Planned |

The wiki is a flat-file Markdown repo (`~/mneme/wiki/`), governed by `SCHEMA.md`. Obsidian
is the UI layer. Hermes reads and writes via git. There is no Postgres schema, no pgvector
dependency, and no MinIO dependency in the current design.

## Definition of Done

- Telegram bot wired to n8n ingestion workflow (capture → classify → file to wiki → commit)
- n8n pipelines operational: `/mneme` capture, `/mneme-ask` retrieval, scheduled Daily Digest
- Hermes retrieval confirmed end-to-end: Telegram query → wiki read → response

## Role in Stack

**Depends on:**
- `platform/n8n` — ingestion and report pipelines
- `platform/redis` — session state for Telegram bot clarification flow
- `hermes` — wiki read/write skills and ReAct retrieval loop
- Telegram — ingestion endpoint (external)

**Depended on by:**
- `hermes` — Mnemosyne wiki is Hermes's persistent memory store
- `argus` — incidents stored as JOURNAL/REFERENCE entries

## IaC Layout

```
infrastructure/mnemosyne/
  ansible/     ← placeholder (.gitkeep) — not yet written
  terraform/   ← placeholder (.gitkeep) — not yet written
```

No IaC written. No dedicated Proxmox resource — the wiki is a git repo on the Hermes LXC.
Mnemosyne IaC, when written, will consist of Ansible tasks for n8n pipeline deployment.

## Vault Variables

- `vault_mnemosyne_password` — exists in postgres group_vars; not used in current architecture

## Notes

- The old pgvector/Postgres design is retired — do not reference or build against it
- `lib/skills/mneme.py` (the old Postgres skill) is archived to `apps/hermes/lib/skills/_archive/`
- Design doc: `docs/mnemosyne-design-doc-v1.1.md`
- IaC conventions: see root `CLAUDE.md`
