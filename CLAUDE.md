# homelab-command

Monorepo for the full homelab infrastructure: Terraform + Ansible for all services, network
IaC (pfSense + switch), application code (Hermes), and design docs. Single Proxmox node
(puppetmaster) hosts everything via LXC containers and VMs.

**Philosophy:** `docs/homelab-philosophy-v1.0.md` - the values and principles behind every decision in this repo.

## Focused Sessions

**Start Claude from the service directory, not the repo root**, when working on a specific
service. Claude Code loads CLAUDE.md files walking up from your working directory — so starting
from `infrastructure/orpheus/` gives you Orpheus context + these root conventions without the
noise of the full roster.

```bash
cd infrastructure/orpheus && claude     # Orpheus-focused
cd infrastructure/platform/postgres && claude   # Postgres-focused
```

---

## Service Roster

| Service | Dir | Primary Host(s) | VLAN | Status |
|---------|-----|-----------------|------|--------|
| **Argus** | `infrastructure/argus/` | 3 planned LXCs: 10.0.50.20–22 | 50 | Designed — Phase 3 |
| **Ariadne** | `infrastructure/ariadne/` | NPM (VMID 120, 10.0.60.10), Authelia (VMID 121, 10.0.60.11), Umami (VMID 122, 10.0.50.18) | 60 / 50 | Deployed |
| **Hermes** | `infrastructure/hermes/` | LXC VMID 110, 10.0.50.17 | 50 | IaC written — pending deploy |
| **Iris** | `infrastructure/iris/` | Bare metal: 10.0.10.25 (Helm HPS20) | 10 | ntfy deployed; logging Phase 3 |
| **Mnemosyne** | `infrastructure/mnemosyne/` | No dedicated host — wiki at `~/mneme/wiki/`, served by Hermes | 50 | Phase 2 — pipeline pending |
| **Orpheus** | `infrastructure/orpheus/` | TrueNAS R710 eno4: 10.0.80.5 (13+ TrueNAS Scale apps) | 80 | Apps running; *Arr reconfiguration pending |
| **Hephaestus** | `infrastructure/hephaestus/` *(planned)* | VM 10.0.50.30 — Docker Compose host | 50 | Planned — post-June |
| **Postgres** | `infrastructure/platform/postgres/` | LXC VMID 105, 10.0.50.14 | 50 | Deployed |
| **Redis** | `infrastructure/platform/redis/` | LXC VMID 106, 10.0.50.15 | 50 | Deployed |
| **MinIO** | `infrastructure/platform/minio/` | LXC VMID 108, 10.0.50.16 | 50 | Deployed |
| **n8n** | `infrastructure/platform/n8n/` | LXC VMID 107, 10.0.50.13 | 50 | Deployed |
| **Ollama** | `infrastructure/platform/ollama/` | LXC VMID 101, 10.0.50.10 | 50 | Deployed |
| **Whisper** | `infrastructure/platform/whisper/` | LXC VMID 102, 10.0.50.12 | 50 | Deployed |
| **pfSense** | `infrastructure/network/pfsense/` | VM VMID 200, 10.0.10.1 | 10 | Deployed |
| **Switch** | `infrastructure/network/switch/` | TP-Link T1600G-28PS, 10.0.10.50 | 10 | Deployed |
| **Proxmox** | `infrastructure/proxmox/` | Bare metal puppetmaster, 10.0.10.2 | 10 | Deployed |

**Available VMIDs:** 103, 109, 111–119, 123–199, 201+
**Available IPs:** VLAN 50 → 10.0.50.19+; VLAN 60 → 10.0.60.12+

---

## IaC Conventions

These apply to every service in the repo. Service CLAUDE.md files do not repeat them.

### OS / platform
- Linux-first; Debian and Debian derivatives (Ubuntu, Proxmox VE) are the default
- Other distros only when they are clearly the right tool

### Deployment model
- LXC (unprivileged) is always preferred
- Docker services go on a dedicated Docker host VM (Hephaestus, 10.0.50.30) — not in an LXC
- Docker Compose on that VM is managed via Ansible; `compose.yaml` lives in IaC as Source of Truth
- Docker-in-LXC: absolute last resort

### Terraform
- Provider: `bpg/proxmox` version `0.96.0` — no exceptions
- Bridge: `vmbr1` (VLAN-aware trunk)
- LXC template: `local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst`
- Storage — root FS: `local-lvm`; data volumes: `general-store` (ZFS, 11.5TB)
- Modules at `infrastructure/modules/` are empty placeholders — write inline Terraform until populated
- State files: `terraform.tfstate` — gitignored; stored locally per-service

### Ansible
- `roles_path` depth depends on service location:
  - 2-level services (`infrastructure/<service>/ansible/`): `roles:../../ansible/roles`
  - 3-level services (`infrastructure/platform/<service>/ansible/`): `roles:../../../ansible/roles`
  - 3-level network (`infrastructure/network/<service>/ansible/`): `roles:../../../ansible/roles`
- Shared roles live at `infrastructure/ansible/roles/` (dotfiles, proxmox_base)
- SSH keys: most services → `~/.ssh/id_rsa`; iris + pfSense → `~/.ssh/homelab_ed25519`

### Vault
- Convention: `vault_<service>_<credential>`
- Known variables (do not duplicate):
  - `vault_redis_password`
  - `vault_n8n_password`
  - `vault_minio_root_user`, `vault_minio_root_password`
  - `vault_mnemosyne_password`, `vault_argus_password`, `vault_umami_password`
  - `vault_switch_password`

---

## VLAN Topology

| VLAN | Name | Subnet | Gateway | Purpose |
|------|------|--------|---------|---------|
| 10 | Management | 10.0.10.0/24 | 10.0.10.1 | Proxmox, switch, Iris, pfSense, TrueNAS mgmt |
| 20 | Personal | 10.0.20.0/24 | 10.0.20.1 | Family WiFi (eero SSID 1) |
| 30 | Work | 10.0.30.0/24 | 10.0.30.1 | Work device — fully isolated |
| 40 | IoT | 10.0.40.0/24 | 10.0.40.1 | Smart devices — internet only |
| 50 | Lab Services | 10.0.50.0/24 | 10.0.50.1 | All self-hosted services and AI stack |
| 60 | DMZ | 10.0.60.0/24 | 10.0.60.1 | Ariadne, Authelia — internet-facing |
| 66 | Sandbox | 10.0.66.0/24 | 10.0.66.1 | Isolated testing and quarantine |
| 70 | Guest | 10.0.70.0/24 | 10.0.70.1 | Guest WiFi — internet only |
| 80 | Media | 10.0.80.0/24 | 10.0.80.1 | Orpheus — TrueNAS media serving |

---

## Proxmox Node (puppetmaster)

| Field | Value |
|-------|-------|
| IP | 10.0.10.2 |
| PVE version | 9.1.0 |
| WAN bridge | vmbr0 (eno8303) |
| LAN/VLAN bridge | vmbr1 (eno8403, VLAN-aware) |
| Storage — ZFS | `general-store` (11.5TB) |
| Storage — LVM thin | `local-lvm` (1.7TB SSD) |
| DNS | 10.0.10.1, 1.1.1.1, 8.8.8.8; search: homelab.internal |

---

## Key Docs

| Doc | Purpose |
|-----|---------|
| `docs/homelab-philosophy-v1.0.md` | Values and principles behind all homelab decisions — read this first |
| `docs/README.md` | Full document index |
| `docs/network-services-architecture-v1.6.md` | VLAN topology, firewall rules, full IP schema |
| `docs/iac-runbook-v1.2.md` | Deployment procedures, secrets management, Ansible patterns |
| `docs/project-roadmap-v1.4.md` | Phased delivery schedule and current pursuits |
| `docs/argus-design-doc-v1.2.md` | Argus SIEM architecture |
| `docs/ariadne-design-doc-v1.0.md` | DMZ and perimeter design |
| `docs/hermes-design-doc-v1.0.md` | Hermes AI agent architecture |
| `docs/mnemosyne-design-doc-v1.1.md` | Mnemosyne knowledge base design |
| `docs/orpheus-design-doc-v1.1.md` | Orpheus media platform |
| `.claude/agents/homelab-iac-specialist.md` | Authoritative VMID/IP allocation table |
