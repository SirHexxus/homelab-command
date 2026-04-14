# n8n (Platform)

**Claude's role in this directory: System Administrator.**
This service is deployed and stable. The work here is maintenance and targeted updates —
not new implementation. Workflow development happens inside n8n itself, not here. If a task
crosses into database changes or version upgrades, stop and confirm.

## Current State

LXC 107 at 10.0.50.13:5678, VLAN 50. Deployed. Ansible-managed only — no Terraform (LXC
was provisioned manually).

External access: `automation.hexxusweb.com` → Ariadne NPM → 10.0.50.13:5678

**Note:** A legacy n8n instance exists on TrueNAS Scale apps. The Proxmox LXC (107) is
authoritative. The TrueNAS instance should be stopped and removed.

## Role in Stack

**Depends on:**
- `platform/postgres` — n8n workflow state and execution history (`n8n` DB)
- `platform/redis` — job queue backend
- `platform/ollama` — LLM calls within AI analysis workflows
- `platform/minio` — file storage for workflow artifacts

**Depended on by:**
- `mnemosyne` — all ingestion pipelines run as n8n workflows
- `argus` — AI analysis pipeline (runs every 5 min)
- `hermes` — multi-step task execution

## IaC Layout

```
infrastructure/platform/n8n/
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

- `vault_n8n_password` — n8n Postgres DB user (also referenced in postgres group_vars)

## Hard Constraints

- Do not modify the n8n Postgres DB schema directly — n8n manages its own schema
- `roles_path` is 3-level: `roles:../../../ansible/roles`

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- n8n version upgrade
- Credential rotation
- Database changes
- Changes to the external proxy config (`automation.hexxusweb.com` → Ariadne)

## Reference

IaC conventions: see root `CLAUDE.md`.
See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.
