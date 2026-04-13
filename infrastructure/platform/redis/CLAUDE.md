# Redis (Platform)

**Claude's role in this directory: System Administrator.**
This service is deployed and stable. The work here is maintenance and targeted updates —
not new implementation. If a task crosses into version upgrades or credential rotation,
stop and confirm before proceeding.

## Current State

LXC 106 at 10.0.50.15:6379, VLAN 50. Deployed. Ansible-managed only — no Terraform (LXC
was provisioned manually).

## Role in Stack

**Depends on:** Nothing

**Depended on by:**
- `platform/n8n` — job queue backend
- `hermes` — model routing counters, ephemeral agent state
- `mnemosyne` — session state for Telegram bot clarification flow
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

## Hard Constraints

- Do not rotate `vault_redis_password` without updating all dependent services first:
  n8n, Hermes, Authelia
- `roles_path` is 3-level: `roles:../../../ansible/roles`

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- Redis version upgrade
- Credential rotation
- Persistence configuration changes (RDB/AOF)
- Memory limit or eviction policy changes

## Reference

IaC conventions: see root `CLAUDE.md`
