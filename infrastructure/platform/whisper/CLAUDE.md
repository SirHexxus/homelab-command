# Whisper (Platform)

**Claude's role in this directory: System Administrator.**
This service is deployed and stable. The work here is maintenance and targeted updates —
not new implementation.

## Current State

LXC 102 at 10.0.50.12:9000, VLAN 50. Deployed. Terraform + Ansible managed.

**API endpoint:** `POST http://10.0.50.12:9000/v1/audio/transcriptions` (OpenAI-compatible)

## Role in Stack

**Depends on:** Nothing

**Depended on by:**
- `mnemosyne` — voice memo transcription before classify → file pipeline
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

## Hard Constraints

- Endpoint must remain OpenAI-compatible — Mnemosyne and Hermes clients use the OpenAI
  audio API format unchanged
- `roles_path` is 3-level: `roles:../../../ansible/roles`

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- Whisper version upgrade or model change
- Port or endpoint path changes
- API compatibility changes

## Reference

IaC conventions: see root `CLAUDE.md`.
See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.
