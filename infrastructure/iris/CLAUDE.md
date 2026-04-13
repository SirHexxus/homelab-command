# Iris

**Claude's role in this directory: System Administrator.**
Current scope is ntfy maintenance. Phase 3 work (syslog-ng, Vector, Wazuh agent) is not
yet active — do not implement those roles without a confirmed Phase 3 start. If Phase 3
begins, treat that work as PM scope.

## Current State

| Name | Type | IP | Port(s) | VLAN | Status |
|------|------|----|---------|------|--------|
| Helm HPS20 (helm-log) | Bare metal | 10.0.10.25 | — | 10 | Deployed |
| ntfy | Service on helm-log | 10.0.10.25 | 2586 | 10 | Deployed |
| syslog-ng | Service on helm-log | 10.0.10.25 | 514/udp | 10 | Phase 3 — not started |
| Vector | Service on helm-log | 10.0.10.25 | — | 10 | Phase 3 — not started |
| Wazuh agent | Service on helm-log | 10.0.10.25 | — | 10 | Phase 3 — not started |

DHCP static reservation: MAC `72:c6:b9:0d:32:ac` → 10.0.10.25
SSH key: `~/.ssh/homelab_ed25519` — not the default `id_rsa`

External access: `ntfy.sirhexx.com` → Ariadne NPM → 10.0.10.25:2586

## ntfy Topics

| Topic | Purpose |
|-------|---------|
| `provisioning` | Ansible playbook run notifications |
| `general-operations` | Homelab operational events |
| `argus` | Security alerts from Argus AI analysis |

## Role in Stack

**Depends on:** Nothing

**Depended on by:**
- All services using ntfy for push notifications
- `argus` (Phase 3) — syslog-ng + Vector ship structured logs to Splunk/TimescaleDB

## IaC Layout

```
infrastructure/iris/
  ansible/
    inventory.ini
    ansible.cfg        ← roles_path: roles:../../ansible/roles
    group_vars/
      all.yml
      vault.yml
    provision.yml
    roles/
      baseline/        ← system hardening
      ntfy/            ← ntfy 2.17.0 (var: ntfy_version)
      syslog_ng/       ← Phase 3 — not yet implemented
      vector/          ← Phase 3 — not yet implemented
      wazuh_agent/     ← Phase 3 — not yet implemented
```

No Terraform — bare metal host, not a Proxmox resource.

## Hard Constraints

- SSH key is `~/.ssh/homelab_ed25519` — not `id_rsa`
- ntfy version pinned: `ntfy_version: "2.17.0"` — update the variable when upgrading,
  do not hardcode the version string elsewhere

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- ntfy version upgrade
- Any Phase 3 role (syslog_ng, vector, wazuh_agent) — requires Wazuh Manager (Argus) deployed first
- Changes to ntfy topic configuration

## Reference

IaC conventions: see root `CLAUDE.md`
