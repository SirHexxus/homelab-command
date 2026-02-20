# Homelab Command Project — Project Roadmap
**Version:** 1.2
**Last Updated:** February 2026
**North Star:** Kaiser Permanente CRDC Consultant III (SOC Analyst) — application target June 2, 2026

---

## Project Structure

### Homelab Command Project
All homelab infrastructure, security, CRDC certification prep, and portfolio work.
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
| Hardware Catalog | v1.1 | ✅ Complete |
| Network & Services Architecture | v1.4 | ✅ Complete |
| Project Roadmap | v1.2 | ✅ This document |
| Second Brain Design Doc | v1.1 | ✅ Complete |
| IaC Runbook | v1.1 | ✅ Complete |
| Argus Design Doc | v1.1 | ✅ Complete |
| Media Stack Design Doc | v1.1 | ✅ Complete |

### Remaining
| Document | Version | Status |
|----------|---------|--------|
| Ariadne Design Doc (DMZ & Perimeter) | v1.0 | ✅ Complete |
| Home Assistant Design Doc | v1.0 | 🔲 Planned (Post-June) |
| AD + Authentik Design Doc | v1.0 | 🔲 Planned (Post-June) |
| Productivity Stack Design Doc | v1.0 | 🔲 Planned (Post-June) — Nextcloud, Vaultwarden (existing instance on TrueNAS; migrate to Docker VM) |

---

## North Star & Timeline

**Target:** CRDC Consultant III (SOC Analyst) application — June 2, 2026
**Timeline:** 16 weeks from February 16, 2026

---

## Phase 1 — Infrastructure Foundation
**Duration:** Weeks 1–4 | **Target:** March 15, 2026

### Network
- [x] VLANs 10, 20, 30, 50 operational
- [ ] Create VLANs 40, 60, 66, 70 in pfSense
- [ ] Configure managed switch trunk/access ports for all VLANs
- [ ] Rename VLAN 20 "Trusted" → "Personal" in pfSense and switch

### Services (IaC — Terraform + Ansible)
- [ ] Deploy n8n (10.0.50.13)
- [ ] Deploy Postgres with pgvector + TimescaleDB (10.0.50.14)
- [ ] Deploy Redis (10.0.50.15)
- [ ] Deploy MinIO (10.0.50.16)
- [ ] Verify Ollama + nomic-embed-text + Mistral 7B (10.0.50.10)
- [ ] Verify Whisper operational (10.0.50.12)
- [ ] Retire Qdrant (10.0.50.11) once Postgres pgvector confirmed stable
- [ ] Reconnect R710 TrueNAS to network

### GitHub
- [ ] Create homelab-command repository
- [ ] Commit all existing docs (Hardware Catalog, Network Architecture, Roadmap, Second Brain)
- [ ] Establish IaC folder structure; commit all Terraform + Ansible from start

### Documentation
- [x] Complete Argus Design Doc v1.0

---

## Phase 2 — Google Cybersecurity Certificate + Second Brain Rebuild
**Duration:** Weeks 5–7 | **Target:** April 5, 2026

### Google Cybersecurity Certificate
- [ ] Complete Courses 5–8
- [ ] Certificate earned
- [ ] Resume updated

### Second Brain (Rebuild on VLAN 50)
- [ ] Create REFERENCE, JOURNAL, PURSUIT Notion databases; update IDs in Second Brain Design Doc
- [ ] Rebuild Telegram capture + classification workflow with model routing logic
- [ ] Add Entity Resolution step for Compound buckets
- [ ] Rebuild Notion database writes (all 7 buckets)
- [ ] Add pgvector embedding step to ingestion pipeline
- [ ] Test end-to-end: Telegram note → Postgres → Notion → confirmation
- [ ] Build /search and /ask Telegram commands
- [ ] Build Daily Digest and Serendipity Engine
- [ ] Build Weekly Summary and Idea Synthesis Report
- [ ] Add voice memo path (Telegram → Whisper → pipeline)

### Documentation
- [x] Complete Media Stack Design Doc v1.1

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
- [ ] Deploy NGINX Proxy Manager (10.0.60.10)
- [ ] Configure WireGuard (pfSense package)
- [ ] Configure Squid (pfSense package)
- [ ] Deploy Authelia (10.0.60.11)
- [ ] Configure Crowdsec (pfSense package)
- [ ] Configure Fail2ban per-host

### External Monitoring
- [ ] Provision external VPS (provider TBD)
- [ ] Deploy Uptime Kuma for outside-in monitoring

### Argus AI Pipeline
- [ ] n8n polls TimescaleDB every 5 min → Ollama/Claude summarization → Second Brain incident resources → Telegram alerts
- [ ] Build Ansible quarantine playbook: accepts IP/MAC → moves device to VLAN 66 → logs to Argus → optional Telegram alert

### Second Brain (Additional Workflows)
- [ ] Add email newsletter ingestion
- [ ] Build Periodic Entity Consolidation workflow
- [ ] Plan Google Keep bulk import

---

## Phase 6 — Portfolio & Application
**Duration:** Weeks 14–16 | **Target:** June 2, 2026

### GitHub Portfolio
- [ ] All docs committed: Hardware Catalog, Network Architecture, Second Brain, Argus, Media Stack, DMZ
- [ ] All IaC committed: Terraform + Ansible for all services
- [ ] Architecture diagrams (network, SIEM, Second Brain, Argus)

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
| Nextcloud + Vaultwarden (Productivity Stack) | Post-June; Vaultwarden currently on TrueNAS pending migration to Docker VM; Design Doc planned |
| Hardware upgrades (GPU, SSD, charger) | Budget-dependent |
| UniFi AP (replace eero) | Post-June; enables true IoT VLAN isolation for TV + Nintendo Switch |
| Google Keep bulk import | Post-Phase 5 |

---

## Dependencies Map

```
Phase 1: Infrastructure + GitHub + Argus Design Doc
    ├── Phase 2: Second Brain Rebuild + Google Cert + Media Stack Design Doc
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

*Companion documents: Hardware Catalog v1.1 · Network & Services Architecture v1.4 · Second Brain Design Doc v1.1 · IaC Runbook v1.1 · Argus Design Doc v1.1 · Media Stack Design Doc v1.1 · Ariadne Design Doc v1.0*
