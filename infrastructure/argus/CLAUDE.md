# Argus

AI-augmented homelab SIEM — combines Splunk, Wazuh, and Grafana with local LLM analysis via n8n
to provide continuous log monitoring, automated threat analysis, and Telegram-based incident response.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| Splunk Free | LXC (planned) | TBD | 10.0.50.20 | 8000 (UI), 9997 (forwarder) | 50 | Planned — Phase 3 |
| Wazuh Manager | LXC (planned) | TBD | 10.0.50.21 | 1514 (agents), 1515, 55000 (API) | 50 | Planned — Phase 3 |
| Grafana | LXC (planned) | TBD | 10.0.50.22 | 3000 | 50 | Planned — Phase 3 |
| Suricata | pfSense package | — | — | — | 10 | Planned |
| Crowdsec | pfSense package | — | — | — | 10 | Planned |
| Fail2ban | Per-host agent | — | — | — | All | Planned |

**Assign VMIDs from available range (111–119) when deploying.** Check `.claude/agents/homelab-iac-specialist.md` allocation table first.

## Role in Stack

**Depends on:**
- `platform/postgres` — `argus_logs` database (TimescaleDB hypertables)
- `platform/n8n` — AI analysis pipeline (query → Ollama → enrich → store, runs every 5 min)
- `platform/ollama` — local LLM inference for threat analysis
- `platform/redis` — (indirectly via n8n)
- `iris` — syslog-ng + Vector log collection (Phase 3)
- `network/pfsense` — pfSense syslog export + Suricata/Crowdsec packages

**Depended on by:**
- Mnemosyne — incidents stored as JOURNAL/REFERENCE entries
- ntfy `argus` topic — push alerts for security events

## IaC Layout

```
infrastructure/argus/
  ansible/     ← placeholder (.gitkeep) — Ansible not yet written
  terraform/   ← placeholder (.gitkeep) — Terraform not yet written
```

No IaC exists yet. Both directories are empty placeholders.
Write Terraform + Ansible from scratch when Phase 3 begins.

## Vault Variables

Variables to be created (follow `vault_<service>_<credential>` convention):
- `vault_splunk_password`
- `vault_wazuh_password`
- `vault_grafana_password`
- `vault_argus_password` already exists in postgres group_vars (DB user)

## Design Doc

`docs/argus-design-doc-v1.2.md` — full system diagram, log sources, AI analysis pipeline,
MITRE ATT&CK integration, Telegram bot design, data schema.

## Notes

- Argus is Phase 3 — Hermes must be deployed first (Phase 1), Mnemosyne schema second (Phase 2)
- `argus_logs` database already exists on the deployed Postgres LXC (VMID 105, 10.0.50.14)
  with TimescaleDB hypertables; schema is ready before LXC deployment
- Suricata and Crowdsec are pfSense packages — no separate LXC, no VMID needed
- Fail2ban runs on each SSH-accessible host — not a standalone service
- See root `CLAUDE.md` for IaC conventions (provider version, roles_path, vault naming)
