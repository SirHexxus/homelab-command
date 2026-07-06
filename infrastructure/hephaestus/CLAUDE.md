# Hephaestus — Shared Docker Compose Host

Claude's role in this directory: System Administrator / IaC maintainer.

Hephaestus is the homelab's single Docker host. Any service that ships as a
Docker Compose stack lands here — never Docker-in-LXC. Each stack gets its own
role under `ansible/roles/`, its own directory under `/opt/` on the VM, and its
`compose.yaml` vendored in IaC as Source of Truth.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|-----|---------|------|--------|
| Hephaestus | VM (Ubuntu 24.04 cloud image) | 109 | 10.0.50.30 | 22 | 50 | Deployed |
| Firecrawl | Compose stack (api, playwright, redis, rabbitmq, nuq-postgres) | — | 10.0.50.30 | 3002 | 50 | Deployed |

## Role in Stack

- **Depends on:** Proxmox (puppetmaster), pfSense (VLAN 50 routing)
- **Depended on by:** anything scraping via Firecrawl (n8n workflows, Chiron skills)

## IaC Layout

```
infrastructure/hephaestus/
├── CLAUDE.md
├── terraform/            # VM: cloud image download + cloud-init vendor snippet + VM
│   ├── provider.tf       # bpg/proxmox = 0.98.1
│   ├── main.tf
│   ├── variables.tf
│   ├── locals.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
└── ansible/
    ├── ansible.cfg       # roles_path = roles:../../ansible/roles
    ├── inventory.ini     # ubuntu@10.0.50.30, sudo become
    ├── provision.yml     # docker_host + firecrawl roles + health check
    ├── update.yml        # OS updates + image pull + stack reconcile
    ├── group_vars/
    │   ├── hephaestus.yml
    │   └── vault.yml     # (encrypted; see vault.yml.example)
    └── roles/
        ├── docker_host/  # Docker Engine from official apt repo; reusable base
        └── firecrawl/    # files/compose.yaml = Source of Truth
```

## Hard Constraints

- Provider pinned `= 0.98.1` (bpg/proxmox)
- VM user is `ubuntu` (cloud-init; root SSH disabled) — Ansible escalates via sudo
- `compose.yaml` in IaC is the Source of Truth; never hand-edit `/opt/*/compose.yaml`
  on the VM — change the role file and re-run a playbook
- Firecrawl api image pinned to a release tag; `playwright-service` and
  `nuq-postgres` publish `:latest` only (upstream limitation)
- Firecrawl runs its own redis + postgres containers — deliberately isolated from
  the shared Redis LXC (106) and Postgres LXC (105)
- Cloud-init vendor snippet requires `snippets` content on the `local` datastore

## Vault Variables

- `vault_firecrawl_bull_auth_key` — queue admin UI auth key

## Reference

- Root conventions: `../../CLAUDE.md`
- Philosophy: `../../docs/homelab-philosophy-v1.0.md`
- Upstream: https://github.com/firecrawl/firecrawl (SELF_HOST.md)
