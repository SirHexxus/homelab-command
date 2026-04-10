# Redis

Shared cache and ephemeral state store — used by n8n for its job queue, and by Hermes for
model routing counters and short-lived task state.

## Components

| Name | Type | VMID | IP | Port | VLAN | Status |
|------|------|------|----|------|------|--------|
| Redis LXC | LXC | 106 | 10.0.50.15 | 6379 | 50 | Deployed |

## Role in Stack

**Depends on:**
- Nothing

**Depended on by:**
- `platform/n8n` — job queue backend
- `hermes` — model routing counters, ephemeral agent state
- `mnemosyne` — caching layer (via n8n pipelines)
- `ariadne` (Authelia) — session storage

## IaC Layout

```
infrastructure/platform/redis/
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

- `vault_redis_password`

## Notes

- No Terraform — LXC provisioned manually; Ansible manages configuration only
- `roles_path` is 3-level: `roles:../../../ansible/roles`
- See root `CLAUDE.md` for IaC conventions
