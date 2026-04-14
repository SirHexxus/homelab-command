# Homelab Command Project — Project Roadmap
**Version:** 1.7
**Last Updated:** 2026-04-13
**Philosophy:** See `docs/homelab-philosophy-v1.0.md` for the values and goals behind this homelab.

---

## Project Structure

### Homelab Command Project
All homelab infrastructure, security work, certification prep, and portfolio documentation.
References Coding Project style guides for any scripting/development work.

### Coding Project (Separate)
General-purpose development standards and style guides.
- React/JavaScript Style Guide *(exists)*
- Bash Style Guide *(exists)*
- HTML/CSS/Vanilla JS Style Guide *(exists)*
- Directory System Guide *(exists)*
Not duplicated here — referenced by Homelab when scripting work arises.

---

## Document Registry

### Completed
| Document | Version | Status |
|----------|---------|--------|
| Hardware Catalog | v1.2 | ✅ Complete |
| Network & Services Architecture | v1.6 | ✅ Complete |
| Homelab Philosophy | v1.0 | ✅ Complete |
| Project Roadmap | v1.7 | ✅ This document |
| Mnemosyne Design Doc | v1.2 | ✅ Complete |
| IaC Runbook | v1.2 | ✅ Complete |
| Argus Design Doc | v1.2 | ✅ Complete |
| Orpheus Design Doc | v1.1 | ✅ Complete |
| Hermes Design Doc | v1.0 | ✅ Complete |

### Remaining
| Document | Version | Status |
|----------|---------|--------|
| Ariadne Design Doc (DMZ & Perimeter) | v1.0 | ✅ Complete |
| Iris Design Doc | v1.0 | 🔲 Planned — authoring follow-on after rename |
| Home Assistant Design Doc | v1.0 | 🔲 Planned (Post-June) |
| AD + Authentik Design Doc | v1.0 | 🔲 Planned (Post-June) |
| Productivity Stack Design Doc | v1.0 | 🔲 Planned (Post-June) — Nextcloud, Vaultwarden (existing instance on TrueNAS; migrate to Hephaestus) |

---

## Current pursuits & timeline

The phases below are structured around a current pursuit: the Kaiser Permanente CRDC Consultant III
(SOC Analyst) application, targeting June 2, 2026. This is a short-term goal, not the permanent
purpose of the homelab. See `docs/homelab-philosophy-v1.0.md` for the full list of current pursuits
and the goals that outlast any of them.

**Timeline:** 16 weeks from February 16, 2026

---

## Phase 1 — Infrastructure Foundation
**Duration:** Weeks 1–4 | **Target:** March 15, 2026

### Network
- [x] VLANs 10, 20, 30, 50 operational
- [x] Create VLAN 40 (IoT) in pfSense
- [x] Create VLAN 60 (DMZ) in pfSense
- [x] Create VLAN 66 (Sandbox) in pfSense
- [x] Create VLAN 70 (Guest) in pfSense
- [x] Configure managed switch trunk/access ports for all VLANs
- [x] Rename VLAN 20 "Trusted" → "Personal" in pfSense and switch
- [x] Research TP-Link T1600G-28PS automation — Telnet transport via ansible.netcommon.telnet
- [x] Implement switch configuration IaC (infrastructure/network/switch/)

### Bare Metal
- [x] Provision helm-log baseline hardening (10.0.10.25) — fail2ban, SSH, dotfiles
- [x] Set pfSense static DHCP reservation for helm-log (MAC 72:c6:b9:0d:32:ac → 10.0.10.25)
- [x] Run ntfy provisioning playbook on helm-log
- [x] Write Ansible post-install playbook for Proxmox (infrastructure/proxmox/ansible/) — bridges, storage pools, users, DNS
- [x] Research Proxmox Backup Server (PBS) — decision: PBS LXC on Proxmox node, datastore on TrueNAS NFS; implement when TrueNAS reconnected

### Services (IaC — Terraform + Ansible)
- [x] Deploy n8n (10.0.50.13) — LXC 107
- [x] Deploy Postgres with pgvector + TimescaleDB (10.0.50.14) — LXC 105
- [x] Deploy Redis (10.0.50.15) — LXC 106
- [x] Deploy MinIO (10.0.50.16) — LXC 108
- [x] Verify Ollama + nomic-embed-text + Mistral 7B (10.0.50.10)
- [x] Verify Whisper operational (10.0.50.12)
- [x] Retire Qdrant (10.0.50.11) once Postgres pgvector confirmed stable
- [ ] Research TrueNAS Scale IaC — Ansible (truenas.truenas collection) and/or REST API for managing network config (static routes, interfaces) and app deployment as code
- [x] Reconnect R710 TrueNAS to network
- [ ] Deploy Hermes LXC (10.0.50.17) — LXC 110 via Terraform + Ansible
- [ ] Verify Hermes Phase 1 operational (CLI + Ollama + filesystem/shell skills)
- [x] Write pfSense Terraform IaC (infrastructure/network/pfsense/terraform/) — VM provisioning
- [x] Export + commit pfSense XML config backup to infrastructure/network/pfsense/config.xml

### GitHub
- [x] Create homelab-command repository
- [x] Commit all existing docs (Hardware Catalog, Network Architecture, Roadmap, Mnemosyne)
- [x] Establish IaC folder structure; commit all Terraform + Ansible from start

### Documentation
- [x] Complete Argus Design Doc v1.0

### IaC Tooling / Claude Code Agents
- [x] Write `Agent_Creation_Guide.md` + `agent-template.md` (`~/code/best-practices/`)
- [x] Write global agent: `devops-automator` (`~/.claude/agents/`)
- [x] Write global agent: `technical-writer` (`~/.claude/agents/`)
- [x] Write global agent: `security-engineer` (`~/.claude/agents/`)
- [x] Write global agent: `workflow-optimizer` (`~/.claude/agents/`)
- [x] Write project agent: `homelab-iac-specialist` (`.claude/agents/`) — full VMID/IP topology
- [x] Create `hexxusweb-clients` repo with `hexxusweb-client-builder` project agent

---

## Phase 2 — Google Cybersecurity Certificate + Mnemosyne Rebuild
**Duration:** Weeks 5–7 | **Target:** April 5, 2026

### Hermes (AI Agent)
- [x] Hermes Phase 2: LLM router (Gemini + Claude clients, task_type routing)
- [x] Hermes Phase 2: Wiki skill (`lib/skills/wiki.py` — 7 read/write operations)
- [x] Hermes Phase 2: HTTP endpoint (`/task` + `/health`) for n8n integration
- [x] Hermes Phase 2: `IngestItem` dataclass (`lib/core/ingest.py`)
- [ ] Hermes Phase 2: Deploy Hermes LXC (10.0.50.17) — final Phase 2 item
- [ ] Hermes Phase 3: Register Telegram bots (@BotFather) + implement `telegram_bot.py`
- [ ] Hermes Phase 5: n8n MCP integration (n8n at 10.0.50.13)

### Google Cybersecurity Certificate
- [ ] Complete Courses 5–8
- [ ] Certificate earned
- [ ] Resume updated

### Mnemosyne (Wiki pipeline)
- [x] Architecture: Design doc updated to git wiki model; `SCHEMA.md` written; `IngestItem` spec documented
- [x] Foundation: Wiki scaffold created (`~/mneme/wiki/`) — 7 bucket directories, `SCHEMA.md`, `index.md`, `log.md`
- [ ] Foundation: Create private GitHub remote for wiki repo; configure Obsidian vault + git plugin + Dataview plugin
- [ ] Foundation: Grant Hermes LXC deploy key write access to wiki repo
- [ ] Ingest pipeline: n8n Telegram webhook workflow (text + voice + file attachment paths)
- [ ] Ingest pipeline: End-to-end test — Telegram note → wiki page → Obsidian
- [ ] Retrieval: `/search` and `/ask` Telegram commands via Hermes ReAct loop
- [ ] Retrieval: n8n Chat Trigger as secondary capture/query interface
- [ ] Reports: Daily Digest, Serendipity Engine, Weekly Summary, Idea Synthesis Report
- [ ] Extended sources: Email ingestion, URL capture, Obsidian Web Clipper inbox processing

### IaC Tooling / Claude Code Agents
- [ ] Write project agent: `mnemosyne-pipeline-engineer` — n8n workflow architect for
  7-bucket wiki system; needs Ollama embed endpoint, n8n webhook URL, workflow JSON sample,
  `SCHEMA.md` from wiki repo, `IngestItem` dataclass definition
- [ ] Write project agent: `hermes-python-architect` — knows agent_loop.py, skill_registry.py,
  context.py, audit.py internals; needs skill registration snippet, context dataclass fields,
  audit.py pattern, `/opt/hermes/` layout post-provisioning
- [ ] Hermes Layer A: add `<!-- ollama-prompt -->` sections to security-engineer +
  workflow-optimizer agents (Mistral 7B-sized; store as `.md` files alongside each agent definition)

### Domain Migration (Namecheap → Porkbun)
> Earliest eligible: ~April 2, 2026 (60-day ICANN transfer window from February renewal)
- [ ] Create Porkbun account
- [ ] Recreate DNS records for all three domains in Porkbun DNS panel before transferring
- [ ] Unlock domains + request EPP/auth codes from Namecheap
- [ ] Initiate transfers for sirhexx.com, hexxusweb.com, bravelittlesalamander.com
- [ ] Approve transfers; update nameservers to Porkbun after each completes
- [ ] Configure DDNS on Porkbun for sirhexx.com

### Documentation
- [x] Complete Orpheus Design Doc v1.1

---

## Phase 3 — SIEM Stack (Argus Phase 1)
**Duration:** Weeks 8–9 | **Target:** April 19, 2026

### Deployment
- [ ] Deploy Splunk Free (10.0.50.20)
- [ ] Deploy Wazuh Manager (10.0.50.21)
- [ ] Deploy Grafana (10.0.50.22)
- [ ] Configure Suricata (pfSense package)
- [ ] Configure Crowdsec (pfSense package)
- [ ] Configure Fail2ban on all SSH hosts + NPM

### Integration
- [ ] pfSense logs → Splunk
- [ ] Wazuh agents deployed on 5+ endpoints
- [ ] Suricata alerts → Splunk
- [ ] Grafana → TimescaleDB dashboards

### Portfolio
- [ ] Full SIEM architecture documented
- [ ] Architecture diagram committed to GitHub

### IaC Tooling / Claude Code Agents
- [ ] Write project agent: `argus-detection-engineer` — Splunk SPL, Suricata signatures,
  Wazuh decoders/rules, Crowdsec scenarios; needs top 5 threat scenarios, Wazuh mode
  (active-response vs. passive), one baseline SPL query, known FP sources
- [ ] Write project agent: `incident-response-commander` (argus project) — replaces generic
  SIEM with homelab stack; quarantine = Ansible → VLAN 66; MITRE ATT&CK mandatory
- [ ] Hermes Layer B: implement n8n quality gates — confidence gate, schema gate,
  idempotency gate (Mnemosyne); triage threshold gate, completeness gate (Argus)

### Documentation
- [ ] Complete DMZ Design Doc v1.0

---

## Phase 4 — Security+ Certification
**Duration:** Weeks 10–13 | **Target:** May 17, 2026

- [ ] Study all 6 domains alongside live SIEM data
- [ ] Practice exams at 85%+ consistently
- [ ] Exam scheduled
- [ ] Exam passed
- [ ] Resume updated with Security+

---

## Phase 5 — Argus Phase 2 + DMZ (Parallel with Phase 4)
**Duration:** Weeks 10–13 | **Target:** May 17, 2026

### DMZ (VLAN 60)
- [ ] Hermes Phase 4: FastAPI web UI + NPM routing via Ariadne
- [x] Deploy nginx + certbot (10.0.60.10) — native reverse proxy; no Docker inside LXC
- [ ] Configure WireGuard (pfSense package)
- [ ] Configure Squid (pfSense package)
- [ ] Configure pfSense Dynamic DNS (*.sirhexx.com wildcard → DNS provider)
- [ ] Deploy Authelia (10.0.60.11)
- [x] Deploy Umami (10.0.50.18) — analytics for sirhexx.com / hexxusweb.com
- [ ] Configure Crowdsec (pfSense package)
- [ ] Configure Fail2ban per-host
- [ ] **OpenResty/Lua (low priority)** — swap nginx for OpenResty on 10.0.60.10 to enable Lua scripting: dynamic Redis-backed routing (instant `rpadd` without nginx reload), JWT validation, structured JSON access logs for Argus, custom rate limiting

### External Monitoring
- [ ] Provision external VPS (provider TBD)
- [ ] Deploy Uptime Kuma for outside-in monitoring

### Argus AI Pipeline
- [ ] n8n polls TimescaleDB every 5 min → Ollama/Claude summarization → Mnemosyne incident resources → Telegram alerts
- [ ] Build Ansible quarantine playbook: accepts IP/MAC → moves device to VLAN 66 → logs to Argus → optional Telegram alert

### IaC Tooling / Claude Code Agents
- [ ] Hermes Layer C: n8n MCP bridge — FastAPI service on n8n LXC (10.0.50.13) wrapping
  n8n REST API as MCP tools (`list_workflows`, `trigger_workflow`, `get_execution`,
  `get_workflow_runs`); Ansible role + `~/.claude/settings.json` MCP entry;
  **dependency:** n8n API key provisioned + Hermes Phase 2 complete
- [ ] Write sites agent: `brand-guardian` — Deep Blue/Amber/Dark Gray palette, Rajdhani +
  Space Grotesk + JetBrains Mono; sirhexx.com (React/JSX) vs. hexxusweb.com (vanilla)
- [ ] Write global agent: `hexxus-voice` — synthesizes Voice Identity Guide + Visual
  Identity Guide; needs 2-3 writing samples + tone words from Voice Identity Guide

### Mnemosyne (Additional Workflows)
- [ ] Add email newsletter ingestion
- [ ] Build Periodic Entity Consolidation workflow
- [ ] Plan Google Keep bulk import

---

## Phase 6 — Portfolio & Application
**Duration:** Weeks 14–16 | **Target:** June 2, 2026

### GitHub Portfolio
- [ ] All docs committed: Hardware Catalog, Network Architecture, Mnemosyne, Argus, Orpheus, DMZ
- [ ] All IaC committed: Terraform + Ansible for all services
- [ ] Architecture diagrams (network, SIEM, Mnemosyne, Argus)

### Case Studies
- [ ] Case Study 1: Zero Trust network + VLAN segmentation
- [ ] Case Study 2: SIEM deployment + detection engineering
- [ ] Case Study 3: AI-assisted monitoring (Argus) + quarantine automation

### Application
- [ ] Resume tailored for CRDC Consultant III
- [ ] STAR responses prepared for behavioral questions
- [ ] Mock interviews completed
- [ ] **CRDC APPLICATION SUBMITTED — June 2, 2026**

---

## Deferred Projects (Post-June)

| Project | Notes |
|---------|-------|
| Home Assistant | Post-June; Design Doc planned |
| AD + Authentik (replace Authelia) | Post-June; mirrors enterprise identity architecture; Design Doc planned |
| Nextcloud + Vaultwarden (Productivity Stack) | Post-June; Vaultwarden currently on TrueNAS pending migration to Hephaestus; Design Doc planned |
| Hardware upgrades (GPU, SSD, charger) | Budget-dependent |
| UniFi AP (replace eero) | Post-June; enables true IoT VLAN isolation for TV + Nintendo Switch |
| Google Keep bulk import | Post-Phase 5 |

---

## Dependencies Map

```
Phase 1: Infrastructure + GitHub + Argus Design Doc
    ├── Phase 2: Mnemosyne Rebuild + Google Cert + Orpheus Design Doc
    └── Phase 3: SIEM Stack + DMZ Design Doc
            ├── Phase 4: Security+ (study alongside SIEM)
            └── Phase 5: Argus AI + DMZ + Quarantine
                    └── Phase 6: Portfolio → CRDC APPLICATION
```

---

## Related Projects

### Coding Project (Separate — not part of Homelab Command)
Houses general-purpose development standards referenced when scripting work arises in this project.
- React/JavaScript Style Guide
- Bash Style Guide
- HTML/CSS/Vanilla JS Style Guide
- Directory System Guide

---

---

## Version History

- v1.8 (2026-04-13): Update Phase 2 to reflect actual current state — Hermes Phase 2 items checked off, Mnemosyne section rewritten for git wiki model (Notion/pgvector architecture retired), IaC Tooling agent specs corrected
- v1.7 (2026-04-13): Remove "North Star" framing; replace with philosophy doc reference and Current Pursuits framing; add Homelab Philosophy to Document Registry
- v1.6 (2026-04-03): All Orpheus media services stay on TrueNAS Scale (no VLAN 80 LXC migration); Docker VM renamed Hephaestus; Portainer Server LXC back-burnered
- v1.5 (2026-03-18): Checked off switch trunk/access port configuration (applied to live switch today)
- v1.4 (2026-03-11): Added IaC Tooling / Claude Code Agents sections to Phases 1–3 and 5;
  marked Phase 1 agent work complete; documented Phase 2–5 agent deliverables with input
  dependencies; audited against repo — marked ntfy provisioning, TP-Link research + IaC, PBS
  research, Proxmox post-install Ansible, pfSense Terraform all complete; fixed Document Registry
  version numbers (Network Architecture v1.6, IaC Runbook v1.2)
- v1.3 (2026-03-10): IaC Runbook — Proxmox node spec + tag-gated modularity standard

---

*Companion documents: Hardware Catalog v1.2 · Network & Services Architecture v1.7 · Mnemosyne Design Doc v1.1 · IaC Runbook v1.3 · Argus Design Doc v1.2 · Orpheus Design Doc v1.1 · Ariadne Design Doc v1.0*
