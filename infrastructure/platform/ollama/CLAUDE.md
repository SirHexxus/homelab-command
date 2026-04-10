# Ollama

Local LLM inference engine — runs Mistral 7B for general tasks and nomic-embed-text for
vector embeddings. Hermes routes to Ollama first before escalating to Gemini or Claude API.

## Components

| Name | Type | VMID | IP | Port | VLAN | Status |
|------|------|------|----|------|------|--------|
| Ollama LXC | LXC | 101 | 10.0.50.10 | 11434 | 50 | Deployed |

## Models Loaded

| Model | Purpose |
|-------|---------|
| `mistral:7b` | General reasoning and task execution |
| `nomic-embed-text` | Vector embedding generation for Mnemosyne |

## Role in Stack

**Depends on:**
- Nothing

**Depended on by:**
- `hermes` — primary LLM inference (Tier 1 in routing: Ollama → Gemini → Claude)
- `platform/n8n` — LLM calls within Mnemosyne ingestion and Argus analysis pipelines
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

## Notes

- One of two platform services with Terraform (the other is whisper)
- `roles_path` is 3-level: `roles:../../../ansible/roles`
- GPU passthrough is not yet configured — Ollama runs on CPU only; GPU sourcing deferred
  (target: RTX 3060 12GB or Intel Arc B580)
- See root `CLAUDE.md` for IaC conventions
