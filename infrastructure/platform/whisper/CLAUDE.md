# Whisper

Speech-to-text API — exposes an OpenAI-compatible transcription endpoint used by Mnemosyne
for voice memo ingestion.

## Components

| Name | Type | VMID | IP | Port | VLAN | Status |
|------|------|------|----|------|------|--------|
| Whisper LXC | LXC | 102 | 10.0.50.12 | 9000 | 50 | Deployed |

**API endpoint:** `POST http://10.0.50.12:9000/v1/audio/transcriptions` (OpenAI-compatible)

## Role in Stack

**Depends on:**
- Nothing

**Depended on by:**
- `mnemosyne` — voice memo transcription before classify → embed → store pipeline
- `hermes` — voice input transcription (Phase 3+)

## IaC Layout

```
infrastructure/platform/whisper/
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

- One of two platform services with Terraform (the other is ollama)
- `roles_path` is 3-level: `roles:../../../ansible/roles`
- Endpoint is OpenAI-compatible — any client using the OpenAI audio API works unchanged
- See root `CLAUDE.md` for IaC conventions
