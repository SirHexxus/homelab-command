# docs

Reference documents for the homelab-command monorepo. All design decisions, infrastructure
conventions, and operational procedures live here.

See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.

---

## Core reference

| Document | Version | Purpose |
|----------|---------|---------|
| [Homelab Philosophy](homelab-philosophy-v1.0.md) | v1.0 | Goals, principles, and the values behind every homelab decision |
| [Project Roadmap](project-roadmap-v1.4.md) | v1.6 | Phased delivery plan, current pursuits, and project structure |
| [IaC Runbook](iac-runbook-v1.2.md) | v1.3 | Terraform + Ansible conventions, workflow, secrets, and recovery procedures |
| [Hardware Catalog](hardware-catalog-v1.2.md) | v1.2 | Physical inventory - compute, storage, and networking equipment |
| [Network & Services Architecture](network-services-architecture-v1.6.md) | v1.6 | VLAN topology, IP schema, firewall architecture, and services inventory |

## Service design docs

| Document | Version | Service | Purpose |
|----------|---------|---------|---------|
| [Argus Design Doc](argus-design-doc-v1.2.md) | v1.2 | Argus | AI-augmented SIEM - log collection, threat detection, incident response |
| [Ariadne Design Doc](ariadne-design-doc-v1.0.md) | v1.0 | Ariadne | DMZ and perimeter - reverse proxy, authentication, VPN, outbound filtering |
| [Hermes Design Doc](hermes-design-doc-v1.0.md) | v1.0 | Hermes | Local AI agent for homelab automation and personal productivity |
| [Mnemosyne Design Doc](mnemosyne-design-doc-v1.1.md) | v1.1 | Mnemosyne | Personal knowledge management - git-backed wiki with AI-assisted capture |
| [Orpheus Design Doc](orpheus-design-doc-v1.1.md) | v1.1 | Orpheus | Family media platform - video, photos, music, audiobooks, ebooks |

## Operational guides

| Document | Version | Purpose |
|----------|---------|---------|
| [Media Library Guide](media-library-guide-v1.0.md) | v1.0 | Directory structure, naming conventions, and migration procedures for TrueNAS media storage |

## Evaluations and reports

| Document | Purpose |
|----------|---------|
| [App Evaluation Report (2026-03-11)](app-evaluation-report-2026-03-11.md) | Classification and scoring of 1,166 awesome-selfhosted apps against the homelab profile |

## Templates

| Document | Purpose |
|----------|---------|
| [NAS README Template](nas-readme-template.md) | Boilerplate README for NAS dataset documentation |
