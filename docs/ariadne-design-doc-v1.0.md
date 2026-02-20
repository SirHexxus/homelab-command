# Ariadne Project — DMZ & Perimeter Design Doc
**Version:** 1.0
**Last Updated:** February 2026
**Status:** Draft — pending review and deployment

---

## Table of Contents
1. [Purpose & Philosophy](#1-purpose--philosophy)
2. [Architecture Overview](#2-architecture-overview)
3. [VLAN 60 Infrastructure](#3-vlan-60-infrastructure)
4. [Reverse Proxy Layer — NGINX Proxy Manager](#4-reverse-proxy-layer--nginx-proxy-manager)
5. [Authentication Layer — Authelia](#5-authentication-layer--authelia)
6. [VPN Layer — WireGuard](#6-vpn-layer--wireguard)
7. [Perimeter Defense — Crowdsec & Fail2ban](#7-perimeter-defense--crowdsec--fail2ban)
8. [Outbound Filtering — Squid](#8-outbound-filtering--squid)
9. [External Monitoring — Uptime Kuma](#9-external-monitoring--uptime-kuma)
10. [Firewall Policy](#10-firewall-policy)
11. [Subdomain & Routing Registry](#11-subdomain--routing-registry)
12. [IaC Integration](#12-iac-integration)
13. [Deployment Order](#13-deployment-order)
14. [Portfolio Notes](#14-portfolio-notes)

---

## 1. Purpose & Philosophy

Ariadne is the perimeter layer of the homelab — the thread that determines what crosses between the outside world and the internal network, and where it goes when it does. Named for the Cretan princess who gave Theseus the *clew* (the ball of thread, etymological root of "clue") that made the Minotaur's labyrinth navigable, Ariadne doesn't fight at the gate — she manages the path through the structure.

The DMZ (VLAN 60) is the physical expression of that philosophy. No internal service is exposed directly to the internet. All inbound traffic enters through NGINX Proxy Manager, passes through Authelia's authentication layer where required, and is routed to its destination. Everything that crosses pays a toll. Everything that doesn't belong gets stopped.

**Design principles:**
- No internal service is directly internet-accessible — all external exposure routes through NPM
- Authentication is enforced at the perimeter, not at the service — SSO via Authelia
- Defense is layered — NPM, Authelia, Crowdsec, Fail2ban, and pfSense firewall rules each provide independent protection
- VPN access (WireGuard) provides a trusted path for administrative and family remote access without exposing management interfaces
- Outbound traffic is filtered and logged via Squid — the network knows what it's talking to
- All perimeter activity is visible to Argus — logs flow to Splunk; anomalies surface in Grafana

---

## 2. Architecture Overview

```
INTERNET
    |
    | (WAN — Public IP)
    |
[pfSense CE] — WireGuard VPN termination (pfSense package)
    |           Crowdsec IPS (pfSense package)
    |           Squid forward proxy (pfSense package)
    |           Suricata IDS (pfSense package)
    |
    | (Inbound NAT — port 80/443 → NPM)
    |
[VLAN 60 — DMZ]
    |
    |-- NGINX Proxy Manager (10.0.60.10)
    |       |-- SSL termination (Let's Encrypt)
    |       |-- Subdomain routing → internal services
    |       |-- Authelia forward auth integration
    |       |-- Fail2ban watching NPM logs
    |
    |-- Authelia (10.0.60.11)
            |-- OIDC/OAuth2 SSO
            |-- Sits in front of NPM for protected services
            |-- Session management; MFA enforcement
```

**Traffic flow — inbound request (example: images.sirhexx.com → Immich):**
```
Browser → DNS resolves sirhexx.com → WAN IP
→ pfSense NAT → NPM (10.0.60.10)
→ NPM checks: does this subdomain require Authelia?
    YES → redirect to auth.sirhexx.com → Authelia
        → authenticated → NPM forwards to Immich (10.0.50.30)
    NO  → NPM forwards directly to target service
→ Response returns via same path
```

**Traffic flow — VPN (WireGuard):**
```
Remote device → WireGuard UDP → pfSense WG interface
→ assigned tunnel IP → full internal network access (VLAN 10/50 scope)
→ no NPM involvement; direct service access as if on LAN
```

---

## 3. VLAN 60 Infrastructure

**VLAN:** 60
**Subnet:** 10.0.60.0/24
**Gateway:** 10.0.60.1 (pfSense)
**Purpose:** Publicly facing services; reverse proxy, SSO, perimeter defense

| Service | IP | Type | Status |
|---------|----|------|--------|
| pfSense | 10.0.60.1 | Gateway | Planned |
| NGINX Proxy Manager | 10.0.60.10 | LXC | Planned |
| Authelia | 10.0.60.11 | LXC | Planned |

**pfSense packages (no separate VLAN IP):**

| Package | Function |
|---------|----------|
| WireGuard | VPN termination |
| Crowdsec | Behavioral IPS; community threat intel |
| Squid | Outbound forward proxy + filtering |
| Suricata | Network-layer IDS; alerts → Splunk |

**Firewall policy — VLAN 60:**
- Pass: DMZ → Internet (NPM needs outbound for Let's Encrypt, upstream proxying)
- Block: DMZ → All internal VLANs (DMZ services cannot initiate connections inward)
- Pass: pfSense NAT → NPM on 80/443 (inbound from WAN)
- Pass: WireGuard tunnel → VLAN 10/50 (VPN clients get trusted internal access)
- Block: WireGuard tunnel → VLAN 30 (Work VLAN remains isolated even for VPN clients)

> **Key principle:** The DMZ can receive from the internet and forward to internal services, but it cannot initiate connections into the internal network. NPM proxies requests on behalf of external clients — the internal services see traffic from NPM, never directly from the internet.

---

## 4. Reverse Proxy Layer — NGINX Proxy Manager

**Service:** NGINX Proxy Manager
**IP:** 10.0.60.10
**Port exposure:** 80, 443 (inbound NAT from pfSense WAN)
**Purpose:** SSL termination, subdomain routing, forward auth integration with Authelia

NPM is the single point of ingress for all external web traffic. It handles Let's Encrypt certificate provisioning and renewal automatically, routes subdomains to internal service IPs, and enforces Authelia authentication on protected routes via the forward auth pattern.

**SSL approach:** Let's Encrypt wildcard certificate for *.sirhexx.com via DNS challenge. Single cert covers all subdomains without per-service certificate management.

**Authelia integration pattern:**
NPM uses the `proxy_set_header` forward auth configuration to check every protected request against Authelia before passing it upstream. If Authelia returns 401, NPM redirects to the Authelia login page. If authenticated, the request proceeds with user identity headers injected.

**Services that get NPM exposure:**

| Subdomain | Target | Auth Required |
|-----------|--------|---------------|
| watch.sirhexx.com | Jellyfin (10.0.80.X) | No — Jellyfin handles its own auth |
| images.sirhexx.com | Immich (10.0.50.30) | No — Immich handles its own auth |
| audible.sirhexx.com | Audiobookshelf (10.0.80.X) | No — ABS handles its own auth |
| auth.sirhexx.com | Authelia (10.0.60.11) | — (this IS the auth service) |
| request.sirhexx.com | Jellyseerr (10.0.80.X) | Yes — Authelia SSO |
| books.sirhexx.com | CalibreWeb (10.0.80.X) | Yes — Authelia SSO |
| music.sirhexx.com | Navidrome (10.0.80.X) | Yes — Authelia SSO |
| photos.hexxusweb.com | — | Reserved — portfolio/professional use TBD |

> **Auth rationale:** Jellyfin, Immich, and Audiobookshelf ship with robust built-in authentication and are designed to be self-hosted publicly. Jellyseerr, CalibreWeb, and Navidrome have weaker native auth — Authelia adds the SSO layer in front of them.

---

## 5. Authentication Layer — Authelia

**Service:** Authelia
**IP:** 10.0.60.11
**Purpose:** SSO layer; OIDC/OAuth2 provider; MFA enforcement; session management

Authelia sits between NPM and any service marked as requiring authentication. It provides a single login experience across all protected services, enforces MFA (TOTP), and issues session cookies scoped to the sirhexx.com domain.

**Configuration approach:**
- User database: file-based initially (small household, no AD yet)
- MFA: TOTP (Google Authenticator / Aegis compatible)
- Session domain: sirhexx.com
- Post-June migration path: replace file-based users with Active Directory as identity source; Authentik replaces Authelia as the OIDC provider

**Access policy design:**

| Rule | Target | Policy |
|------|--------|--------|
| Default | All protected subdomains | Two-factor (user + TOTP) |
| Bypass | auth.sirhexx.com | None (it's the login page) |
| Bypass | watch.sirhexx.com | None (Jellyfin self-authenticates) |
| Bypass | images.sirhexx.com | None (Immich self-authenticates) |
| Bypass | audible.sirhexx.com | None (ABS self-authenticates) |

---

## 6. VPN Layer — WireGuard

**Service:** WireGuard
**Deployment:** pfSense package (no separate IP)
**Purpose:** Secure remote access to internal network for trusted users

WireGuard provides the trusted remote path for James and family to access internal services without exposing them publicly. VPN clients get full access to VLAN 10 (Management) and VLAN 50 (Lab Services) — equivalent to being physically on the LAN.

**Peer configuration:**

| Peer | Device | Access Scope |
|------|--------|-------------|
| James | ThinkPad T590 (remote) | VLAN 10, 50, 80 |
| James | Samsung Galaxy S24 FE | VLAN 10, 50, 80 |
| Wife | HP Pavilion x360 | VLAN 50, 80 |
| Wife | Samsung Galaxy S23 FE | VLAN 50, 80 |

> **Access scope rationale:** James gets VLAN 10 (Management) access remotely for admin tasks. Wife's devices get VLAN 50/80 (services and media) but not VLAN 10 — no reason for her devices to touch the management plane.

**Port:** UDP — TBD at deployment (non-default port recommended; avoid 51820 as it's widely scanned)

---

## 7. Perimeter Defense — Crowdsec & Fail2ban

### 7.1 Crowdsec

**Deployment:** pfSense package
**Purpose:** Behavioral IPS; community threat intelligence; automated banning

Crowdsec watches traffic patterns at the pfSense level and cross-references against its community threat intelligence feed. Known-bad IPs get blocked at the firewall before they ever reach NPM. Behavioral detections (port scans, credential stuffing, etc.) trigger automatic bans.

**Integration points:**
- pfSense: firewall-level blocking via bouncer
- NPM: HTTP-level bouncer watches access logs
- Splunk: Crowdsec events forwarded for Argus visibility

### 7.2 Fail2ban

**Deployment:** Per-host (Ansible role)
**Purpose:** Log-based brute force protection on SSH-accessible hosts and NPM

Fail2ban runs on every host with SSH exposure and on NPM. It watches auth logs and NPM access logs for repeated failure patterns and issues temporary IP bans. Complements Crowdsec — Crowdsec works at the network/behavioral layer, Fail2ban works at the log/application layer.

**Monitored jails:**
- sshd (all LXC/VM hosts)
- nginx (NPM access log)
- authelia (failed auth attempts)

---

## 8. Outbound Filtering — Squid

**Deployment:** pfSense package
**Purpose:** Outbound forward proxy; traffic visibility; filtering

Squid intercepts outbound HTTP/HTTPS traffic from internal VLANs, providing a log of what the network is talking to. This serves two purposes: security visibility (Argus can see outbound connections) and the ability to block specific destinations if needed.

Initial deployment is transparent/logging-only — no active filtering until there's a reason to block something specific. Logs forwarded to Splunk.

> **Scope note:** Squid is a pfSense package and applies to traffic routed through pfSense. It does not inspect encrypted traffic without SSL bump configured — SSL bump is deferred as it introduces complexity and certificate trust issues on family devices.

---

## 9. External Monitoring — Uptime Kuma

**Deployment:** External VPS (provider TBD)
**Purpose:** Outside-in availability monitoring of all DMZ-exposed endpoints

Uptime Kuma runs outside the homelab entirely, pinging each public subdomain from the internet's perspective. If NPM goes down, WAN goes down, or a Let's Encrypt cert expires, Uptime Kuma catches it from outside where internal monitoring can't see.

**Monitored endpoints:**

| Endpoint | Check Type | Alert Target |
|----------|------------|-------------|
| watch.sirhexx.com | HTTPS | TBD (Telegram bot preferred) |
| images.sirhexx.com | HTTPS | TBD |
| audible.sirhexx.com | HTTPS | TBD |
| request.sirhexx.com | HTTPS | TBD |
| books.sirhexx.com | HTTPS | TBD |
| music.sirhexx.com | HTTPS | TBD |

> **Alert delivery:** Telegram bot integration is the natural fit given Second Brain infrastructure already uses Telegram. Confirm at deployment.

---

## 10. Firewall Policy

Full pfSense rule set for VLAN 60 and WAN inbound NAT.

### WAN Inbound NAT

| Port | Protocol | Destination | Notes |
|------|----------|-------------|-------|
| 80 | TCP | 10.0.60.10 (NPM) | HTTP — NPM redirects to HTTPS |
| 443 | TCP | 10.0.60.10 (NPM) | HTTPS — primary inbound |
| TBD | UDP | pfSense WG interface | WireGuard VPN |

### VLAN 60 Outbound Rules

| Rule | Source | Destination | Action |
|------|--------|-------------|--------|
| 1 | 10.0.60.0/24 | Internet | Pass — NPM needs outbound |
| 2 | 10.0.60.0/24 | 10.0.0.0/8 | Block — DMZ cannot initiate inbound connections |

### WireGuard Tunnel Rules

| Rule | Source | Destination | Action |
|------|--------|-------------|--------|
| 1 | WG tunnel | 10.0.10.0/24 | Pass (James peers only) |
| 2 | WG tunnel | 10.0.50.0/24 | Pass (all peers) |
| 3 | WG tunnel | 10.0.80.0/24 | Pass (all peers) |
| 4 | WG tunnel | 10.0.30.0/24 | Block (Work VLAN always isolated) |
| 5 | WG tunnel | Internet | Pass (split tunnel optional — TBD) |

---

## 11. Subdomain & Routing Registry

Canonical subdomain list. Cross-reference with Media Stack Design Doc v1.1 §8 for full domain registry.

| Subdomain | Domain | Target Service | Target IP | Auth | Status |
|-----------|--------|---------------|-----------|------|--------|
| watch | sirhexx.com | Jellyfin | 10.0.80.X | None | Planned |
| images | sirhexx.com | Immich | 10.0.50.30 | None | Planned |
| audible | sirhexx.com | Audiobookshelf | 10.0.80.X | None | Planned |
| auth | sirhexx.com | Authelia | 10.0.60.11 | — | Planned |
| request | sirhexx.com | Jellyseerr | 10.0.80.X | Authelia | Planned |
| books | sirhexx.com | CalibreWeb | 10.0.80.X | Authelia | Planned |
| music | sirhexx.com | Navidrome | 10.0.80.X | Authelia | Planned |

> **TBD subdomains:** hexxusweb.com professional services TBD post-June. Additional sirhexx.com subdomains assigned at deployment time for any newly exposed services.

---

## 12. IaC Integration

Ariadne follows the same IaC conventions as all Homelab Command projects. See IaC Runbook v1.1 for tooling, secrets management, and workflow standards.

**Project path:** `~/projects/IaC-Projects/ariadne/`

```
ariadne/
├── terraform/
│   ├── main.tf              # NPM LXC + Authelia LXC provisioning
│   ├── variables.tf
│   ├── terraform.tfvars     # gitignored
│   └── terraform.tfvars.example
└── ansible/
    ├── inventory/
    │   └── ariadne.ini      # NPM + Authelia hosts
    ├── group_vars/
    │   └── ariadne.yml      # Vault-encrypted secrets
    ├── provision.yml        # Full stack deploy
    ├── roles/
    │   ├── npm/             # NPM install + proxy host configs
    │   ├── authelia/        # Authelia install + config templating
    │   └── fail2ban/        # Fail2ban jails for NPM + Authelia
    └── vault/
        └── secrets.yml      # gitignored; Authelia JWT secret, session secret, SMTP creds
```

**Not IaC-managed (pfSense UI configuration):**
- WireGuard peers and tunnel configuration
- Crowdsec pfSense package install and bouncer config
- Squid pfSense package install and ACLs
- Suricata pfSense package install and rule sets
- Inbound NAT rules (80/443 → NPM, WireGuard UDP)

> These are documented here for reference but configured manually in the pfSense UI. pfSense does not have a mature Terraform provider suitable for production use; manual config with this doc as the source of truth is the correct approach.

---

## 13. Deployment Order

Prerequisites: VLAN 60 created in pfSense and switch. VLAN 50 stable (NPM needs to route to Lab Services). TrueNAS reconnected and VLAN 80 services deployed (so NPM has targets to route to).

1. Create VLAN 60 in pfSense (interface, firewall rules, DHCP if needed)
2. Configure VLAN 60 on TP-Link switch (trunk port already carries all VLANs)
3. Provision NPM LXC via Terraform (10.0.60.10)
4. Run Ansible `provision.yml` → NPM role (install, basic config)
5. Configure pfSense inbound NAT (80/443 → NPM)
6. Obtain Let's Encrypt wildcard cert for *.sirhexx.com via DNS challenge
7. Provision Authelia LXC via Terraform (10.0.60.11)
8. Run Ansible `provision.yml` → Authelia role (install, config, user DB)
9. Configure NPM forward auth integration with Authelia
10. Add proxy hosts in NPM (one per subdomain in §11 registry)
11. Configure WireGuard in pfSense (tunnel, peers, firewall rules)
12. Install and configure Crowdsec pfSense package + NPM bouncer
13. Install Squid pfSense package (transparent/logging mode)
14. Install Suricata pfSense package (alert mode initially; block mode after tuning)
15. Run Ansible `provision.yml` → Fail2ban role (NPM + Authelia jails)
16. Deploy Uptime Kuma on external VPS; configure endpoint monitors
17. Forward NPM + Authelia + Crowdsec + Fail2ban logs to Splunk (Argus integration)
18. Test full flow: external request → NPM → Authelia → target service → response
19. Test VPN: WireGuard client → tunnel → internal service access
20. Test blocking: verify DMZ cannot initiate connections to internal VLANs

---

## 14. Portfolio Notes

The Ariadne project demonstrates a cluster of competencies directly relevant to the CRDC SOC Analyst role:

**Network segmentation:** VLAN 60 as a true DMZ — not just a label, but a segment with enforced firewall policy that prevents DMZ services from initiating internal connections. This mirrors enterprise DMZ architecture used to protect internal resources from internet-facing systems.

**Defense in depth:** Five independent defensive layers (pfSense firewall rules, Crowdsec IPS, Suricata IDS, NPM access control, Authelia authentication, Fail2ban) each catching what the others miss. No single point of failure in the defensive stack.

**Zero Trust principles:** No service is trusted by default. External requests authenticate at the perimeter before reaching internal services. VPN access is peer-specific with scoped permissions. Internal services never see raw internet traffic.

**Identity and access management:** Authelia implements SSO with MFA across all protected services — centralized identity, consistent enforcement, auditable access. Maps directly to enterprise IAM architecture.

**Security visibility:** All perimeter events (NPM access logs, Authelia auth events, Crowdsec bans, Fail2ban bans, Suricata alerts) forward to Splunk for Argus correlation. The perimeter is not just defended — it's watched.

**Incident response readiness:** Crowdsec + Fail2ban provide automated response to detected threats. Suricata alerts feed the SIEM. WireGuard access is peer-specific and revocable. The architecture supports rapid containment.

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.1 · Network & Services Architecture v1.4 · Project Roadmap v1.2 · Second Brain Design Doc v1.1 · IaC Runbook v1.1 · Argus Design Doc v1.1 · Media Stack Design Doc v1.1*
