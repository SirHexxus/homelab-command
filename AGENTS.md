# AGENTS.md — homelab-command

Guidance for AI agents operating in this repository. Human contributors should
read `CLAUDE.md` (root) and the per-service `CLAUDE.md` files; this file is the
short, agent-facing contract.

## What this repo is

The IaC monorepo for the full homelab: Terraform + Ansible for every service,
network IaC, application code, and design docs. A single Proxmox node
(puppetmaster) hosts everything via LXC containers and VMs.

- **Philosophy:** `docs/homelab-philosophy-v1.0.md` — read first.
- **Service roster** (hosts, VMIDs, IPs, VLANs, status): the table in root
  `CLAUDE.md`. Treat it as the source of truth for what runs where.
- **IaC conventions** (Terraform provider, LXC templates, Ansible `roles_path`,
  Vault naming): also root `CLAUDE.md` — do not restate or diverge.

## Commit conventions

- **Subject-only, single line.** No body, no heredoc. Split distinct changes
  into multiple atomic commits instead of one multi-part commit.
- **No `Co-Authored-By` / Claude attribution** unless explicitly requested.
- **Propose, then wait for approval** before committing. Match the existing
  style in `git log --oneline` for the area you are touching.

## Read-only clone rule (Chiron / Hermes-Agent on LXC 110)

A read-only checkout of this repo lives on the Hermes-Agent LXC at
`/opt/hermes-agent/repos/homelab-command`, cloned via a **read-only GitHub
deploy key** (`vault_chiron_repo_deploy_key`, deployed by
`infrastructure/hermes/ansible/roles/hermes_agent/tasks/repo.yml`).

That clone exists solely for **read-only repo verification** (e.g. the
`repo-health-sweep` skill diffing live service state against the roster).

- **Never push, commit, or write from that clone.** `git pull` only.
- The deploy key has no write scope on GitHub; do not attempt to escalate it.
- Mutating changes to this repo happen from a human-driven workspace, never
  from an autonomous agent on the LXC.

## Live systems — handle with care

- Crontab and live-service changes go through a human-supervised session, not
  autonomous agents (see the autonomous-action-boundaries rule).
- Terraform is plan-gated: never apply a plan that shows replace/destroy —
  stop and escalate.
- Never touch `general_pool/archive` on the NAS without explicit direction.
