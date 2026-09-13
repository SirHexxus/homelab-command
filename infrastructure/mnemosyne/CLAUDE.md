# Mnemosyne

**Claude's role in this directory: Project Manager for the Mnemosyne knowledge pipeline.**
The capture path runs today via two routes: Claude Code direct (`/mneme`, `/mneme-ask`)
and an interim n8n cron pipeline (Telegram → n8n → inbox-receiver → `claude -p` sweep →
wiki). The Hermes-routed target path (Phase 2T, now via Chiron/Hermes-Agent) is re-queued to
the 2026-09-01 gate — the 2026-06-01 gate was superseded by the Chiron migration (D1/AUD-011).
Hermes wiki skills are complete; what remains is the target-path migration, Telegram
retrieval, and the remaining scheduled reports. For the wiki skills themselves, see
`apps/hermes/CLAUDE.md`.

Read `infrastructure/mnemosyne/ToDo.md` for the current task backlog. Do not build pipeline
components not in the backlog without checking first.

See `docs/homelab-philosophy.md` for the values and principles behind all homelab decisions.

## Architecture (Current)

Mnemosyne is not a standalone host. It is a pipeline layer across shared infrastructure.

| Component | Host | Status |
|-----------|------|--------|
| Wiki repo (git) | Cloned on Hermes LXC (10.0.50.17) | Operational |
| Hermes wiki skills | `apps/hermes/lib/skills/wiki.py` | Complete — Phase 2 done |
| n8n ingestion pipelines | n8n LXC (10.0.50.13) | Operational (interim path); Phase 2T pending |
| Telegram ingestion bot | n8n Telegram Trigger | Operational |
| Scheduled reports | cron / n8n | Daily Digest live; Phase 4.2–4.5 planned |
| Maintenance scripts | `infrastructure/mnemosyne/scripts/maintenance/` | 12 standalone scripts built; wiring into Lint pending |

The wiki is a flat-file Markdown repo (`~/mneme/wiki/`), governed by `SCHEMA.md`. Obsidian
is the UI layer. Hermes reads and writes via git. There is no Postgres schema, no pgvector
dependency, and no MinIO dependency in the current design.

## Definition of Done

- Telegram bot wired to n8n ingestion workflow (capture → classify → file to wiki → commit)
  — **Done in shape, different in flow.** Workflow is now: capture → inbox → commit →
  classify & create stub → enrich stubs. Functionally satisfies the criterion.
- n8n pipelines operational: `/mneme` capture, `/mneme-ask` retrieval, scheduled Daily Digest
  — **Operational via `claude -p` workaround.** All three are functioning today; the
  workaround will be replaced as Phase 2T and the Daily Digest LLM swap land.
- Hermes retrieval confirmed end-to-end: Telegram query → wiki read → response
  — **Still pending.** Phase 3 work; buildable now that Hermes is off hold.

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
  ansible/
    ansible.cfg              ← roles_path = roles:../../ansible/roles
    inventory.ini            ← [mneme_workers] 10.0.50.19 (inbox-receiver LXC 103)
    provision.yml            ← deploys the mneme-* script tree + systemd timers/services
    roles/mneme_workers/     ← source of truth for the worker fleet (units templated
                               from defaults/main.yml: mneme-worker.timer/.service,
                               mneme-watch-inbox.service, mneme-alert@.service)
  terraform/   ← placeholder (.gitkeep) — no dedicated Proxmox resource
```

The worker fleet runs on the inbox-receiver LXC (103); the inbox-receiver Flask app itself is
provisioned separately from `inbox-receiver/ansible/provision.yml`. Terraform for LXC 103 also
lives under `inbox-receiver/`. The wiki is a git repo on the Hermes LXC — no IaC of its own.

```bash
cd infrastructure/mnemosyne/ansible
ansible-playbook -i inventory.ini provision.yml
# Also remove mneme-* units the role no longer declares:
ansible-playbook -i inventory.ini provision.yml -e mneme_purge_unmanaged=true
```

## Vault Variables

- `vault_mnemosyne_password` — exists in postgres group_vars; not used in current architecture

## Notes

- The old pgvector/Postgres design is retired — do not reference or build against it
- `lib/skills/mneme.py` (the old Postgres skill) is archived to `apps/hermes/lib/skills/_archive/`
- **Read-direct, Write-through-Hermes pattern.** Not all wiki interactions need to route
  through Hermes. Read operations may go direct to Gemini (e.g., the planned n8n Chat
  Trigger interface, ToDo 3.5); Create/Update operations route through Hermes for schema
  + index + log + git governance. See `THOUGHTS.md` "The Read Path: Direct LLM vs.
  Hermes-Routed".
- **Maintenance scripts** at `scripts/maintenance/` already implement most Phase 7.1
  checks (ghost links, orphan files, stub pages, overdue tasks, stale projects, etc.).
  See `ToDo.md` Phase 7 for the inventory and remaining wiring work.
- Design doc: `docs/mnemosyne-design-doc.md`
- IaC conventions: see root `CLAUDE.md`
