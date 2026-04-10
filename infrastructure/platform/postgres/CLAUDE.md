# Postgres

Shared database LXC — hosts all structured data for the homelab: Mnemosyne knowledge base
(pgvector + pg_trgm), Argus security logs (TimescaleDB hypertables), n8n workflow state,
and Umami analytics.

## Components

| Name | Type | VMID | IP | Port | VLAN | Status |
|------|------|------|----|------|------|--------|
| Postgres LXC | LXC | 105 | 10.0.50.14 | 5432 | 50 | Deployed |

**Extensions:** pgvector, TimescaleDB, pg_cron, pg_trgm, fuzzystrmatch

## Databases Hosted

| Database | Owner | Purpose |
|----------|-------|---------|
| `mnemosyne` | Mnemosyne | Knowledge base — pgvector embeddings, 7 bucket tables |
| `argus_logs` | Argus | Security event log store — TimescaleDB hypertables |
| `n8n` | n8n | Workflow state and execution history |
| `umami` | Umami | Web analytics for Ariadne-proxied services |

## Role in Stack

**Depends on:**
- Nothing — foundational data layer

**Depended on by:**
- `mnemosyne` — primary knowledge store
- `argus` — `argus_logs` TimescaleDB for security events
- `platform/n8n` — workflow state
- `ariadne` (Umami) — analytics data

## IaC Layout

```
infrastructure/platform/postgres/
  ansible/
    inventory.ini
    ansible.cfg        ← roles_path: roles:../../../ansible/roles
    group_vars/
      all.yml
      vault.yml
    provision.yml
  terraform/           ← .gitkeep only (no Terraform for this service)
```

## Vault Variables

- `vault_mnemosyne_password` — mnemosyne DB user
- `vault_argus_password` — argus_logs DB user
- `vault_umami_password` — umami DB user
- `vault_n8n_password` — n8n DB user

## Notes

- No Terraform for this service — LXC was provisioned manually; only Ansible manages it
- `roles_path` is 3-level: `roles:../../../ansible/roles`
- Do NOT drop or alter the `argus_logs` or `mnemosyne` databases without explicit direction
- See root `CLAUDE.md` for IaC conventions
