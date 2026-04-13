# Postgres (Platform)

**Claude's role in this directory: System Administrator.**
This service is deployed and stable. The work here is maintenance and targeted updates —
not new implementation. If a task crosses into schema migrations, new database creation,
or extension upgrades, stop and confirm before proceeding. That is PM scope, not maintenance.

## Current State

LXC 105 at 10.0.50.14:5432, VLAN 50. Deployed. Ansible-managed only — no Terraform (LXC
was provisioned manually).

**Extensions installed:** pgvector, TimescaleDB, pg_cron, pg_trgm, fuzzystrmatch

## Databases

| Database | Owner service | Purpose |
|----------|--------------|---------|
| `mnemosyne` | Mnemosyne | Knowledge base — pgvector embeddings, 7 bucket tables |
| `argus_logs` | Argus | Security event log store — TimescaleDB hypertables |
| `n8n` | n8n | Workflow state and execution history |
| `umami` | Umami | Web analytics for Ariadne-proxied services |

## Role in Stack

**Depends on:** Nothing — foundational data layer

**Depended on by:** Mnemosyne, Argus, n8n, Umami (via Ariadne)

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

## Hard Constraints

- Do not drop or alter `mnemosyne` or `argus_logs` without explicit direction — both hold
  production data
- Do not remove or downgrade any installed extension — all four services depend on them
- `roles_path` is 3-level: `roles:../../../ansible/roles`

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- Schema migrations on any database
- Creating or dropping databases or users
- Upgrading PostgreSQL or any extension
- Changes to connection credentials

These are PM-scope decisions.

## Reference

IaC conventions: see root `CLAUDE.md`
