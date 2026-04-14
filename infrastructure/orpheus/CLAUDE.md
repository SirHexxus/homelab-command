# Orpheus

**Claude's role in this directory: System Administrator — with one active escalation trigger.**
Media delivery services (Jellyfin, Immich, etc.) are in maintenance mode. The *Arr download
automation stack requires a full fresh deployment — when that work begins, treat the session
as PM scope, not maintenance.

## Current State

All services are TrueNAS Scale apps on the R710. Orpheus has no LXC/VM IaC of its own —
see below for where the relevant IaC lives. The host has two NICs:
- `eno1` → 10.0.10.30 (VLAN 10, management + PBS)
- `eno4` → 10.0.80.5 (VLAN 80, media serving)

TrueNAS has static routes for return traffic to VLAN 20/50/60 configured in the TrueNAS UI
— not IaC.

### Media Delivery (VLAN 80 — SysAdmin scope)

| Name | IP | Port | Status |
|------|----|------|--------|
| Jellyfin | 10.0.80.5 | 8096 | Running — needs reconfiguration |
| Immich | 10.0.80.5 | 2283 | Running — needs reconfiguration |
| Audiobookshelf | 10.0.80.5 | 13378 | Running — needs reconfiguration |
| CalibreWeb | 10.0.80.5 | 8083 | Running — needs reconfiguration |
| Navidrome | 10.0.80.5 | 4533 | Running — needs reconfiguration |
| Jellyseerr | 10.0.80.5 | 5055 | Deploying |
| Komga | 10.0.80.5 | 25600 | Deferred — post-June |
| RomM | 10.0.80.5 | 8998 | Deferred — post-June |

### Download & Automation (PM scope when active — see Escalation Criteria)

| Name | IP | Port | Status |
|------|----|------|--------|
| Prowlarr | 10.0.80.5 | 9696 | Needs fresh deployment |
| Radarr | 10.0.80.5 | 7878 | Needs fresh deployment |
| Sonarr | 10.0.80.5 | 8989 | Needs fresh deployment |
| Lidarr | 10.0.80.5 | 8686 | Needs fresh deployment |
| Readarr | 10.0.80.5 | 8787 | Needs fresh deployment |
| Bazarr | 10.0.80.5 | 6767 | Needs fresh deployment |
| qBittorrent | 10.0.80.5 | 8080 | Needs fresh deployment |
| Libation | 10.0.80.5 | — | Audible audiobook CLI |

## Role in Stack

**Depends on:**
- `network/pfsense` — VLAN 80 firewall rules, NAT
- `network/switch` — VLAN 80 port assignment (switch port 4 → VLAN 80 untagged)
- `ariadne` — reverse proxy for all public subdomains

**Depended on by:**
- Family devices — only consumer of VLAN 80 media services

## IaC Layout

```
infrastructure/orpheus/
  ansible/     ← placeholder (.gitkeep)
  terraform/   ← placeholder (.gitkeep)
```

The IaC that touches Orpheus lives in:
- `infrastructure/network/pfsense/` — VLAN 80 firewall rules
- `infrastructure/network/switch/` — VLAN 80 port assignment
- `infrastructure/ariadne/ansible/roles/media_proxy/` — proxy configs

## External Subdomains (sirhexx.com)

| Subdomain | Service |
|-----------|---------|
| watch.sirhexx.com | Jellyfin |
| images.sirhexx.com | Immich |
| audible.sirhexx.com | Audiobookshelf |
| TBD | Jellyseerr, CalibreWeb, Navidrome |

## Hard Constraints

- Do not access, write, or delete `general_pool/archive` without explicit direction
- Do not delete `test-share` (97.99 GiB) — likely the Immich library; confirm storage path
  and complete data migration before any action

## Escalation Criteria

**Automatic PM trigger:** Any work involving the *Arr stack (Prowlarr, Radarr, Sonarr,
Lidarr, Readarr, Bazarr, qBittorrent) is a fresh deployment project — stop and confirm
before proceeding. Read `docs/orpheus-design-doc-v1.1.md` §12 first.

Additional escalation triggers:
- ZFS dataset restructuring or deletion
- TrueNAS app removal or reinstallation
- eno4 or VLAN 80 network configuration changes

## Reference

Design doc: `docs/orpheus-design-doc-v1.1.md`. VLAN topology: see root `CLAUDE.md`.
See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.
