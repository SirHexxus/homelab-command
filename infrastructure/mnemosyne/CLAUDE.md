# Mnemosyne

Personal knowledge management system — captures, classifies, embeds, and retrieves information
across 7 semantic buckets (IDEA, ADMIN, REFERENCE, JOURNAL, PERSON, PROJECT, PURSUIT).
Designed to reduce ADHD executive function failures by making capture frictionless and
retrieval semantic. No dedicated host — lives in the shared Postgres instance.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| `mnemosyne` DB | Database on Postgres LXC | 105 | 10.0.50.14 | 5432 | 50 | Schema planned — Phase 2 |
| n8n pipelines | Workflows on n8n LXC | 107 | 10.0.50.13 | 5678 | 50 | Planned — Phase 2 |
| MinIO objects | Object storage | 108 | 10.0.50.16 | 9000 | 50 | Ready (platform deployed) |
| Hermes skill | App module on Hermes LXC | 110 | 10.0.50.17 | — | 50 | Planned |

Mnemosyne is not a standalone host — it is a schema + pipeline + retrieval layer across
shared platform infrastructure.

## Role in Stack

**Depends on:**
- `platform/postgres` — primary store: pgvector embeddings, entity records, 7 bucket tables
- `platform/n8n` — ingestion pipelines (classify → embed → route → store)
- `platform/redis` — caching and session management
- `platform/minio` — object storage for voice memos and file attachments
- `platform/ollama` — embedding generation (nomic-embed-text model)
- Notion — UI layer for structured views (external dependency)
- Telegram — ingestion endpoint and retrieval bot (external dependency)

**Depended on by:**
- `hermes` — Mnemosyne Postgres is Hermes's persistent memory store
- `argus` — incidents stored as Mnemosyne JOURNAL/REFERENCE entries

## IaC Layout

```
infrastructure/mnemosyne/
  ansible/     ← placeholder (.gitkeep) — not yet written
  terraform/   ← placeholder (.gitkeep) — not yet written
```

No IaC written yet. Both are empty placeholders.
Mnemosyne IaC will consist of Ansible tasks to apply schema migrations to the shared
Postgres instance — not a new LXC.

## Vault Variables

Mnemosyne uses the shared Postgres instance:
- `vault_mnemosyne_password` — already exists in postgres group_vars

## Design Doc

`docs/mnemosyne-design-doc-v1.1.md` — full bucket definitions, data schema (pgvector tables,
entity reconciliation), n8n ingestion pipeline design, Telegram bot retrieval, scheduled
reports.

## Notes

- Mnemosyne has no dedicated Proxmox resource — it is schema + workflows on shared infra
- The `argus_logs` database co-exists on the same Postgres LXC (TimescaleDB hypertables)
- pgvector, pg_trgm, fuzzystrmatch extensions required on the `mnemosyne` DB
- IDEA vs. REFERENCE classification is the highest-ambiguity boundary — AI classifier should
  ask for confirmation when confidence is below threshold at this specific boundary
- See root `CLAUDE.md` for IaC conventions
