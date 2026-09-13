# docs

Reference documents for the homelab-command monorepo. All design decisions, infrastructure
conventions, and operational procedures live here.

See `docs/homelab-philosophy.md` for the values and principles behind all homelab decisions.

> **Versioning policy (D4 / AUD-015, 2026-06-14):** document filenames are version-free; the
> authoritative version lives in each doc's header and the Version column below. Filenames are
> **not** renamed on version bumps, so links never break. The `-vX.Y` filename suffixes were
> stripped in the S5.1 sweep (2026-09-13).

---

## Core reference

| Document | Version | Purpose |
|----------|---------|---------|
| [Homelab Philosophy](homelab-philosophy.md) | v1.0 | Goals, principles, and the values behind every homelab decision |
| [Project Roadmap](project-roadmap.md) | v2.4 | Phased delivery plan, current pursuits, and project structure |
| [IaC Runbook](iac-runbook.md) | v1.5 | Terraform + Ansible conventions, workflow, secrets, and recovery procedures |
| [Hardware Catalog](hardware-catalog.md) | v1.3 | Physical inventory - compute, storage, and networking equipment |
| [Network & Services Architecture](network-services-architecture.md) | v1.9 | VLAN topology, IP schema, firewall architecture, and services inventory |

## Service design docs

| Document | Version | Service | Purpose |
|----------|---------|---------|---------|
| [Argus Design Doc](argus-design-doc.md) | v1.2 | Argus | AI-augmented SIEM - log collection, threat detection, incident response |
| [Ariadne Design Doc](ariadne-design-doc.md) | v1.0 | Ariadne | DMZ and perimeter - reverse proxy, authentication, VPN, outbound filtering |
| [Hermes Design Doc](hermes-design-doc.md) | v1.1 | Hermes | Autonomous-execution subsystem encapsulating Layers 1–4 of the Five-Layer AI Stack |
| [Mnemosyne Design Doc](mnemosyne-design-doc.md) | v1.2 | Mnemosyne | Personal knowledge management - git-backed wiki with AI-assisted capture |
| [Mnemosyne Worker Migration](mnemosyne-worker-migration.md) | v1.0 | Mnemosyne | Migration plan moving pipeline cron off the laptop onto the LXC 103 worker (n8n/LXC split, LLM engine decision, cutover slices) |
| [Orpheus Design Doc](orpheus-design-doc.md) | v1.3 | Orpheus | Family media platform - video, photos, music, audiobooks, ebooks |
| [Phemius Design Doc](phemius-design-doc.md) | v1.0 | Phemius | Living-room media client - Kodi on lobotomised panel, Tunarr channels, kid profiles |
| [Themis Design Doc](themis-design-doc.md) | v1.1 | Themis | Android endpoint management - MDM policy groups, enrollment modes, fleet phasing |

## Operational guides

| Document | Version | Purpose |
|----------|---------|---------|
| [Media Library Guide](media-library-guide.md) | v1.0 | Directory structure, naming conventions, and migration procedures for TrueNAS media storage |

## Evaluations and reports

| Document | Purpose |
|----------|---------|
| [App Evaluation Report (2026-03-11)](app-evaluation-report-2026-03-11.md) | Classification and scoring of 1,166 awesome-selfhosted apps against the homelab profile |

## Templates

| Document | Purpose |
|----------|---------|
| [NAS README Template](nas-readme-template.md) | Boilerplate README for NAS dataset documentation |
