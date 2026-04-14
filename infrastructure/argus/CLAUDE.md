# Argus

**Claude's role in this directory: Project Manager for the Argus SIEM deployment.**
This service has not been implemented — both IaC directories are empty placeholders. Phase 3
has not begun. Do not write IaC here until Phase 3 is active.

When Phase 3 begins: read `docs/argus-design-doc-v1.2.md` in full before writing any IaC.
Check `.claude/agents/homelab-iac-specialist.md` for current VMID allocations before
assigning VMIDs to the planned LXCs.

See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.

## Definition of Done

- Splunk Free LXC deployed and receiving logs from all sources
- Wazuh Manager LXC deployed; Wazuh agents running on all SSH-accessible hosts
- Grafana LXC deployed; Argus dashboards operational
- n8n AI analysis pipeline running (query TimescaleDB → Ollama → enrich → alert every 5 min)
- Security alerts reaching the ntfy `argus` topic

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| Splunk Free | LXC (planned) | TBD | 10.0.50.20 | 8000 (UI), 9997 (forwarder) | 50 | Phase 3 |
| Wazuh Manager | LXC (planned) | TBD | 10.0.50.21 | 1514, 1515, 55000 (API) | 50 | Phase 3 |
| Grafana | LXC (planned) | TBD | 10.0.50.22 | 3000 | 50 | Phase 3 |
| Suricata | pfSense package | — | — | — | 10 | Phase 3 |
| Crowdsec | pfSense package | — | — | — | 10 | Phase 3 |
| Fail2ban | Per-host agent | — | — | — | All | Phase 3 |

Assign VMIDs from the available range (111–119) at deployment time. Confirm in
`.claude/agents/homelab-iac-specialist.md` before reserving.

## Role in Stack

**Depends on:**
- `platform/postgres` — `argus_logs` database (TimescaleDB hypertables — already deployed)
- `platform/n8n` — AI analysis pipeline
- `platform/ollama` — local LLM inference for threat analysis
- `iris` — syslog-ng + Vector log collection
- `network/pfsense` — syslog export, Suricata/Crowdsec packages

**Depended on by:**
- Mnemosyne — incidents stored as JOURNAL/REFERENCE entries
- ntfy `argus` topic — push alerts for security events

## IaC Layout

```
infrastructure/argus/
  ansible/     ← placeholder (.gitkeep) — not yet written
  terraform/   ← placeholder (.gitkeep) — not yet written
```

Write Terraform + Ansible from scratch when Phase 3 begins.

## Vault Variables

To be created when Phase 3 begins (follow `vault_<service>_<credential>` convention):
- `vault_splunk_password`
- `vault_wazuh_password`
- `vault_grafana_password`
- `vault_argus_password` — already exists in postgres group_vars (DB user)

## Notes

- Phase gate: Hermes (Phase 1) → Mnemosyne pipelines (Phase 2) → Argus (Phase 3)
- `argus_logs` database already exists on Postgres LXC (VMID 105) with TimescaleDB hypertables
- Suricata and Crowdsec are pfSense packages — no separate LXC, no VMID needed
- Fail2ban runs per-host — not a standalone service
- IaC conventions: see root `CLAUDE.md`
