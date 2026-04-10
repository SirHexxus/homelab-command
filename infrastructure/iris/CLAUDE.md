# Iris

Bare-metal log collector and notification broker — runs on the Helm HPS20 (helm-log).
Currently hosts ntfy push notifications; Phase 3 adds syslog-ng + Vector for Argus log
collection, plus a Wazuh agent.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| Helm HPS20 (helm-log) | Bare metal | — | 10.0.10.25 | — | 10 | Deployed |
| ntfy | Service on helm-log | — | 10.0.10.25 | 2586 | 10 | IaC-deployed |
| syslog-ng | Service on helm-log | — | 10.0.10.25 | 514/udp | 10 | Planned — Phase 3 |
| Vector | Service on helm-log | — | 10.0.10.25 | — | 10 | Planned — Phase 3 |
| Wazuh agent | Service on helm-log | — | 10.0.10.25 | — | 10 | Planned — Phase 3 |

**Note:** helm-log is bare metal — no Terraform, Ansible only.
DHCP static reservation: MAC `72:c6:b9:0d:32:ac` → 10.0.10.25

## Role in Stack

**Depends on:**
- Nothing — sits at the infrastructure boundary, receives from other services

**Depended on by:**
- All services using ntfy for push notifications (topics: `provisioning`, `general-operations`, `argus`)
- `argus` — ntfy `argus` topic receives security event alerts
- `argus` (Phase 3) — syslog-ng + Vector ship structured logs to Splunk/TimescaleDB

## ntfy Topics

| Topic | Purpose |
|-------|---------|
| `provisioning` | Ansible playbook run notifications |
| `general-operations` | Homelab operational events |
| `argus` | Security alerts from Argus AI analysis |

External access: `ntfy.sirhexx.com` → Ariadne NPM → 10.0.10.25:2586

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
      syslog_ng/       ← planned Phase 3
      vector/          ← planned Phase 3
      wazuh_agent/     ← planned Phase 3
```

No Terraform — bare metal host, not a Proxmox resource.

## Vault Variables

- SSH key: `~/.ssh/homelab_ed25519` (ed25519 — not the default `id_rsa`)

## Notes

- SSH key is `homelab_ed25519` — not the default `id_rsa` used by most other services
- ntfy version pinned: `ntfy_version: "2.17.0"` — update var when upgrading
- Provisioning playbook was run 2026-03-10 — all 3 roles clean and idempotent
- Phase 3 (syslog-ng + Vector) requires Wazuh Manager (Argus) deployed first
- See root `CLAUDE.md` for IaC conventions (roles_path, vault naming)
