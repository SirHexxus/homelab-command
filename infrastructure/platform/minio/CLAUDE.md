# MinIO (Platform)

**Claude's role in this directory: System Administrator.**
This service is deployed and stable. The work here is maintenance and targeted updates —
not new implementation. If a task crosses into bucket restructuring or credential rotation,
stop and confirm before proceeding.

## Current State

LXC 108 at 10.0.50.16, VLAN 50. Deployed. Ansible-managed only — no Terraform (LXC was
provisioned manually).

| Port | Purpose |
|------|---------|
| 9000 | S3-compatible API |
| 9001 | MinIO console (admin UI) |

## Role in Stack

**Depends on:** Nothing

**Depended on by:**
- `mnemosyne` — voice memo storage, file attachments from Telegram ingestion
- `ariadne` (Umami) — analytics backup storage

## IaC Layout

```
infrastructure/platform/minio/
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

- `vault_minio_root_user`
- `vault_minio_root_password`

## Hard Constraints

- Do not delete or restructure existing buckets without explicit direction — Mnemosyne
  and Umami data lives here
- `roles_path` is 3-level: `roles:../../../ansible/roles`

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- Bucket deletion or restructuring
- Credential rotation
- MinIO version upgrade
- Access policy changes

## Reference

IaC conventions: see root `CLAUDE.md`
