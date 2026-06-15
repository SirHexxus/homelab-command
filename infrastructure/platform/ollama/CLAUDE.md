# Ollama (Platform)

**Claude's role in this directory: System Administrator.**
This service is deployed and stable. The work here is maintenance and targeted updates —
not new implementation. Model changes have downstream effects on Hermes routing — stop
and confirm before adding or removing models.

## Current State

LXC 101 at 10.0.50.10:11434, VLAN 50. Deployed. Terraform + Ansible managed.
GPU passthrough is not configured — Ollama runs on CPU only. GPU sourcing is deferred
(target: RTX 3060 12GB or Intel Arc B580).

## Models Loaded

| Model | Purpose |
|-------|---------|
| `nomic-embed-text` | Vector embedding generation — never routed to cloud |

**Reasoning tier retired (D2 / AUD-017, 2026-06-14):** post-pivot, all reasoning inference
moved to Vertex via Chiron's LiteLLM proxy — Ollama is **embeddings-only**. The CPU-only
reasoning models (`mistral:7b`, `qwen3:1.7b`, `qwen3:4b`) are being pruned. Revisit a local
reasoning tier once a GPU lands (target RTX 3060 12GB / Intel Arc B580).

## Role in Stack

**Depends on:** Nothing

**Depended on by:**
- `hermes` — Tier 1 LLM inference (Ollama → Gemini → Claude)
- `platform/n8n` — LLM calls within Mnemosyne and Argus pipelines
- `mnemosyne` — embedding generation via nomic-embed-text

## IaC Layout

```
infrastructure/platform/ollama/
  terraform/
    main.tf            ← LXC container definition
    outputs.tf
    provider.tf
    variables.tf
    locals.tf
    terraform.tfvars   ← gitignored
    .terraform/        ← gitignored (provider binaries)
  ansible/
    inventory.ini
    ansible.cfg        ← roles_path: roles:../../../ansible/roles
    group_vars/
      all.yml
      vault.yml
    provision.yml
```

## Hard Constraints

- `nomic-embed-text` must remain loaded — Mnemosyne embedding generation depends on it
- Do not remove models without checking Hermes routing config in `apps/hermes/config/config.yml`
- `roles_path` is 3-level: `roles:../../../ansible/roles`

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- Adding or removing models
- GPU passthrough configuration
- Ollama version upgrade
- Memory or resource limit changes

## Reference

IaC conventions: see root `CLAUDE.md`.
See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.
