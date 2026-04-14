# Hermes (IaC)

**Claude's role in this directory: Project Manager for the Hermes LXC deployment.**
The deliverable is a running LXC (VMID 110, 10.0.50.17) with the Hermes application live
and verified. For the application code, see `apps/hermes/CLAUDE.md`.

Read `apps/hermes/ToDo.md` for the current task backlog. Do not run provisioning steps
not in the backlog without checking first.

See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.

## Definition of Done

- LXC provisioned via Terraform and running on VLAN 50
- Ansible provisioning complete: base OS hardened, dotfiles deployed, Hermes app installed
- Connectivity verified to all runtime dependencies (Ollama, Postgres, Redis, n8n)
- CLI entrypoint (`bin/hermes`) responds on the LXC

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| Hermes LXC | LXC | 110 | 10.0.50.17 | — (CLI only in Phase 1) | 50 | IaC written — pending deployment |

## Role in Stack

**Depends on:**
- `platform/ollama` — Tier 1 LLM inference (10.0.50.10)
- `platform/postgres` — Mnemosyne wiki persistence (10.0.50.14)
- `platform/redis` — model routing counters, ephemeral state (10.0.50.15)
- `platform/n8n` — multi-step workflow execution (10.0.50.13)

**Depended on by:**
- Nothing in Phase 1 — Hermes is the terminal consumer

## IaC Layout

```
infrastructure/hermes/
  terraform/
    main.tf            ← LXC container definition
    outputs.tf
    provider.tf
    variables.tf
    locals.tf
    terraform.tfvars   ← gitignored
    .terraform/        ← gitignored (provider binaries ~27MB)
  ansible/
    inventory.ini
    ansible.cfg        ← roles_path: roles:../../ansible/roles
    group_vars/
      all.yml
      vault.yml        ← ansible-vault encrypted
    provision.yml
  scripts/             ← untracked benchmark scripts (ab-test-models.sh)
  test-results/        ← untracked benchmark result .md files
```

## Hard Constraints

- VMID 110 is reserved for Hermes — do not reassign
- IP 10.0.50.17 is statically assigned — do not change
- Provider: `bpg/proxmox` pinned to `0.96.0` — see root `CLAUDE.md`
- Bridge: `vmbr1`, VLAN tag 50
- Template: `local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst`

## Vault Variables

Vault file is encrypted — decrypt with `ansible-vault view` to inspect. Expected: SSH
credentials, Postgres connection string for Mnemosyne, API keys (Gemini, Claude).

## Notes

- `scripts/` and `test-results/` are untracked — review before committing or gitignoring
- Design doc: `docs/hermes-design-doc-v1.0.md`
- IaC conventions: see root `CLAUDE.md`
