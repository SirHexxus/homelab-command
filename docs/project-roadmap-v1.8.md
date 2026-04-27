# Homelab Command Project — Project Roadmap
**Version:** 2.0
**Last Updated:** 2026-04-27
**Philosophy:** See `docs/homelab-philosophy-v1.0.md` for the values and goals behind this homelab.

---

## Project Structure

### Homelab Command Project
All homelab infrastructure, security work, and portfolio documentation.
References Coding Project style guides for any scripting/development work.

### Coding Project (Separate)
General-purpose development standards and style guides.
- React/JavaScript Style Guide *(exists)*
- Bash Style Guide *(exists)*
- HTML/CSS/Vanilla JS Style Guide *(exists)*
- Directory System Guide *(exists)*
Not duplicated here — referenced by Homelab when scripting work arises.

### Career Advancement (Separate — tracked in Mnemosyne)
Cert prep and job applications are tracked as Projects and Pursuits in Mnemosyne:
- Pursuit — Career Advancement
- Project — Google Cybersecurity Professional Certificate
- Project — CompTIA Security+ Certification
- Project — Kaiser Permanente CRDC Consultant III Application

These are *current pursuits* of this homelab (see Philosophy doc), not its identity.
They have been removed from this roadmap to keep scope clean.

---

## Document Registry

### Completed
| Document | Version | Status |
|----------|---------|--------|
| Hardware Catalog | v1.2 | ✅ Complete |
| Network & Services Architecture | v1.6 | ✅ Complete |
| Homelab Philosophy | v1.0 | ✅ Complete |
| Project Roadmap | v1.9 | ✅ This document |
| Mnemosyne Design Doc | v1.2 | ✅ Complete |
| IaC Runbook | v1.2 | ✅ Complete |
| Argus Design Doc | v1.2 | ✅ Complete |
| Orpheus Design Doc | v1.1 | ✅ Complete |
| Hermes Design Doc | v1.0 | ✅ Complete |
| Ariadne Design Doc | v1.0 | ✅ Complete |

### Remaining
| Document | Version | Status |
|----------|---------|--------|
| Iris Design Doc | v1.0 | 🔲 Planned — authoring follow-on after rename |
| Home Assistant Design Doc | v1.0 | 🔲 Planned (Post-June) |
| AD + Authentik Design Doc | v1.0 | 🔲 Planned (Post-June) |
| Productivity Stack Design Doc | v1.0 | 🔲 Planned (Post-June) — Nextcloud, Vaultwarden (existing instance on TrueNAS; migrate to Hephaestus) |

---

## Current pursuits & timeline

The phases below support the homelab's core purpose: skill building, portfolio, and family
services. Current external pursuits (certs, job application) are tracked separately in Mnemosyne.
See `docs/homelab-philosophy-v1.0.md` for the full context.

**Original timeline:** 16 weeks from February 16, 2026. Phases have slipped — targets below
reflect revised estimates as of 2026-04-16.

---

## Phase 1 — Infrastructure Foundation
**Duration:** Weeks 1–4 | **Original Target:** March 15, 2026 | **Status:** Complete (minor tail)

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
- [x] Write pfSense Terraform IaC (infrastructure/network/pfsense/terraform/) — VM provisioning
- [x] Write pfSense full Ansible firewall IaC — all VLANs, aliases, idempotent
- [x] Export + commit pfSense XML config backup to infrastructure/network/pfsense/config.xml
- [x] VLAN 80 (Media): pfSense firewall rules + switch trunk/port IaC applied

### Bare Metal
- [x] Provision helm-log baseline hardening (10.0.10.25) — fail2ban, SSH, dotfiles
- [x] Set pfSense static DHCP reservation for helm-log (MAC 72:c6:b9:0d:32:ac → 10.0.10.25)
- [x] Run ntfy provisioning playbook on helm-log
- [x] Write Ansible post-install playbook for Proxmox (infrastructure/proxmox/ansible/) — bridges, storage pools, users, DNS
- [x] proxmox_base: add repos.yml — disable enterprise repo, enable no-subscription, fix Ceph sources, remove subscription nag, disable HA services
- [x] Research Proxmox Backup Server (PBS) — decision: PBS LXC on Proxmox node, datastore on TrueNAS NFS; implement when TrueNAS reconnected
- [x] Iris SSH recovery runbook added to Ansible docs

### Services (IaC — Terraform + Ansible)
- [x] Deploy n8n (10.0.50.13) — LXC 107
- [x] Deploy Postgres with pgvector + TimescaleDB (10.0.50.14) — LXC 105
- [x] Deploy Redis (10.0.50.15) — LXC 106
- [x] Deploy MinIO (10.0.50.16) — LXC 108
- [x] Verify Ollama + nomic-embed-text + Mistral 7B (10.0.50.10)
- [x] Verify Whisper operational (10.0.50.12)
- [x] Retire Qdrant (10.0.50.11) once Postgres pgvector confirmed stable
- [x] Reconnect R710 TrueNAS to network
- [x] Deploy Hermes LXC (10.0.50.17) — LXC 110 via Terraform + Ansible
- [x] Verify Hermes Phase 1 operational (CLI + Ollama + filesystem/shell skills)
- [x] Research TrueNAS Scale IaC — Ansible (truenas.truenas collection) and/or REST API for managing network config and app deployment as code

### Ariadne (DMZ)
- [x] Deploy nginx + certbot (10.0.60.10) — native reverse proxy; no Docker inside LXC
- [x] Deploy Authelia (10.0.60.11)
- [x] Deploy Umami (10.0.50.18) — analytics for sirhexx.com / hexxusweb.com
- [x] Ariadne IaC: NPM, Authelia, Umami provisioning roles
- [x] Ariadne IaC: media_proxy role (8 domain configs)
- [x] Ariadne IaC: ntfy reverse proxy role
- [x] TrueNAS UI: configure eno4 → 10.0.80.5/24 (gateway 10.0.80.1) *(manual — external to IaC)*
- [x] DNS: *.sirhexx.com wildcard record covers all media domains — no per-domain DNS work needed
- [x] SSL: certs already present for all 8 domains — confirmed by playbook run 2026-04-16

### GitHub
- [x] Create homelab-command repository
- [x] Commit all existing docs (Hardware Catalog, Network Architecture, Roadmap, Mnemosyne)
- [x] Establish IaC folder structure; commit all Terraform + Ansible from start
- [x] Commit network topology diagram (draw.io)

### Documentation
- [x] Complete Argus Design Doc v1.2
- [x] Complete Homelab Philosophy v1.0
- [x] Complete Ariadne Design Doc v1.0

### IaC Tooling / Claude Code Agents
- [x] Write `Agent_Creation_Guide.md` + `agent-template.md` (`~/code/best-practices/`)
- [x] Write global agents: devops-automator, technical-writer, security-engineer, workflow-optimizer
- [x] Write project agent: `homelab-iac-specialist` (`.claude/agents/`) — full VMID/IP topology
- [x] Create `hexxusweb-clients` repo with `hexxusweb-client-builder` project agent

---

## Phase 2 — Mnemosyne Pipeline
**Duration:** Weeks 5–7 | **Original Target:** April 5, 2026 | **Revised Target:** May 4, 2026

*Note: Cert prep items previously in this phase have been moved to Mnemosyne (Career Advancement pursuit).*

### Hermes (AI Agent) — ⚠️ BACK-BURNERED as of 2026-04-27
**Status:** Pipeline wired end-to-end but not reliably functional. Requires replanning before
resuming. Do not add Hermes tasks or invest further time without a dedicated replanning session.

**Blockers that caused back-burner decision:**
- Gemini free tier eliminated — cloud fallback no longer viable without billing
- Local models (qwen3:1.7b, qwen3:4b) too slow/small for multi-step ReAct loops on CPU
- Root cause: Hermes was designed around cloud LLM availability; local-first inference requires
  a GPU to be practical. Revisit when a GPU (e.g. RTX 3090) is available.

**What is complete and working:**
- [x] LLM router (Gemini + Claude clients, task_type routing)
- [x] Wiki skill (`lib/skills/wiki.py` — 7 read/write operations)
- [x] HTTP endpoint (`/task` + `/health`) for n8n integration
- [x] `IngestItem` dataclass (`lib/core/ingest.py`)
- [x] LXC deployed and live (10.0.50.17) — wiki repo cloned, systemd service running
- [x] n8n Telegram → Hermes ingest pipeline wired and tested
- [x] Async ingest with Telegram callback

**Remaining work (deferred — pending hold trigger):**
- [ ] Hermes Phase 3: Register Telegram bots (@BotFather) + implement `telegram_bot.py`
- [ ] Hermes Phase 5: n8n MCP integration (n8n at 10.0.50.13)
- [x] Replanning session: reconsider architecture — held 2026-04-27; hold triggers defined

**Hold triggers — Hermes resumes when any one occurs (hard expiry Jan 1 2027):**
- Bug Bounty Validation (tracked in Mnemosyne) produces a successful outcome
- Hexxus Web Solutions onboards a new client
- Jan 1 2027 — if neither above has occurred, Hermes is shuttered

### Mnemosyne (Wiki pipeline)
- [x] Architecture: Design doc updated to git wiki model; `SCHEMA.md` written; `IngestItem` spec documented
- [x] Foundation: Wiki scaffold created (`~/mneme/wiki/`) — 7 bucket directories, `SCHEMA.md`, `index.md`, `log.md`
- [x] Foundation: Create private GitHub remote for wiki repo; push initial scaffold
- [x] Foundation: Configure Obsidian vault + git plugin
- [x] Foundation: Install and configure Dataview plugin
**Interim path (active — Hermes not required):**
- [ ] n8n: modify Telegram webhook to write raw note to `wiki/inbox/` (text path; no LLM at ingest)
- [ ] Laptop: `inotifywait` daemon on `~/mneme/wiki/inbox/` — triggers `claude -p` on new files
- [ ] Laptop: hourly cron `claude -p` inbox sweep; silent if empty, ntfy notification if processed
  - Sleep window: 01:00–07:00; `!!` prefix in message bypasses sleep window
- [ ] Laptop: scheduled cron `claude -p` for Daily Digest and Weekly Summary reports
- [ ] Scripts documented and maintained in `infrastructure/mnemosyne/` in homelab-command repo

**Full pipeline (deferred — pending Hermes hold trigger):**
- [ ] Foundation: Grant Hermes LXC deploy key write access to wiki repo
- [ ] Ingest pipeline: n8n Telegram webhook — voice + file attachment paths
- [ ] Ingest pipeline: End-to-end test — Telegram note → wiki page → Obsidian (full pipeline)
- [ ] Retrieval: `/search` and `/ask` Telegram commands via Hermes ReAct loop
- [ ] Retrieval: n8n Chat Trigger as secondary capture/query interface
- [ ] Reports: Serendipity Engine, Idea Synthesis Report (require agent reasoning)
- [ ] Extended sources: Email ingestion, URL capture, Obsidian Web Clipper inbox processing

### Domain Migration (Namecheap → Porkbun)
> Transfer window is open as of ~April 2, 2026
- [ ] Create Porkbun account
- [ ] Recreate DNS records for all three domains in Porkbun DNS panel before transferring
- [ ] Unlock domains + request EPP/auth codes from Namecheap
- [ ] Initiate transfers for sirhexx.com, hexxusweb.com, bravelittlesalamander.com
- [ ] Approve transfers; update nameservers to Porkbun after each completes
- [ ] Configure DDNS on Porkbun for sirhexx.com

### IaC Tooling / Claude Code Agents
- [ ] Write project agent: `mnemosyne-pipeline-engineer` — n8n workflow architect for
  7-bucket wiki system; needs Ollama embed endpoint, n8n webhook URL, workflow JSON sample,
  `SCHEMA.md` from wiki repo, `IngestItem` dataclass definition
- [ ] Write project agent: `hermes-python-architect` — knows agent_loop.py, skill_registry.py,
  context.py, audit.py internals; needs skill registration snippet, context dataclass fields,
  audit.py pattern, `/opt/hermes/` layout post-provisioning
- [ ] Hermes Layer A: add `<!-- ollama-prompt -->` sections to security-engineer +
  workflow-optimizer agents (Mistral 7B-sized; store as `.md` files alongside each agent definition)

---

## Phase 3 — SIEM Stack (Argus Phase 1)
**Duration:** ~5–7 weeks | **Revised Target:** mid-June 2026

*Argus represents the first genuinely new domain in this project (SIEMs, detection engineering,
log pipelines). The timeline reflects real learning time, not just deployment time.*

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
- [ ] Write project agent: `incident-response-commander` — homelab stack; quarantine = Ansible → VLAN 66; MITRE ATT&CK mandatory
- [ ] Hermes Layer B: implement n8n quality gates — confidence gate, schema gate,
  idempotency gate (Mnemosyne); triage threshold gate, completeness gate (Argus)

### Documentation
- [ ] Complete DMZ Design Doc v1.0

---

## Phase 4 — Argus Phase 2 + DMZ Hardening
**Duration:** ~3–4 weeks | **Revised Target:** mid-July 2026

*(Previously "Phase 5" — cert prep phase removed, phases renumbered)*

### DMZ (VLAN 60)
- [ ] Hermes Phase 4: FastAPI web UI + NPM routing via Ariadne
- [ ] Configure WireGuard (pfSense package)
- [ ] Configure Squid (pfSense package)
- [ ] Configure pfSense Dynamic DNS (*.sirhexx.com wildcard → DNS provider)
- [ ] Configure Crowdsec (pfSense package)
- [ ] Configure Fail2ban per-host
- [ ] **OpenResty/Lua (low priority)** — swap nginx for OpenResty on 10.0.60.10 for dynamic Redis-backed routing, JWT validation, structured JSON access logs for Argus, custom rate limiting

### External Monitoring
- [ ] Provision external VPS (provider TBD)
- [ ] Deploy Uptime Kuma for outside-in monitoring

### Argus AI Pipeline
- [ ] n8n polls TimescaleDB every 5 min → Ollama/Claude summarization → Mnemosyne incident resources → Telegram alerts
- [ ] Build Ansible quarantine playbook: accepts IP/MAC → moves device to VLAN 66 → logs to Argus → optional Telegram alert

### IaC Tooling / Claude Code Agents
- [ ] Hermes Layer C: n8n MCP bridge — FastAPI service on n8n LXC (10.0.50.13) wrapping
  n8n REST API as MCP tools; Ansible role + `~/.claude/settings.json` MCP entry
- [ ] Write sites agent: `brand-guardian` — Deep Blue/Amber/Dark Gray palette, Rajdhani +
  Space Grotesk + JetBrains Mono; sirhexx.com (React/JSX) vs. hexxusweb.com (vanilla)
- [ ] Write global agent: `hexxus-voice` — synthesizes Voice + Visual Identity Guide;
  needs 2-3 writing samples + tone words from Voice Identity Guide

### Mnemosyne (Additional Workflows)
- [ ] Add email newsletter ingestion
- [ ] Build Periodic Entity Consolidation workflow
- [ ] Plan Google Keep bulk import

---

## Phase 5 — Portfolio & Application
**Duration:** ~2 weeks | **Revised Target:** late July / early August 2026

*(Previously "Phase 6")*

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
- [ ] **CRDC APPLICATION SUBMITTED** *(readiness target: late July 2026; actual submission window: mid-August 2026 after return from family trip July 25–Aug 12)*

---

## Deferred Projects (Post-Application)

| Project | Notes |
|---------|-------|
| Home Assistant | Design Doc planned |
| AD + Authentik (replace Authelia) | Mirrors enterprise identity architecture; Design Doc planned |
| Nextcloud + Vaultwarden (Productivity Stack) | Vaultwarden currently on TrueNAS pending migration to Hephaestus; Design Doc planned |
| Hardware upgrades (GPU, SSD, charger) | Budget-dependent |
| UniFi AP (replace eero) | Enables true IoT VLAN isolation for TV + Nintendo Switch |
| Google Keep bulk import | Post-Phase 4 |
| PBS deployment | Implement when TrueNAS eno4 is live and NFS share confirmed |

---

## Dependencies Map

```
Phase 1: Infrastructure Foundation ✅ (minor tail)
    └── Phase 2: Mnemosyne Pipeline (in progress)
            └── Phase 3: SIEM Stack / Argus Phase 1
                    └── Phase 4: Argus Phase 2 + DMZ Hardening
                            └── Phase 5: Portfolio → APPLICATION
```

---

## Related Projects

### Coding Project (Separate — not part of Homelab Command)
Houses general-purpose development standards referenced when scripting work arises.

### Career Advancement (Separate — tracked in Mnemosyne)
Google cert, Security+, and Kaiser application tracked as Projects under the
Career Advancement pursuit in Mnemosyne.

---

## Version History

- v2.0 (2026-04-27): Hermes replanning complete — hold triggers documented, replanning item checked off; Mnemosyne Phase 2 restructured into interim cron path (active) vs full pipeline (deferred); Phase 5 CRDC submission window adjusted to mid-August for family trip July 25–Aug 12
- v1.9 (2026-04-16): Full audit + re-sync — check off all completed work (Hermes LXC live,
  pfSense full firewall IaC, Ariadne media_proxy + ntfy proxy, Mnemosyne wiki scaffold,
  Iris SSH runbook, Ariadne Design Doc); extract cert prep to Mnemosyne Career Advancement
  pursuit; revise phase targets to reflect actual progress; remove Phase 4 (Security+) as
  standalone phase; renumber phases 5→4 and 6→5; file renamed v1.4→v1.8→v1.9
- v1.8 (2026-04-13): Update Phase 2 to reflect actual current state — Hermes Phase 2 items
  checked off, Mnemosyne section rewritten for git wiki model (Notion/pgvector architecture retired),
  IaC Tooling agent specs corrected
- v1.7 (2026-04-13): Remove "North Star" framing; replace with philosophy doc reference and
  Current Pursuits framing; add Homelab Philosophy to Document Registry
- v1.6 (2026-04-03): All Orpheus media services stay on TrueNAS Scale (no VLAN 80 LXC migration);
  Docker VM renamed Hephaestus; Portainer Server LXC back-burnered
- v1.5 (2026-03-18): Checked off switch trunk/access port configuration (applied to live switch today)
- v1.4 (2026-03-11): Added IaC Tooling / Claude Code Agents sections to Phases 1–3 and 5;
  marked Phase 1 agent work complete; documented Phase 2–5 agent deliverables with input
  dependencies
- v1.3 (2026-03-10): IaC Runbook — Proxmox node spec + tag-gated modularity standard

---

*Companion documents: Hardware Catalog v1.2 · Network & Services Architecture v1.6 · Mnemosyne Design Doc v1.2 · IaC Runbook v1.2 · Argus Design Doc v1.2 · Orpheus Design Doc v1.1 · Ariadne Design Doc v1.0 · Homelab Philosophy v1.0*
