# Homelab Command: Network & Services Architecture
**Version:** 1.4
**Last Updated:** February 2026
**Status:** Living Document — Update as architecture evolves

---

## Table of Contents
1. [Physical Network Topology](#1-physical-network-topology)
2. [VLAN Design](#2-vlan-design)
3. [IP Address Schema](#3-ip-address-schema)
4. [Firewall Architecture](#4-firewall-architecture)
5. [Services Inventory](#5-services-inventory)
6. [External Access & Domains](#6-external-access--domains)
7. [Second Brain & Argus](#7-second-brain--argus)
8. [Planned Migrations & Deployment Queue](#8-planned-migrations--deployment-queue)
9. [Open Items & Known Gaps](#9-open-items--known-gaps)

---

## 1. Physical Network Topology

```
[ISP / Cable Modem]
       |
       | (WAN -- Public IP)
       |
[Dell EMC PowerEdge T150]   <-- Proxmox 9.1.2 Hypervisor
  eno8303 (Port 1) = vmbr0  <-- WAN Bridge -> pfSense vtnet0
  eno8403 (Port 2) = vmbr1  <-- LAN/VLAN Bridge -> pfSense vtnet1
       |
       | (Trunk: VLAN 10, 20, 30, 50, 80 tagged — 40, 60, 66, 70 planned)
       |
[TP-Link T1600G-28PS] @ 10.0.10.50
  Port 1 = Trunk -> T150 (all VLANs)
       |
       |-- VLAN 10 (Management)
       |      |-- Proxmox WebGUI (10.0.10.2)
       |      |-- TP-Link Switch (10.0.10.50)
       |      |-- YoLink Hub (10.0.10.65)
       |      |-- James's Laptop, wired (10.0.10.x)
       |      |-- Portainer Server LXC (10.0.10.20) [NOT YET DEPLOYED]
       |
       |-- VLAN 20 (Personal)
       |      |-- eero Pro 6 (10.0.20.100) -- Bridge Mode
       |      |      SSID 1: "HUGE Tracts of LAN" -> VLAN 20
       |             |-- James's Laptop, WiFi (10.0.20.103)
       |             |-- James's Phone (10.0.20.104)
       |             |-- Wife's Laptop (10.0.20.101)
       |             |-- Wife's Phone (10.0.20.105)
       |             |-- Living Room TV (10.0.20.102) [eero SSID limit]
       |             |-- Nintendo Switch [eero SSID limit]
       |
       |-- VLAN 30 (Work)
       |      |-- Work Device (10.0.30.x)
       |      |-- Internet: ALLOWED | Internal: BLOCKED
       |
       |-- VLAN 50 (Lab Services)
       |      |-- Ollama (10.0.50.10) -- LXC 101
       |      |-- Whisper (10.0.50.12) -- LXC 102
       |      |-- Qdrant (10.0.50.11) -- LXC 103 [RETIRING -> pgvector]
       |      |-- n8n (10.0.50.13) -- LXC [NOT YET DEPLOYED]
       |      |-- Docker VM (10.0.50.30) -- VM [NOT YET DEPLOYED]
       |      |    |-- Portainer Agent (container)
       |      |    |-- Immich (container stack)
       |      |    |-- [future: Nextcloud, Vaultwarden]
       |      |-- [Planned: Postgres, Redis, MinIO, SIEM stack]
       |
       |-- VLAN 80 (Media) [PLANNED]
       |      |-- Jellyfin (10.0.80.X)
       |      |-- Audiobookshelf (10.0.80.X)
       |      |-- CalibreWeb (10.0.80.X)
       |      |-- Navidrome (10.0.80.X)
       |      |-- Jellyseerr (10.0.80.X)
       |      |-- [deferred: Komga, RomM]
       |
       |-- VLAN 40 (IoT) [PLANNED]
       |      |-- Smart switches, sensors
       |      |-- Note: TV and Switch remain on VLAN 20 (eero limitation)
       |
       |-- VLAN 60 (DMZ) [PLANNED]
       |      |-- NGINX Proxy Manager
       |      |-- WireGuard VPN (via pfSense package)
       |      |-- Squid forward proxy (via pfSense)
       |      |-- Authelia (SSO)
       |      |-- Crowdsec (behavioral IPS)
       |      |-- Fail2ban
       |
       |-- VLAN 66 (Sandbox) [PLANNED]
       |      |-- Isolated testing; quarantine target for Ansible playbook
       |
       |-- VLAN 70 (Guest) [PLANNED]
              |-- eero SSID 2: "Guest" -> VLAN 70
              |-- Temporary/untrusted WiFi devices; internet-only
```

> **Note:** Dell PowerEdge R710 (TrueNAS Scale) is currently **disconnected**. Reconnection pending. Target VLAN TBD (likely VLAN 10 or 50).

> **WiFi limitation:** eero Pro 6 supports 2 SSIDs in bridge mode. Nintendo Switch and Smart TV remain on VLAN 20 (Personal) until eero is replaced with a VLAN-capable AP (e.g., UniFi).

> **External monitoring:** Uptime Kuma will run on an external VPS (provider TBD) for outside-in service availability monitoring of DMZ endpoints.

---

## 2. VLAN Design

| VLAN | Name | Subnet | Gateway | Purpose |
|------|------|--------|---------|---------|
| 10 | Management | 10.0.10.0/24 | 10.0.10.1 | Infrastructure: Proxmox, switch, hub, admin workstation, Portainer Server |
| 20 | Personal | 10.0.20.0/24 | 10.0.20.1 | Family WiFi (SSID 1); identified personal devices |
| 30 | Work | 10.0.30.0/24 | 10.0.30.1 | KP work device; fully isolated from all internal networks |
| 40 | IoT | 10.0.40.0/24 | 10.0.40.1 | Smart switches, sensors; internet-only |
| 50 | Lab Services | 10.0.50.0/24 | 10.0.50.1 | Self-hosted services, AI stack, automation, SIEM, Docker VM |
| 60 | DMZ | 10.0.60.0/24 | 10.0.60.1 | Publicly facing services; reverse proxy, VPN, SSO, IPS |
| 66 | Sandbox | 10.0.66.0/24 | 10.0.66.1 | Isolated testing; quarantine target for compromised devices |
| 70 | Guest | 10.0.70.0/24 | 10.0.70.1 | Guest WiFi (SSID 2); internet-only, no internal access |
| 80 | Media | 10.0.80.0/24 | 10.0.80.1 | Media-serving services (Jellyfin, ABS, CalibreWeb, Navidrome); family-accessible |

> **DHCP convention:** Static IPs for infrastructure/services in .2-.50 range. DHCP dynamic pool in .100-.200 range.

---

## 3. IP Address Schema

### VLAN 10 -- Management

| Device | IP | Notes |
|--------|----|-------|
| pfSense | 10.0.10.1 | Gateway |
| Proxmox (T150) | 10.0.10.2 | Static; /etc/network/interfaces |
| Portainer Server LXC | 10.0.10.20 | Binary install (no Docker); manages Docker VM containers |
| TP-Link Switch | 10.0.10.50 | DHCP static mapping |
| YoLink Hub | 10.0.10.65 | DHCP static mapping |
| James's Laptop (wired) | 10.0.10.x | DHCP |

### VLAN 20 -- Personal

| Device | IP | Notes |
|--------|----|-------|
| pfSense | 10.0.20.1 | Gateway |
| eero Pro 6 | 10.0.20.100 | Bridge mode; DHCP static mapping |
| Wife's Laptop | 10.0.20.101 | DHCP |
| Living Room TV | 10.0.20.102 | DHCP; stays here (eero SSID limit) |
| James's Laptop (WiFi) | 10.0.20.103 | DHCP |
| James's Phone | 10.0.20.104 | DHCP |
| Wife's Phone | 10.0.20.105 | DHCP |
| Nintendo Switch | 10.0.20.x | DHCP; stays here (eero SSID limit) |

### VLAN 30 -- Work

| Device | IP | Notes |
|--------|----|-------|
| pfSense | 10.0.30.1 | Gateway (DNS only) |
| Work Device | 10.0.30.x | DHCP |

### VLAN 50 -- Lab Services

| Service | IP | Type | Notes |
|---------|----|------|-------|
| pfSense | 10.0.50.1 | Gateway | |
| Ollama | 10.0.50.10 | LXC 101 | IaC-deployed. AI inference. |
| Qdrant | 10.0.50.11 | LXC 103 | RETIRING — replaced by Postgres pgvector |
| Whisper | 10.0.50.12 | LXC 102 | IaC-deployed. Speech-to-text. |
| n8n | 10.0.50.13 | LXC (planned) | Previously on TrueNAS; needs IaC redeploy |
| Postgres | 10.0.50.14 | LXC (planned) | second_brain + argus_logs; pgvector + TimescaleDB |
| Redis | 10.0.50.15 | LXC (planned) | Ephemeral/session cache |
| MinIO | 10.0.50.16 | LXC (planned) | S3-compatible object storage |
| Splunk Free | 10.0.50.20 | LXC (planned) | SIEM log aggregation |
| Wazuh Manager | 10.0.50.21 | LXC (planned) | Host-based IDS |
| Grafana | 10.0.50.22 | LXC (planned) | TimescaleDB dashboards |
| Docker VM | 10.0.50.30 | VM (planned) | Shared Docker Compose host; Portainer Agent + Immich + future services |

### VLAN 60 -- DMZ (Planned)

| Service | IP | Notes |
|---------|----|-------|
| pfSense | 10.0.60.1 | Gateway |
| NGINX Proxy Manager | 10.0.60.10 | Reverse proxy + SSL termination |
| WireGuard VPN | pfSense pkg | VPN termination at firewall |
| Squid | pfSense pkg | Outbound forward proxy / filtering |
| Crowdsec | pfSense pkg | Behavioral IPS; pfSense package — no standalone IP |
| Authelia | 10.0.60.11 | SSO layer; OIDC/OAuth2; sits in front of NPM |
| Fail2ban | per-host | On all SSH-accessible hosts and NPM |

> **Uptime Kuma:** Deployed externally on a VPS (provider TBD). Monitors DMZ service availability from outside the network.

> **Post-June planned addition:** Active Directory VM (Proxmox) + Authentik replacing Authelia; federated identity with AD as source of truth.

### VLAN 40 -- IoT (Planned)

| Device | Target IP | Notes |
|--------|-----------|-------|
| YoLink Door Sensors (2x) | -- | Managed via YoLink Hub on VLAN 10 |
| Smart Switches (brand TBD) | 10.0.40.x | Confirm HA compatibility first |
| Future AP | -- | VLAN-capable AP replacement enables TV + Switch migration |

### VLAN 66 -- Sandbox (Planned)

| Purpose | Notes |
|---------|-------|
| Risky/compromised system testing | Fully isolated; no internal or internet access by default |
| Ansible quarantine target | quarantine.yml playbook moves devices here during IR |

### VLAN 80 -- Media (Planned)

| Service | IP | Type | Notes |
|---------|----|------|-------|
| pfSense | 10.0.80.1 | Gateway | |
| Jellyfin | TBD (10.0.80.X) | LXC | Movies, TV, Kids, Internet video |
| Audiobookshelf | TBD (10.0.80.X) | LXC | Audiobooks + podcasts |
| CalibreWeb | TBD (10.0.80.X) | LXC | Ebooks (fiction, non-fiction, reference) |
| Navidrome | TBD (10.0.80.X) | LXC | Music streaming |
| Jellyseerr | TBD (10.0.80.X) | LXC | Family media request UI |
| Komga | TBD (10.0.80.X) | LXC | Comics/Manga (deferred post-June) |
| RomM | TBD (10.0.80.X) | LXC | ROMs + EmulatorJS (deferred post-June) |

IPs assigned at deployment time. All VLAN 80 LXCs mount media from TrueNAS via NFS.

> **Media file storage:** R710 TrueNAS holds all media files on ZFS. *Arr stack (Radarr, Sonarr, Lidarr, Readarr, Prowlarr, Bazarr, qBittorrent) runs as TrueNAS Scale apps. See Media Stack Design Doc v1.1.

---

## 4. Firewall Architecture

**Firewall:** pfSense CE (VM 200 on T150)
- WAN: vtnet0 -> eno8303 (vmbr0)
- LAN/VLAN: vtnet1 -> eno8403 (vmbr1), VLAN-aware

### Rules by Interface

**VLAN 10 -- Management**
- Pass: Management -> Any (full administrative access)

**VLAN 20 -- Personal** (Verified operational)
- Pass: Personal -> Internet
- Block: Personal -> Management (10.0.10.0/24)
- Block: Personal -> Lab Services (10.0.50.0/24)

**VLAN 30 -- Work** (Verified operational)
```
1. Pass   | 10.0.30.0/24 -> 10.0.30.1       | Gateway/DNS
2. Block  | 10.0.30.0/24 -> 10.0.0.0/8      | Block all internal
3. Pass   | 10.0.30.0/24 -> !10.0.0.0/8     | Allow internet
Floating: Block | !10.0.30.0/24 -> 10.0.30.0/24  | Block internal -> Work
```

**VLAN 50 -- Lab Services** (Verified operational)
```
1. Pass   | 10.0.10.0/24 -> LAB subnets     | Management -> Lab
2. Block  | LAB subnets  -> 10.0.0.0/8      | Block Lab -> Internal (logged)
3. Pass   | LAB subnets  -> !10.0.0.0/8     | Allow internet
```

**VLAN 40 -- IoT (Planned)**
- Pass: IoT -> Internet only
- Block: IoT -> All internal VLANs
- Pass: Management -> IoT (for Home Assistant)

**VLAN 60 -- DMZ (Planned)**
- Pass: DMZ -> Internet
- Block: DMZ -> All internal VLANs
- Inbound NAT rules per exposed service (NPM handles routing internally)
- WireGuard: inbound UDP on designated port -> pfSense WG interface

**VLAN 66 -- Sandbox (Planned)**
- Block: Sandbox -> All internal VLANs
- Block: Sandbox -> Internet (default; enable case-by-case)

**VLAN 70 -- Guest (Planned)**
- Pass: Guest -> Internet only
- Block: Guest -> All internal VLANs

---

## 5. Services Inventory

### Currently Running

| Service | Host | IP | Purpose | Status |
|---------|------|----|---------|--------|
| pfSense CE | T150 VM 200 | 10.0.10.1 | Firewall/router/DHCP/DNS | Operational |
| Proxmox 9.1.2 | T150 | 10.0.10.2 | Hypervisor | Operational |
| Ollama | T150 LXC 101 | 10.0.50.10 | Local LLM inference | Operational |
| Qdrant | T150 LXC 103 | 10.0.50.11 | Vector DB (retiring) | Operational -> Retiring |
| Whisper | T150 LXC 102 | 10.0.50.12 | Speech-to-text | Operational |
| TrueNAS Scale | R710 | -- | NAS / ZFS storage | Disconnected |

### Planned Services

| Service | Target IP | Priority | Purpose |
|---------|-----------|----------|---------|
| n8n | 10.0.50.13 | HIGH | Workflow automation; IaC redeploy |
| Postgres | 10.0.50.14 | HIGH | second_brain DB + argus_logs; pgvector + TimescaleDB |
| Redis | 10.0.50.15 | HIGH | Session cache, dedup |
| MinIO | 10.0.50.16 | MEDIUM | S3 object storage |
| Splunk Free | 10.0.50.20 | HIGH | SIEM log aggregation |
| Wazuh Manager | 10.0.50.21 | HIGH | Host-based IDS |
| Suricata | pfSense pkg | HIGH | Network IDS |
| Crowdsec | pfSense pkg | HIGH | Behavioral IPS; pfSense package integration |
| Grafana | 10.0.50.22 | MEDIUM | TimescaleDB visualization |
| Docker VM | 10.0.50.30 | MEDIUM | Shared Docker Compose host (Immich, future Nextcloud/Vaultwarden) |
| Portainer Server LXC | 10.0.10.20 | MEDIUM | Docker container management UI (binary install, no Docker) |
| NGINX Proxy Manager | 10.0.60.10 | MEDIUM | Reverse proxy + SSL |
| WireGuard VPN | pfSense pkg | MEDIUM | VPN access |
| Squid | pfSense pkg | MEDIUM | Outbound forward proxy |
| Authelia | 10.0.60.11 | MEDIUM | SSO / identity layer |
| Fail2ban | per-host | MEDIUM | SSH + service brute force protection |
| Uptime Kuma | External VPS | LOW | Outside-in service monitoring |
| Jellyfin | 10.0.80.X | MEDIUM | Media server (VLAN 80) |
| Immich | 10.0.50.30 (Docker VM) | MEDIUM | Photo library; Google Photos replacement |
| Audiobookshelf | 10.0.80.X | MEDIUM | Audiobooks + podcasts (VLAN 80) |
| CalibreWeb | 10.0.80.X | MEDIUM | Ebook serving (VLAN 80) |
| Navidrome | 10.0.80.X | MEDIUM | Music streaming (VLAN 80) |
| Jellyseerr | 10.0.80.X | MEDIUM | Family media request UI (VLAN 80) |
| Home Assistant | 10.0.10.x | LOW | IoT hub (post-June) |
| Pi-hole | 10.0.10.x | LOW | DNS ad-blocking |

---

## 6. External Access & Domains

### 6.1 Owned Domains

| Domain | Purpose | Notes |
|--------|---------|-------|
| sirhexx.com | Personal services — all homelab external access subdomains | Primary domain for self-hosted service exposure via NPM |
| hexxusweb.com | Professional / portfolio-facing | Reserved for career and work-related use |
| bravelittlesalamander.com | Wife's domain | Held for future use |

All external service exposure routes through NGINX Proxy Manager (10.0.60.10) in the DMZ. Subdomains are defined per-service and documented in the relevant Design Doc (see Media Stack Design Doc v1.1 §8 for current known subdomain assignments).

### 6.2 DNS Architecture

External DNS for sirhexx.com resolves to the WAN IP (dynamic — managed via DDNS or manual update). NPM handles subdomain routing internally via reverse proxy rules. No internal services are exposed directly — all traffic enters through NPM.

Internal DNS resolution is handled by pfSense (DNS Resolver). Static mappings for all service IPs are maintained in pfSense to allow hostname-based access on the LAN without relying on external DNS.

---

## 7. Second Brain & Argus

The Second Brain (personal knowledge management / ADHD executive function support) and Argus (homelab SIEM layer) are two overlapping projects that share the VLAN 50 service infrastructure above. Their workflow designs, storage schemas, ingestion pipelines, and AI integration details are documented separately.

See: **Second Brain Design Doc** and **Argus Design Doc** (Homelab Command Project).

---

## 8. Planned Migrations & Deployment Queue

| Priority | Task | Dependency |
|----------|------|------------|
| HIGH | Deploy n8n via IaC on VLAN 50 | None -- do first |
| HIGH | Deploy Postgres + pgvector + TimescaleDB | n8n redeploy |
| HIGH | Deploy Redis | n8n redeploy |
| HIGH | Reconnect R710 (TrueNAS) | None |
| HIGH | Create VLANs 40, 60, 66, 70 in pfSense + switch | None |
| HIGH | Create VLAN 80 (Media) in pfSense + switch | None |
| HIGH | Create GitHub repo; commit existing docs + IaC | None |
| HIGH | Deploy Splunk Free + pfSense log forwarding | VLAN 50 stable |
| HIGH | Deploy Wazuh + endpoint agents | Splunk running |
| HIGH | Deploy Suricata + Crowdsec (pfSense packages) | pfSense configured |
| HIGH | Deploy Fail2ban on all SSH hosts + NPM | NPM deployed |
| MEDIUM | Rename VLAN 20 "Trusted" → "Personal" in pfSense + switch | None |
| MEDIUM | Deploy Portainer Server LXC (10.0.10.20) | None |
| MEDIUM | Deploy Docker VM (10.0.50.30) | None |
| MEDIUM | Deploy Immich on Docker VM | Docker VM running; TrueNAS NFS exports ready |
| MEDIUM | Deploy NPM, WireGuard, Squid, Authelia (VLAN 60) | VLAN 66 done |
| MEDIUM | Deploy Jellyfin + ABS + CalibreWeb + Navidrome (VLAN 80) | TrueNAS reconnected; library cleanup done |
| MEDIUM | Deploy Jellyseerr + *Arr stack | Jellyfin + TrueNAS ready |
| MEDIUM | Retire Qdrant LXC 103 once pgvector stable | Postgres deployed |
| MEDIUM | Deploy MinIO | None |
| MEDIUM | Deploy Grafana | TimescaleDB running |
| MEDIUM | Deploy Uptime Kuma on external VPS | VPS provisioned |
| LOW | Deploy Pi-hole | None |
| LOW | Deploy Home Assistant | VLAN 40 created |
| LOW | Source GPU (RTX 3060 or Intel Arc B580) | Budget |
| LOW | Evaluate Helm HPS20 repurpose | None |
| POST-JUNE | Active Directory VM + Authentik (replace Authelia) | After application |
| POST-JUNE | UniFi AP replacement for eero (true IoT VLAN isolation) | After application |
| POST-JUNE | Deploy Nextcloud + Vaultwarden on Docker VM | After application |

> **IaC convention:** All service containers deployed via Terraform + Ansible (repo: ~/projects/IaC-Projects/). Bridge: vmbr1. VLAN tag per schema above. Static IPs in .2-.50 range.

---

## 9. Open Items & Known Gaps

| # | Item | Action |
|---|------|--------|
| 1 | n8n not on VLAN 50 | Deploy via IaC at 10.0.50.13; restore all workflows |
| 2 | VLAN 20 not yet renamed in pfSense/switch | Rename interface to "Personal" |
| 3 | VLAN 40 (IoT) not created | Create in pfSense + switch |
| 4 | VLAN 60 (DMZ) not created | Create when DMZ services ready to deploy |
| 5 | VLAN 66 (Sandbox) not created | High priority; low effort; do next |
| 6 | VLAN 70 (Guest) not created | Prerequisite for eero SSID 2 (Guest) |
| 7 | VLAN 80 (Media) not created | Create before Media Stack deployment |
| 8 | R710 disconnected | Reconnect; assign static IP; restore TrueNAS; establish NFS exports |
| 9 | Postgres/Redis/MinIO not deployed | Core Second Brain/Argus data layer |
| 10 | Qdrant marked for retirement | Retire once pgvector tested and stable |
| 11 | SIEM stack not deployed | Splunk + Wazuh + Suricata + Crowdsec; SOC portfolio milestone |
| 12 | DMZ stack not deployed | NPM + WireGuard + Squid + Authelia + Fail2ban |
| 13 | Docker VM not deployed | 10.0.50.30; prerequisite for Immich + future Docker services |
| 14 | Portainer Server LXC not deployed | 10.0.10.20; VLAN 10; binary install |
| 15 | Media Stack LXCs not deployed | VLAN 80; requires TrueNAS reconnected + library cleanup |
| 16 | GitHub repo not created | Start in Phase 1; commit all existing docs immediately |
| 17 | Uptime Kuma VPS provider TBD | Evaluate options; deploy externally |
| 18 | Home Assistant not deployed | Requires VLAN 40 first; defer until post-June |
| 19 | GPU not sourced | RTX 3060 12GB or Intel Arc B580 |
| 20 | TrueNAS service history | Document what apps ran pre-migration |
| 21 | eero SSID limit | TV + Switch on VLAN 20; resolved by future AP upgrade |
| 22 | Crowdsec IP 10.0.60.12 freed | Crowdsec is pfSense package only; .12 address available |

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.1 · Project Roadmap v1.2 · Second Brain Design Doc v1.1 · IaC Runbook v1.1 · Argus Design Doc v1.1 · Media Stack Design Doc v1.1 · Ariadne Design Doc v1.0*
