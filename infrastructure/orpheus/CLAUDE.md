# Orpheus

Self-hosted family media platform — video (Jellyfin), photos (Immich), audiobooks + podcasts
(Audiobookshelf), ebooks (CalibreWeb), music (Navidrome), download automation (*Arr stack +
qBittorrent). All services run as TrueNAS Scale apps on the R710, co-located with ZFS storage.

## Components

All services are TrueNAS Scale apps on the R710. The host has two NICs:
- `eno1` → 10.0.10.30 (VLAN 10, management + PBS)
- `eno4` → 10.0.80.5 (VLAN 80, media serving)

### Media Delivery (VLAN 80 — family-accessible)

| Name | Type | IP | Port | Status |
|------|------|----|------|--------|
| Jellyfin | TrueNAS Scale app | 10.0.80.5 | 8096 | Running — needs reconfiguration |
| Immich | TrueNAS Scale app | 10.0.80.5 | 2283 | Running — needs reconfiguration |
| Audiobookshelf | TrueNAS Scale app | 10.0.80.5 | 13378 | Running — needs reconfiguration |
| CalibreWeb | TrueNAS Scale app | 10.0.80.5 | 8083 | Running — needs reconfiguration |
| Navidrome | TrueNAS Scale app | 10.0.80.5 | 4533 | Running — needs reconfiguration |
| Jellyseerr | TrueNAS Scale app | 10.0.80.5 | 5055 | Deploying |
| Komga | TrueNAS Scale app | 10.0.80.5 | 25600 | Deferred — post-June |
| RomM | TrueNAS Scale app | 10.0.80.5 | 8998 | Deferred — post-June |

### Download & Automation (internal-only)

| Name | Type | IP | Port | Status |
|------|------|----|------|--------|
| Prowlarr | TrueNAS Scale app | 10.0.80.5 | 9696 | Needs fresh deployment |
| Radarr | TrueNAS Scale app | 10.0.80.5 | 7878 | Needs fresh deployment |
| Sonarr | TrueNAS Scale app | 10.0.80.5 | 8989 | Needs fresh deployment |
| Lidarr | TrueNAS Scale app | 10.0.80.5 | 8686 | Needs fresh deployment |
| Readarr | TrueNAS Scale app | 10.0.80.5 | 8787 | Needs fresh deployment |
| Bazarr | TrueNAS Scale app | 10.0.80.5 | 6767 | Needs fresh deployment |
| qBittorrent | TrueNAS Scale app | 10.0.80.5 | 8080 | Needs fresh deployment |
| Libation | TrueNAS Scale app | 10.0.80.5 | — | Audible audiobook CLI |

## Role in Stack

**Depends on:**
- `network/pfsense` — VLAN 80 firewall rules, NAT
- `network/switch` — VLAN 80 port assignment (switch port 4 → VLAN 80 untagged)
- `ariadne` — reverse proxy for all public subdomains (watch, images, audible, etc.)

**Depended on by:**
- Family devices — only consumer of VLAN 80 media services

## IaC Layout

```
infrastructure/orpheus/
  ansible/     ← placeholder (.gitkeep)
  terraform/   ← placeholder (.gitkeep)
```

**Orpheus has no LXC/VM IaC.** All services are TrueNAS Scale apps — configured through
the TrueNAS UI, not Terraform or Ansible. The IaC that touches Orpheus is:
- pfSense Terraform: `infrastructure/network/pfsense/` (VLAN 80 rules)
- Switch Ansible: `infrastructure/network/switch/` (VLAN 80 port)
- Ariadne Ansible: `infrastructure/ariadne/ansible/roles/media_proxy/` (proxy configs)

## External Subdomains (sirhexx.com)

| Subdomain | Service |
|-----------|---------|
| watch.sirhexx.com | Jellyfin |
| images.sirhexx.com | Immich |
| audible.sirhexx.com | Audiobookshelf |
| TBD | Jellyseerr, CalibreWeb, Navidrome |

## Notes

- *Arr stack on TrueNAS is poorly configured — full fresh deployment planned; see §12 of design doc
- TrueNAS has static routes configured (UI only) for return traffic to VLAN 20/50/60 via eno4
- Never directly access/write/delete `general_pool/archive` without explicit direction
- `test-share` on TrueNAS (97.99 GiB) is likely the Immich library — do NOT delete until
  Immich storage path confirmed and data migrated to proper dataset
- See root `CLAUDE.md` for VLAN topology
- Design doc: `docs/orpheus-design-doc-v1.1.md`
