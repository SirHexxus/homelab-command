# n8n

Workflow automation engine — orchestrates all Mnemosyne ingestion pipelines (capture → classify
→ embed → store) and Argus AI analysis pipelines (query → Ollama → enrich → alert).

## Components

| Name | Type | VMID | IP | Port | VLAN | Status |
|------|------|------|----|------|------|--------|
| n8n LXC | LXC | 107 | 10.0.50.13 | 5678 | 50 | Deployed |

External access: `automation.hexxusweb.com` → Ariadne NPM → 10.0.50.13:5678

## Role in Stack

**Depends on:**
- `platform/postgres` — n8n workflow state and execution history (`n8n` DB)
- `platform/redis` — job queue backend
- `platform/ollama` — LLM calls within AI analysis workflows
- `platform/minio` — file storage for workflow artifacts

**Depended on by:**
- `mnemosyne` — all ingestion pipelines run as n8n workflows
- `argus` — AI analysis pipeline (runs every 5 min: query TimescaleDB → analyze → enrich)
- `hermes` — multi-step task execution via n8n workflows

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

## Notes

- No Terraform — LXC provisioned manually; Ansible manages configuration only
- `roles_path` is 3-level: `roles:../../../ansible/roles`
- n8n is duplicated on TrueNAS Scale apps — the Proxmox LXC (107) is **authoritative**;
  the TrueNAS instance is a legacy artifact and should be stopped/removed
- See root `CLAUDE.md` for IaC conventions
