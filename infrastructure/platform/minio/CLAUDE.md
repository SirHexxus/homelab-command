# MinIO

S3-compatible object storage — stores voice memos, file attachments, and binary objects that
don't belong in Postgres. Also used for Umami analytics backups.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| MinIO LXC | LXC | 108 | 10.0.50.16 | 9000 (API), 9001 (console) | 50 | Deployed |

## Role in Stack

**Depends on:**
- Nothing

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

## Notes

- No Terraform — LXC provisioned manually; Ansible manages configuration only
- `roles_path` is 3-level: `roles:../../../ansible/roles`
- See root `CLAUDE.md` for IaC conventions
