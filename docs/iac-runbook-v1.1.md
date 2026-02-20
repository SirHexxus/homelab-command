# IaC Runbook
**Version:** 1.1
**Last Updated:** February 2026
**Status:** Living Document

---

## 1. Purpose & Philosophy

This document defines how Infrastructure as Code is used across the homelab. It is the canonical reference for tooling, conventions, workflow, secrets management, and recovery procedures. It is project-agnostic — individual Design Documents describe *what* a project deploys and how to invoke IaC for that project; this document describes *how* IaC works and *why* it is done this way.

**Core principles:**

**Reproducibility over convenience.** Every service must be rebuildable from code and documentation alone. If it isn't in Git, it doesn't exist.

**Separation of concerns.** Terraform provisions infrastructure (VMs, LXCs, network interfaces, storage). Ansible configures it (packages, services, application state). These layers never cross — Terraform does not configure software; Ansible does not create VMs.

**Idempotency.** Every playbook and Terraform configuration must be safe to run multiple times against the same target. Running it twice produces the same result as running it once.

**Auditability.** Infrastructure changes are committed to Git before they are applied. The Git log is the change log.

**Secrets are never committed.** Credentials, API tokens, and passwords live in Ansible Vault or environment variables — never in plaintext in any file tracked by Git.

**Portfolio value.** IaC doubles as documentation and interview artifact. Code is written to be readable and well-commented, as if a senior engineer is reviewing it.

---

## 2. Tool Stack

| Tool | Role | Version Target |
|------|------|---------------|
| Terraform | Infrastructure provisioning — creates VMs and LXC containers in Proxmox | Latest stable |
| Ansible | Configuration management — installs, configures, and maintains software inside hosts | Latest stable |
| Ansible Vault | Secrets encryption — stores credentials safely inside the repository | Bundled with Ansible |
| Git / GitHub | Version control and portfolio artifact | — |
| bpg/proxmox | Terraform provider for Proxmox VE | ~0.50+ |

**Why bpg/proxmox over telmate/proxmox:** The bpg provider is actively maintained, better documented, and handles LXC containers and VMs more reliably. The telmate provider has known bugs with token authentication and is no longer recommended.

**Docker / Docker Compose note:** Some services may optionally run inside Docker within an LXC or VM. When this is the case, the Ansible role handles Docker installation and Compose file deployment. Docker itself is not used as an IaC layer — Terraform and Ansible remain the authoritative provisioning stack.

---

## 3. Repository Structure

All IaC lives in the `homelab-command` GitHub repository under the `infrastructure/` directory.

```
homelab-command/
├── docs/                          # Design docs, architecture diagrams
├── infrastructure/
│   ├── modules/                   # Reusable Terraform modules
│   │   ├── lxc-container/         # Standard LXC provisioning module
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── proxmox-vm/            # Standard VM provisioning module
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   │
│   ├── {project}/                 # One directory per project/service group
│   │   ├── terraform/
│   │   │   ├── provider.tf        # Proxmox provider configuration
│   │   │   ├── variables.tf       # Input variable definitions
│   │   │   ├── main.tf            # Core resource definitions
│   │   │   ├── outputs.tf         # IP addresses, VMIDs, etc.
│   │   │   ├── terraform.tfvars.example  # Template — NEVER commit tfvars
│   │   │   └── README.md          # What this deploys + usage
│   │   │
│   │   └── ansible/
│   │       ├── inventory.ini      # Host definitions (IP from Terraform output)
│   │       ├── group_vars/
│   │       │   └── all/
│   │       │       ├── vars.yml   # Non-secret variables
│   │       │       └── vault.yml  # Encrypted secrets (ansible-vault)
│   │       ├── roles/
│   │       │   └── {service}/     # One role per service
│   │       │       ├── tasks/
│   │       │       │   └── main.yml
│   │       │       ├── templates/ # Jinja2 config templates
│   │       │       ├── handlers/
│   │       │       │   └── main.yml
│   │       │       └── defaults/
│   │       │           └── main.yml
│   │       ├── provision.yml      # Initial provisioning playbook
│   │       ├── update.yml         # Maintenance/update playbook
│   │       └── README.md
│   │
│   └── network/                   # pfSense and switch configs
│       ├── pfsense/               # Exported pfSense configs (XML)
│       └── switch/                # Ansible playbooks for TP-Link switch
│
└── .gitignore                     # Must include *.tfvars, vault passwords
```

**Project directory naming convention:** Use lowercase kebab-case matching the service group. Examples: `second-brain/`, `argus/`, `media-stack/`, `dmz/`.

---

## 4. Standard Workflow

Every infrastructure change follows this sequence. No exceptions.

```
1. PLAN
   Write or modify Terraform / Ansible code
   Commit to a feature branch in Git
   terraform plan → review what will change
   |
   v
2. REVIEW
   Verify plan output matches intent
   Check for unintended destroy/replace operations
   For Ansible: --check --diff mode for dry run
   |
   v
3. APPLY
   terraform apply
   ansible-playbook provision.yml
   |
   v
4. VERIFY
   Confirm service is reachable and functional
   Run smoke tests (API endpoint checks, service health)
   |
   v
5. COMMIT
   Commit any final changes to main branch
   Tag release if it's a significant milestone
   Update relevant Design Doc if architecture changed
```

**Never apply changes without planning first.** A `terraform plan` output in the commit message or PR description is the expected norm for significant changes.

---

## 5. Terraform Conventions

### 5.1 Provider Configuration

All projects use the `bpg/proxmox` provider. The provider block lives in `provider.tf` and reads credentials from variables — never hardcoded.

```hcl
terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.50"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = "${var.proxmox_token_id}=${var.proxmox_token_secret}"
  insecure  = var.proxmox_tls_insecure
}
```

### 5.2 Variables

All configurable values are defined in `variables.tf` with descriptions and types. Sensitive values are marked `sensitive = true`. Actual values go in `terraform.tfvars` (never committed — .gitignored). A `terraform.tfvars.example` template with placeholder values is committed instead.

```hcl
# variables.tf
variable "proxmox_endpoint" {
  description = "Proxmox API endpoint URL"
  type        = string
  default     = "https://10.0.10.2:8006"
}

variable "proxmox_token_id" {
  description = "Proxmox API token ID (format: user@realm!tokenname)"
  type        = string
}

variable "proxmox_token_secret" {
  description = "Proxmox API token secret"
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Skip TLS verification (true for self-signed certs)"
  type        = bool
  default     = true
}
```

### 5.3 Reusable Modules

Common provisioning patterns are abstracted into modules under `infrastructure/modules/`. Projects call modules rather than repeating resource definitions.

```hcl
# Example: deploying a standard LXC container via module
module "postgres" {
  source = "../../modules/lxc-container"

  hostname     = "postgres"
  cores        = 4
  memory_mb    = 8192
  disk_gb      = 100
  vlan_id      = 50
  ip_address   = "10.0.50.14/24"
  gateway      = "10.0.50.1"
  lxc_template = var.lxc_template
  proxmox_node = var.proxmox_node
  ssh_public_key = var.ssh_public_key
}
```

### 5.4 Outputs

Every Terraform project outputs at minimum the container/VM IP address and VMID. These outputs are used to populate the Ansible inventory.

```hcl
# outputs.tf
output "container_ip" {
  description = "IP address of the provisioned container"
  value       = module.postgres.ip_address
}

output "container_vmid" {
  description = "Proxmox VMID of the container"
  value       = module.postgres.vmid
}
```

### 5.5 State Management

Terraform state is stored locally for now (`terraform.tfstate` in each project directory). State files are .gitignored — they may contain sensitive data and are machine-generated, not human-authored. If a state file is lost, `terraform import` can reconstruct it from existing Proxmox resources.

**Future improvement:** Migrate to remote state (Terraform Cloud free tier or self-hosted Minio backend) once the lab is stable. Not required for Phase 1.

---

## 6. Ansible Conventions

### 6.1 Inventory

Each project maintains its own `inventory.ini` populated with IPs from Terraform outputs. Groups follow the service name.

```ini
[postgres]
postgres ansible_host=10.0.50.14

[postgres:vars]
ansible_user=root
ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
ansible_python_interpreter=/usr/bin/python3
```

### 6.2 Secrets — Ansible Vault

All secrets (passwords, API keys, tokens used inside services) are stored encrypted using Ansible Vault. The vault password itself is stored in a local password manager (not in the repo).

```bash
# Create encrypted vault file
ansible-vault create group_vars/all/vault.yml

# Edit existing vault
ansible-vault edit group_vars/all/vault.yml

# Run playbook with vault (prompt for password)
ansible-playbook provision.yml --ask-vault-pass

# Run playbook with vault password file (for automation)
ansible-playbook provision.yml --vault-password-file ~/.vault_pass
```

**Vault file naming convention:** Always named `vault.yml`. Variables inside are prefixed `vault_` to distinguish them from plain variables.

```yaml
# group_vars/all/vault.yml (encrypted)
vault_postgres_password: "..."
vault_redis_password: "..."
vault_minio_root_password: "..."
```

```yaml
# group_vars/all/vars.yml (plaintext — safe to commit)
postgres_password: "{{ vault_postgres_password }}"
redis_password: "{{ vault_redis_password }}"
```

### 6.3 Roles

Each service gets its own Ansible role. Roles are self-contained — they should work independently and not assume other roles have run.

Role task structure follows the pattern: install → configure → enable → verify.

```yaml
# roles/postgres/tasks/main.yml
- name: Install PostgreSQL
  apt:
    name: postgresql-16
    state: present
  tags: install

- name: Configure PostgreSQL
  template:
    src: postgresql.conf.j2
    dest: /etc/postgresql/16/main/postgresql.conf
  notify: restart postgresql
  tags: configure

- name: Enable and start PostgreSQL
  systemd:
    name: postgresql
    enabled: true
    state: started
  tags: enable

- name: Verify PostgreSQL is accepting connections
  postgresql_ping:
    login_host: localhost
  tags: verify
```

### 6.4 Playbook Structure

Every project has at minimum two playbooks:

**provision.yml** — Full initial setup from blank container. Runs all roles. Safe to re-run (idempotent). Used for first deployment and full rebuilds.

**update.yml** — Maintenance playbook. Updates packages, rotates logs, checks service health. Run on a schedule or manually.

Additional playbooks as needed: `backup.yml`, `restore.yml`, `configure-only.yml`.

---

## 7. Secrets Management Summary

| Secret Type | Storage | Access |
|-------------|---------|--------|
| Proxmox API token | `terraform.tfvars` (local, .gitignored) | Terraform reads at apply time |
| Service passwords (DB, Redis, etc.) | Ansible Vault `vault.yml` (encrypted in Git) | Ansible reads with vault password |
| SSH private key | `~/.ssh/homelab_ed25519` (local only) | Ansible uses for host connections |
| Vault password | Local password manager | Provided via `--ask-vault-pass` or `~/.vault_pass` |
| API keys (external services) | Ansible Vault | Injected into service config via templates |

**The vault password file (`~/.vault_pass`) must never be committed to Git.** It is the master key for all encrypted secrets in the repository.

---

## 8. .gitignore Requirements

Every IaC project directory must have these entries covered by the root `.gitignore`:

```gitignore
# Terraform
*.tfvars
*.tfstate
*.tfstate.*
.terraform/
.terraform.lock.hcl
terraform.tfplan

# Ansible
*.retry
.vault_pass
vault_pass.txt

# General
*.log
.DS_Store
```

---

## 9. Recovery Procedure

This is the authoritative procedure for rebuilding the homelab from scratch — whether recovering from hardware failure, a corrupt Proxmox installation, or a deliberate rebuild.

**Prerequisites:**
- Proxmox VE installed and accessible at 10.0.10.2
- pfSense restored from config backup (XML — stored in `infrastructure/network/pfsense/`)
- SSH key pair available (`~/.ssh/homelab_ed25519`)
- Vault password available (from password manager)
- Git repository cloned: `git clone https://github.com/{username}/homelab-command`

**Recovery sequence — deploy in this order to respect dependencies:**

```
Phase 1: Management Plane
    1. Portainer Server LXC (10.0.10.20)  ← Management UI for Docker VM

Phase 2: Core Data Services
    2. Postgres (10.0.50.14)   ← Second Brain + Argus depend on this
    3. Redis (10.0.50.15)      ← Session/cache layer
    4. MinIO (10.0.50.16)      ← Object storage

Phase 3: AI Inference
    5. Ollama (10.0.50.10)     ← Embeddings + LLM inference
    6. Whisper (10.0.50.12)    ← Voice transcription

Phase 4: Workflow Engine
    7. n8n (10.0.50.13)        ← Depends on Postgres, Redis, Ollama

Phase 5: SIEM Stack
    8. Splunk (10.0.50.20)
    9. Wazuh Manager (10.0.50.21)
    10. Grafana (10.0.50.22)

Phase 6: DMZ Services
    11. NGINX Proxy Manager (10.0.60.10)
    12. Authelia (10.0.60.11)
    Note: Crowdsec is a pfSense package — configure via pfSense UI, not IaC

Phase 7: Media Stack
    13. Docker VM (10.0.50.30)         ← Portainer Agent + Immich
    14. Jellyfin LXC (10.0.80.X)
    15. Audiobookshelf LXC (10.0.80.X)
    16. CalibreWeb LXC (10.0.80.X)
    17. Navidrome LXC (10.0.80.X)
    18. Jellyseerr LXC (10.0.80.X)
    Note: Media files survive on TrueNAS ZFS — only services need rebuilding
    Note: Restore Immich Postgres backup before provisioning Immich
```

**For each service, the recovery invocation is:**

```bash
cd infrastructure/{project}/terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with Proxmox credentials
terraform init
terraform apply

# Once container is provisioned:
cd ../ansible/
# Update inventory.ini with IP from Terraform output
ansible-playbook provision.yml --ask-vault-pass
```

Each project's `README.md` documents any project-specific steps, variables, or post-provisioning actions.

**Estimated full rebuild time from bare Proxmox:** 2–4 hours (mostly unattended).

---

## 10. Maintenance

### Regular tasks

| Task | Frequency | Playbook |
|------|-----------|---------|
| Update all service packages | Weekly | `update.yml` per project |
| Rotate Ansible Vault secrets | Quarterly | Manual + `ansible-vault rekey` |
| Review .gitignore for new secret patterns | On each new service addition | Manual |
| Test recovery procedure | Every 6 months | Full or partial rebuild in Proxmox |
| Update Terraform provider versions | Quarterly | `terraform init -upgrade` |

### When adding a new service

1. Create `infrastructure/{project}/terraform/` and `ansible/` directories
2. Copy provider.tf and variables.tf from an existing project as starting point
3. Write Terraform resources using modules where possible
4. Write Ansible roles following the install → configure → enable → verify pattern
5. Add secrets to Ansible Vault
6. Create `terraform.tfvars.example` with all required variables and placeholder values
7. Add recovery steps to the relevant Design Doc's IaC section
8. Verify the service appears in the recovery sequence above; update if needed
9. Test the full provision.yml playbook against a fresh container before merging

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.1 · Network & Services Architecture v1.4 · Project Roadmap v1.2 · Second Brain Design Doc v1.1 · Argus Design Doc v1.1 · Media Stack Design Doc v1.1 · Ariadne Design Doc v1.0*
