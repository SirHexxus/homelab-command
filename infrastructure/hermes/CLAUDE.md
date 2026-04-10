# Hermes (IaC)

Provisions the Hermes LXC — the runtime host for the Hermes AI agent application.
For the application code itself, see `apps/hermes/CLAUDE.md`.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| Hermes LXC | LXC | 110 | 10.0.50.17 | — (CLI only in Phase 1) | 50 | IaC written — pending deployment |

## Role in Stack

**Depends on:**
- `platform/ollama` — primary LLM inference (10.0.50.10); Hermes routes to it first in tier
- `platform/postgres` — Mnemosyne persistent memory (10.0.50.14)
- `platform/n8n` — workflow execution for multi-step tasks
- `platform/redis` — ephemeral state and model routing counters

**Depended on by:**
- Nothing currently — Hermes is the terminal consumer in Phase 1

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

## Vault Variables

- Vault file is encrypted — decrypt with `ansible-vault view` to inspect
- Expected: SSH credentials, Postgres connection string for Mnemosyne, API keys

## Design Doc

`docs/hermes-design-doc-v1.0.md` — ReAct loop architecture, LLM tier routing (Ollama →
Gemini → Claude), skills framework, context system, Phase 1–5 build plan.

## Notes

- This is the IaC directory — it provisions the LXC host only
- Phase 1 is CLI-only; Telegram bots come in Phase 3; FastAPI web UI in Phase 4
- `scripts/` and `test-results/` are untracked — review before committing or gitignoring
- See root `CLAUDE.md` for IaC conventions (provider version, roles_path, vault naming)
