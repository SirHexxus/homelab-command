# Homelab Command: Network & Services Architecture
**Version:** 1.9
**Last Updated:** 2026-04-03
**Status:** Living Document — Update as architecture evolves

---

## Table of Contents
1. [Physical Network Topology](#1-physical-network-topology)
2. [VLAN Design](#2-vlan-design)
3. [IP Address Schema](#3-ip-address-schema)
4. [Firewall Architecture](#4-firewall-architecture)
5. [Services Inventory](#5-services-inventory)
6. [External Access & Domains](#6-external-access--domains)
7. [Mnemosyne, Argus, and Iris](#7-mnemosyne-argus-and-iris)
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
       | (Trunk: all VLANs tagged — 10, 20, 30, 40, 50, 60, 66, 70, 80)
       |
[TP-Link T1600G-28PS] @ 10.0.10.50
  Port 1 = Trunk -> T150 (all VLANs)
       |
       |-- VLAN 10 (Management)
       |      |-- Proxmox WebGUI (10.0.10.2)
       |      |-- TP-Link Switch (10.0.10.50)
       |      |-- YoLink Hub (10.0.10.65)
       |      |-- James's Laptop, wired (10.0.10.x)
       |      |-- Helm HPS20 / helm-log (10.0.10.25) [ntfy :2586 IaC-deployed; Phase 3: syslog-ng + Vector]
       |      |-- Portainer Server LXC (10.0.10.20) [DEFERRED — back-burnered]
       |      |-- TrueNAS Scale / R710 (10.0.10.30)
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
       |      |-- Qdrant (10.0.50.11) -- RETIRED
       |      |-- n8n (10.0.50.13) -- LXC 107
       |      |-- Postgres (10.0.50.14) -- LXC 105
       |      |-- Redis (10.0.50.15) -- LXC 106
       |      |-- MinIO (10.0.50.16) -- LXC 108
       |      |-- Hephaestus (10.0.50.30) -- VM [NOT YET DEPLOYED]
       |      |    |-- wger (container stack)
       |      |    |-- [future: Nextcloud, Vaultwarden, Healthchecks, NetBox, Guacamole]
       |      |-- [Planned: SIEM stack]
       |
       |-- VLAN 80 (Media)
       |      |-- TrueNAS R710 eno4 (10.0.80.5) — Jellyfin, ABS, Navidrome, CalibreWeb, *Arr, qBittorrent [eno4 config pending]
       |      |-- Jellyseerr (10.0.80.X) — TrueNAS app
       |      |-- [deferred: Komga, RomM]
       |
       |-- VLAN 40 (IoT)
       |      |-- Smart switches, sensors
       |      |-- Note: TV and Switch remain on VLAN 20 (eero limitation)
       |
       |-- VLAN 60 (DMZ)
       |      |-- Ariadne nginx + certbot (10.0.60.10) — reverse proxy; ntfy + media + analytics proxied
       |      |-- Authelia (10.0.60.11) — SSO
       |      |-- WireGuard VPN (via pfSense package) [planned]
       |      |-- Squid forward proxy (via pfSense) [planned]
       |      |-- Crowdsec (behavioral IPS) [planned]
       |      |-- Fail2ban [planned]
       |
       |-- VLAN 66 (Sandbox)
       |      |-- Isolated testing; quarantine target for Ansible playbook
       |
       |-- VLAN 70 (Guest)
              |-- eero SSID 2: "Guest" -> VLAN 70
              |-- Temporary/untrusted WiFi devices; internet-only
```

> **Note:** Dell PowerEdge R710 (TrueNAS Scale) has two active NICs — eno1 (10.0.10.30, VLAN 10, management + PBS) and eno4 (10.0.80.5, VLAN 80, media serving). Media apps (Jellyfin, ABS, Navidrome, CalibreWeb, *Arr, qBittorrent) run directly on TrueNAS co-located with ZFS storage. VLAN 80 requires switch port 4 reconfigured as VLAN 80 untagged access port.

> **WiFi limitation:** eero Pro 6 supports 2 SSIDs in bridge mode. Nintendo Switch and Smart TV remain on VLAN 20 (Personal) until eero is replaced with a VLAN-capable AP (e.g., UniFi).

> **External monitoring:** Uptime Kuma will run on an external VPS (provider TBD) for outside-in service availability monitoring of DMZ endpoints.

---

## 2. VLAN Design

| VLAN | Name | Subnet | Gateway | Purpose |
|------|------|--------|---------|---------|
| 10 | Management | 10.0.10.0/24 | 10.0.10.1 | Infrastructure: Proxmox, switch, hub, admin workstation |
| 20 | Personal | 10.0.20.0/24 | 10.0.20.1 | Family WiFi (SSID 1); identified personal devices |
| 30 | Work | 10.0.30.0/24 | 10.0.30.1 | KP work device; fully isolated from all internal networks |
| 40 | IoT | 10.0.40.0/24 | 10.0.40.1 | Smart switches, sensors; internet-only |
| 50 | Lab Services | 10.0.50.0/24 | 10.0.50.1 | Self-hosted services, AI stack, automation, SIEM, Hephaestus |
| 60 | DMZ | 10.0.60.0/24 | 10.0.60.1 | Publicly facing services; reverse proxy, VPN, SSO, IPS |
| 66 | Sandbox | 10.0.66.0/24 | 10.0.66.1 | Isolated testing; quarantine target for compromised devices |
| 70 | Guest | 10.0.70.0/24 | 10.0.70.1 | Guest WiFi (SSID 2); internet-only, no internal access |
| 80 | Media | 10.0.80.0/24 | 10.0.80.1 | Media-serving services on TrueNAS R710 (Jellyfin, ABS, CalibreWeb, Navidrome, Immich, etc.); family-accessible |

> **DHCP convention:** Static IPs for infrastructure/services in .2-.50 range. DHCP dynamic pool in .100-.200 range.

---

## 3. IP Address Schema

### VLAN 10 -- Management

| Device | IP | Notes |
|--------|----|-------|
| pfSense | 10.0.10.1 | Gateway |
| Proxmox (T150) | 10.0.10.2 | Static; /etc/network/interfaces |
| Portainer Server LXC | 10.0.10.20 | DEFERRED — back-burnered; may not be deployed |
| TP-Link Switch | 10.0.10.50 | DHCP static mapping |
| YoLink Hub | 10.0.10.65 | DHCP static mapping |
| Helm HPS20 (helm-log) | 10.0.10.25 | Static DHCP reservation — MAC 72:c6:b9:0d:32:ac; ntfy broker :2586 |
| TrueNAS Scale (R710) | 10.0.10.30 | Static — eno1 MAC 00:26:b9:55:a7:6d; management + PBS |
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
| Qdrant | 10.0.50.11 | — | RETIRED — replaced by Postgres pgvector |
| Whisper | 10.0.50.12 | LXC 102 | IaC-deployed. Speech-to-text. OpenAI-compatible API on :9000 (`/v1/audio/transcriptions`). |
| n8n | 10.0.50.13 | LXC 107 | IaC-deployed. Workflow automation; wired to Postgres. |
| Postgres | 10.0.50.14 | LXC 105 | IaC-deployed. mnemosyne + argus_logs + n8n; pgvector + TimescaleDB + pg_cron. |
| Redis | 10.0.50.15 | LXC 106 | IaC-deployed. Session/ephemeral cache. |
| MinIO | 10.0.50.16 | LXC 108 | IaC-deployed. S3-compatible object storage. |
| Hermes | 10.0.50.17 | LXC (planned) | AI agent; Mnemosyne Postgres client + homelab automation |
| Umami | 10.0.50.18 | LXC 122 | IaC-deployed. Web analytics for Ariadne-proxied public services. |
| Splunk Free | 10.0.50.20 | LXC (planned) | SIEM log aggregation |
| Wazuh Manager | 10.0.50.21 | LXC (planned) | Host-based IDS |
| Grafana | 10.0.50.22 | LXC (planned) | TimescaleDB dashboards |
| Hephaestus | 10.0.50.30 | VM (planned) | Shared Docker Compose host; wger + future services (Nextcloud, Vaultwarden) |

### VLAN 60 -- DMZ

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

### VLAN 40 -- IoT

| Device | Target IP | Notes |
|--------|-----------|-------|
| YoLink Door Sensors (2x) | -- | Managed via YoLink Hub on VLAN 10 |
| Smart Switches (brand TBD) | 10.0.40.x | Confirm HA compatibility first |
| Future AP | -- | VLAN-capable AP replacement enables TV + Switch migration |

### VLAN 66 -- Sandbox

| Purpose | Notes |
|---------|-------|
| Risky/compromised system testing | Fully isolated; no internal or internet access by default |
| Ansible quarantine target | quarantine.yml playbook moves devices here during IR |

### VLAN 80 -- Media

| Service | IP | Type | Notes |
|---------|----|------|-------|
| pfSense | 10.0.80.1 | Gateway | |
| TrueNAS R710 (eno4) | 10.0.80.5 | Physical NIC | Media-serving interface — MAC 00:26:b9:55:a7:73; Jellyfin, ABS, Navidrome, CalibreWeb, *Arr stack, qBittorrent, Libation run here. Switch port 4 → VLAN 80 untagged. |
| Jellyseerr | TBD (10.0.80.X) | TrueNAS app | Family media request UI |
| Komga | TBD (10.0.80.X) | TrueNAS app | Comics/Manga (deferred post-June) |
| RomM | TBD (10.0.80.X) | TrueNAS app | ROMs + EmulatorJS (deferred post-June) |

Media apps run directly on TrueNAS R710 (co-located with ZFS storage, no NFS hop). VLAN 80 access via eno4 (10.0.80.5). *Arr stack + qBittorrent also stay on TrueNAS for direct pool access.

> **TrueNAS static routes (manual — UI only):** TrueNAS has two NICs with different gateways. Replies to internal VLANs must be routed back out eno4, not the default route (eno1 → 10.0.10.1). Three static routes are configured in TrueNAS UI (System → Network → Static Routes):
> - `10.0.20.0/24` via `10.0.80.1` — PERSONAL devices
> - `10.0.50.0/24` via `10.0.80.1` — LAB_SERVICES
> - `10.0.60.0/24` via `10.0.80.1` — DMZ (Ariadne reverse proxy)
>
> **Deferred:** Research TrueNAS Scale Ansible/API automation to manage these as IaC instead of manual UI config.

> **Media file storage:** R710 TrueNAS holds all media files on ZFS. *Arr stack (Radarr, Sonarr, Lidarr, Readarr, Prowlarr, Bazarr, qBittorrent) runs as TrueNAS Scale apps. See Orpheus Design Doc v1.1.

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

**VLAN 40 -- IoT** (Operational)
- Pass: IoT -> Internet only
- Block: IoT -> All internal VLANs
- Pass: Management -> IoT (for Home Assistant)

**VLAN 60 -- DMZ**
- Pass: DMZ -> Internet
- Block: DMZ -> All internal VLANs (except per-service allows for Ariadne backends)
- Service allows: Ariadne (10.0.60.10) → ntfy :2586, Umami :3000, all VLAN 80 media services, n8n :5678
- WireGuard: inbound UDP on designated port -> pfSense WG interface [planned]

**VLAN 66 -- Sandbox**
- Block: Sandbox -> All internal VLANs
- Block: Sandbox -> Internet (default; enable case-by-case)

**VLAN 70 -- Guest**
- Pass: Guest -> Internet only
- Block: Guest -> All internal VLANs

**VLAN 80 -- Media**
- Block: MEDIA -> ALL_RFC1918 (no lateral movement)
- Pass: MEDIA -> Internet (metadata APIs, torrents, updates)

---

## 5. Services Inventory

### Currently Running

| Service | Host | IP | Purpose | Status |
|---------|------|----|---------|--------|
| pfSense CE | T150 VM 200 | 10.0.10.1 | Firewall/router/DHCP/DNS | Operational |
| Proxmox 9.1.2 | T150 | 10.0.10.2 | Hypervisor | Operational |
| Ollama | T150 LXC 101 | 10.0.50.10 | Local LLM inference | Operational |
| Qdrant | — | 10.0.50.11 | Vector DB | Retired — replaced by pgvector on Postgres LXC 105 |
| Whisper | T150 LXC 102 | 10.0.50.12 | Speech-to-text (OpenAI-compatible API :9000) | Operational |
| n8n | T150 LXC 107 | 10.0.50.13 | Workflow automation | Operational |
| Postgres | T150 LXC 105 | 10.0.50.14 | mnemosyne + argus_logs + n8n; pgvector + TimescaleDB + pg_cron | Operational |
| Redis | T150 LXC 106 | 10.0.50.15 | Session/ephemeral cache | Operational |
| MinIO | T150 LXC 108 | 10.0.50.16 | S3-compatible object storage | Operational |
| Iris (helm-log, Helm HPS20) | Bare metal | 10.0.10.25 | Notification broker (ntfy); Phase 3: central log collector | Baseline operational; ntfy IaC-deployed (pending run) |
| TrueNAS Scale | R710 | 10.0.10.30 | NAS / ZFS storage; NFS host for VLAN 80 + PBS | Operational |
| Ariadne (nginx + certbot) | T150 LXC 120 | 10.0.60.10 | Reverse proxy + SSL. Proxies: ntfy, Umami, 8 media/automation services | Operational |
| Authelia | T150 LXC 121 | 10.0.60.11 | SSO / OIDC identity layer | Operational |

### Planned Services

| Service | Target IP | Priority | Purpose |
|---------|-----------|----------|---------|
| Hermes | 10.0.50.17 | MEDIUM | AI agent; Mnemosyne Postgres client + homelab automation |
| Splunk Free | 10.0.50.20 | HIGH | SIEM log aggregation |
| Wazuh Manager | 10.0.50.21 | HIGH | Host-based IDS |
| Suricata | pfSense pkg | HIGH | Network IDS |
| Crowdsec | pfSense pkg | HIGH | Behavioral IPS; pfSense package integration |
| Grafana | 10.0.50.22 | MEDIUM | TimescaleDB visualization |
| Hephaestus (Docker VM) | 10.0.50.30 | MEDIUM | Shared Docker Compose host (wger, future Nextcloud/Vaultwarden) |
| Portainer Server LXC | 10.0.10.20 | LOW (deferred) | Docker container management UI — back-burnered; may not be deployed |
| WireGuard VPN | pfSense pkg | MEDIUM | VPN access |
| Squid | pfSense pkg | MEDIUM | Outbound forward proxy |
| Fail2ban | per-host | MEDIUM | SSH + service brute force protection |
| Uptime Kuma | External VPS | LOW | Outside-in service monitoring |
| Jellyfin | 10.0.80.5 (TrueNAS) | MEDIUM | Media server — TrueNAS Scale app |
| Immich | 10.0.80.5 (TrueNAS) | MEDIUM | Photo library — TrueNAS Scale app |
| Audiobookshelf | 10.0.80.5 (TrueNAS) | MEDIUM | Audiobooks + podcasts — TrueNAS Scale app |
| CalibreWeb | 10.0.80.5 (TrueNAS) | MEDIUM | Ebook serving — TrueNAS Scale app |
| Navidrome | 10.0.80.5 (TrueNAS) | MEDIUM | Music streaming — TrueNAS Scale app |
| Jellyseerr | 10.0.80.5 (TrueNAS) | MEDIUM | Family media request UI — TrueNAS Scale app |
| Home Assistant | 10.0.10.x | LOW | IoT hub (post-June) |
| ntfy (notification broker) | 10.0.10.25 | HIGH (Now) | Homelab push notification broker on helm-log. Topics: provisioning, general-operations, argus. IaC-deployed; pending playbook run. |
| syslog-ng + Vector (log collector) | 10.0.10.25 | HIGH (Phase 3) | Central log ingestor for Argus; receives pfSense/Suricata/switch syslog, ships structured events to TimescaleDB on VLAN 50. Runs on Helm HPS20 (helm-log). Wazuh agent also runs on device. |
| Pi-hole | 10.0.10.x | LOW | DNS ad-blocking |

---

## 6. External Access & Domains

### 6.1 Owned Domains

| Domain | Purpose | Notes |
|--------|---------|-------|
| sirhexx.com | Personal services — all homelab external access subdomains | Primary domain for self-hosted service exposure via NPM |
| hexxusweb.com | Professional / portfolio-facing | Reserved for career and work-related use |
| bravelittlesalamander.com | Wife's domain | Held for future use |

All external service exposure routes through NGINX Proxy Manager (10.0.60.10) in the DMZ. Subdomains are defined per-service and documented in the relevant Design Doc (see Orpheus Design Doc v1.1 §8 for current known subdomain assignments).

### 6.2 DNS Architecture

External DNS for sirhexx.com resolves to the WAN IP (dynamic — managed via DDNS or manual update). NPM handles subdomain routing internally via reverse proxy rules. No internal services are exposed directly — all traffic enters through NPM.

Internal DNS resolution is handled by pfSense (DNS Resolver). Static mappings for all service IPs are maintained in pfSense to allow hostname-based access on the LAN without relying on external DNS.

---

## 7. Mnemosyne, Argus, and Iris

Mnemosyne (personal knowledge management / ADHD executive function support), Argus (homelab SIEM layer), and Iris (bare-metal log collector and notification broker, running on the Helm HPS20 at 10.0.10.25) are named projects sharing the homelab infrastructure above. Their workflow designs, storage schemas, ingestion pipelines, and AI integration details are documented separately.

See: **Mnemosyne Design Doc**, **Argus Design Doc**, and **Ariadne Design Doc** (Homelab Command Project). Iris design doc is planned.

---

## 8. Planned Migrations & Deployment Queue

| Priority | Task | Dependency |
|----------|------|------------|
| ✅ DONE | Deploy n8n via IaC on VLAN 50 (LXC 107) | — |
| ✅ DONE | Deploy Postgres + pgvector + TimescaleDB (LXC 105) | — |
| ✅ DONE | Deploy Redis (LXC 106) | — |
| ✅ DONE | Deploy MinIO (LXC 108) | — |
| ✅ DONE | Create VLAN 40 (IoT) in pfSense + switch | None |
| ✅ DONE | Create VLANs 60, 66, 70 in pfSense + switch | — |
| ✅ DONE | Create VLAN 80 (Media) in pfSense + switch; Ariadne media proxy deployed (8 configs) | — |
| HIGH | Run ntfy provisioning playbook on helm-log | helm-log accessible via SSH |
| HIGH | Create GitHub repo; commit existing docs + IaC | None |
| HIGH | Deploy Splunk Free + pfSense log forwarding | VLAN 50 stable |
| HIGH | Deploy Wazuh + endpoint agents | Splunk running |
| HIGH | Deploy Suricata + Crowdsec (pfSense packages) | pfSense configured |
| HIGH | Deploy Fail2ban on all SSH hosts + NPM | NPM deployed |
| MEDIUM | Deploy Hephaestus Docker VM (10.0.50.30) | None |
| DEFERRED | Deploy Portainer Server LXC (10.0.10.20) — back-burnered | May not be deployed |
| MEDIUM | Deploy NPM, WireGuard, Squid, Authelia (VLAN 60) | VLAN 66 done |
| MEDIUM | Configure Orpheus media services on TrueNAS (Jellyfin, ABS, CalibreWeb, Navidrome, Immich) | TrueNAS eno4 live; library cleanup done |
| MEDIUM | Deploy Jellyseerr + *Arr stack on TrueNAS | Jellyfin configured; TrueNAS ready |
| MEDIUM | Deploy Libation as custom Docker app on TrueNAS (headless/CLI mode) — auto-pull + decrypt Audible audiobooks into ABS library | ABS deployed + library dataset defined |
| ✅ DONE | Retire Qdrant LXC 103 | pgvector on Postgres confirmed stable |
| ✅ DONE | Reconnect R710 (TrueNAS) — live at 10.0.10.30 | — |
| MEDIUM | Deploy Grafana | TimescaleDB running |
| MEDIUM | Deploy Uptime Kuma on external VPS | VPS provisioned |
| LOW | Deploy Pi-hole | None |
| LOW | Deploy Home Assistant | VLAN 40 created |
| LOW | Source GPU (RTX 3060 or Intel Arc B580) | Budget |
| HIGH (Phase 3) | Deploy syslog-ng + Vector on Helm HPS20 (helm-log, 10.0.10.25) | Wazuh Manager deployed; Splunk running; pfSense syslog export configured |
| POST-JUNE | Active Directory VM + Authentik (replace Authelia) | After application |
| POST-JUNE | UniFi AP replacement for eero (true IoT VLAN isolation) | After application |
| POST-JUNE | Deploy Nextcloud + Vaultwarden on Hephaestus | After application |

> **IaC convention:** All service containers deployed via Terraform + Ansible (repo: ~/projects/IaC-Projects/). Bridge: vmbr1. VLAN tag per schema above. Static IPs in .2-.50 range.

---

## 9. Open Items & Known Gaps

| # | Item | Action |
|---|------|--------|
| 1 | ~~n8n not on VLAN 50~~ | ✅ Deployed LXC 107 (10.0.50.13) |
| 2 | VLAN 20 not yet renamed in pfSense/switch | Rename interface to "Personal" |
| 4 | ~~VLAN 60 (DMZ) not created~~ | ✅ Live. Ariadne (nginx + certbot) deployed at 10.0.60.10; Authelia at 10.0.60.11 |
| 5 | ~~VLAN 66 (Sandbox) not created~~ | ✅ Live. Firewall rules applied |
| 6 | ~~VLAN 70 (Guest) not created~~ | ✅ Live. Firewall rules applied |
| 7 | ~~VLAN 80 (Media) not created~~ | ✅ pfSense + switch IaC applied; 8 Ariadne proxy configs deployed. **Pending:** TrueNAS eno4 UI config (10.0.80.5/24), DNS, SSL |
| 8 | ~~R710 disconnected~~ | ✅ Live at 10.0.10.30 (VLAN 10). Next: establish NFS exports + DHCP static mapping in pfSense |
| 9 | ~~Postgres/Redis/MinIO not deployed~~ | ✅ Deployed — LXC 105/106/108 |
| 10 | ~~Qdrant marked for retirement~~ | ✅ Retired — LXC 103 destroyed |
| 11 | SIEM stack not deployed | Splunk + Wazuh + Suricata + Crowdsec; SOC portfolio milestone |
| 12 | DMZ stack not deployed | NPM + WireGuard + Squid + Authelia + Fail2ban |
| 13 | Hephaestus (Docker VM) not deployed | 10.0.50.30; wger + future Docker services |
| 14 | Portainer Server LXC — back-burnered | May not be deployed; deferred indefinitely |
| 15 | Orpheus LXCs not deployed | VLAN 80; requires TrueNAS reconnected + library cleanup |
| 16 | GitHub repo not created | Start in Phase 1; commit all existing docs immediately |
| 17 | Uptime Kuma VPS provider TBD | Evaluate options; deploy externally |
| 18 | Home Assistant not deployed | Requires VLAN 40 first; defer until post-June |
| 19 | GPU not sourced | RTX 3060 12GB or Intel Arc B580 |
| 20 | ~~TrueNAS service history~~ | ✅ Documented. SMB: media, photos, videos, test-share (general_pool). NFS: /mnt/general_pool/media (live). TrueNAS Scale apps inventory (as of 2026-03-17): **Running:** audiobookshelf, authentik-personal, baserow, calibre-web, dashy, drawio, freshrss, handbrake, home-assistant, immich, it-tools, jellyfin, metube, n8n, navidrome, nginx-proxy-manager, portainer, prowlarr, qbittorrent, radarr, redis, sonarr, syncthing, vaultwarden, wg-easy. **Deploying:** baserow-hexxusweb, ddns-updater, jellyseerr, stirling-pdf. **Stopped:** calibre. Note: *Arr stack (radarr, sonarr, prowlarr, qbittorrent) poorly configured — to be reconfigured on TrueNAS per Orpheus plan. n8n + redis duplicated on Proxmox (authoritative). NPM + WireGuard running here but planned for DMZ VLAN 60 on Proxmox. **Dataset cleanup required** — apps duplicated across general_pool + ssd_pool; test-share (97.99 GiB, likely Immich library — confirm before touching); no Orpheus dataset structure yet. DO NOT delete test-share until Immich storage path confirmed and data migrated to proper dataset. |
| 21 | eero SSID limit | TV + Switch on VLAN 20; resolved by future AP upgrade |
| 22 | Crowdsec IP 10.0.60.12 freed | Crowdsec is pfSense package only; .12 address available |
| 23 | ~~Helm HPS20 DHCP reservation~~ | ✅ Static mapping set in pfSense: MAC 72:c6:b9:0d:32:ac → 10.0.10.25 |

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.2 · Project Roadmap v1.3 · Mnemosyne Design Doc v1.1 · IaC Runbook v1.3 · Argus Design Doc v1.2 · Orpheus Design Doc v1.1 · Ariadne Design Doc v1.0*
