# Media Stack Design Doc
**Version:** 1.1
**Last Updated:** February 2026
**Status:** Living Document

---

## 1. Purpose & Philosophy

The Media Stack provides a self-hosted, family-accessible media platform covering video, photos, audiobooks, ebooks, music, podcasts, comics/manga, and ROMs. It replaces cloud services (Google Photos, Audible, streaming) with owned infrastructure wherever practical.

**Design principles:**
- Files live on TrueNAS (ZFS — data integrity, RAID protection). Services live on PVE (resource management, IaC, consistency with the rest of the homelab).
- Every content type has exactly one authoritative service. No duplication of function.
- File organization is standardized and enforced by automation — not manual effort.
- Remote access for family is a first-class requirement, not an afterthought.
- Active content types (video, photos, audiobooks, music, podcasts) are fully built out. Lower-priority types (comics, ROMs) are documented and deployable but not blocking.

**Hosting split — Option A:**
- **PVE LXCs on VLAN 80 (Media)** — content-serving services (Jellyfin, Audiobookshelf, CalibreWeb, Navidrome, Komga, RomM, Jellyseerr)
- **Docker VM on VLAN 50 (Lab Services)** — services requiring Docker Compose (Immich; future Nextcloud and other Docker-native services across the homelab)
- **TrueNAS Scale apps** — download and file management (*Arr stack, qBittorrent, Calibre, Libation)
- **TrueNAS** — all media files, served to PVE via NFS mounts

**Docker VM note:** The shared Docker VM (10.0.50.X) is homelab-wide infrastructure — it hosts any service that requires Docker Compose, regardless of project. Immich is the first tenant. Future tenants may include Nextcloud and Vaultwarden (Productivity Stack) and others. Managed via Ansible + Docker Compose, not nested containerization inside LXCs.

**Portainer:** Docker containers on the Docker VM are managed via Portainer. Portainer Server runs as a native Linux binary (systemd service — no Docker required on the host) inside a lightweight LXC on VLAN 10 (Management), consistent with the management plane pattern (pfSense, Proxmox, TrueNAS all managed from VLAN 10). The Portainer Agent runs as a container on the Docker VM (VLAN 50) and registers with the Server. Portainer Server is not exposed externally.

---

## 2. Content Types & Service Map

| Content Type | Serving Service | Host | Management (TrueNAS) | Download | Priority |
|---|---|---|---|---|---|
| Movies | Jellyfin | PVE LXC / VLAN 80 | Radarr | qBittorrent | Active |
| TV Shows | Jellyfin | PVE LXC / VLAN 80 | Sonarr | qBittorrent | Active |
| Kids Movies/Shows | Jellyfin (separate libraries) | PVE LXC / VLAN 80 | Radarr / Sonarr | qBittorrent | Active |
| Internet Videos | Jellyfin (separate library) | PVE LXC / VLAN 80 | Manual / yt-dlp | yt-dlp | Active |
| Photos | Immich | Docker VM / VLAN 50 | Immich (self-managing) | — | Active |
| Audiobooks | Audiobookshelf | PVE LXC / VLAN 80 | Libation / Readarr | qBittorrent | Active |
| Ebooks (Fiction) | CalibreWeb | PVE LXC / VLAN 80 | Calibre / Readarr | qBittorrent | Active |
| Ebooks (Non-Fiction) | CalibreWeb | PVE LXC / VLAN 80 | Calibre / Readarr | qBittorrent | Active |
| Ebooks (Reference) | CalibreWeb | PVE LXC / VLAN 80 | Calibre / Readarr | qBittorrent | Active |
| Music | Navidrome | PVE LXC / VLAN 80 | Lidarr | qBittorrent | Active |
| Podcasts | Audiobookshelf | PVE LXC / VLAN 80 | ABS (native) | ABS (native) | Active |
| Comics/Manga | Komga | PVE LXC / VLAN 80 | Manual import | Manual | Deferred |
| ROMs | RomM + EmulatorJS | PVE LXC / VLAN 80 | Manual import | Manual | Deferred |
| Internet Radio | Azuracast | TBD | — | — | Post-June |

---

## 3. Infrastructure

### 3.1 VLAN 80 — Media (New)

VLAN 80 is created specifically for media-serving services. It has its own firewall policy distinct from Lab Services (VLAN 50) and DMZ (VLAN 60), allowing family device access without routing through infrastructure VLANs.

**Firewall policy (VLAN 80):**
- Allow: access from trusted family devices (personal device VLAN)
- Allow: outbound internet (metadata fetching, subtitle downloads)
- Allow: NFS to TrueNAS (media file access)
- Block: access to VLAN 10 (Management), VLAN 50 (Lab), VLAN 60 (DMZ) except via defined rules
- Remote access via NGINX Proxy Manager (DMZ) only — not direct external access

**Note:** VLAN 80 is documented in Network & Services Architecture v1.4.

### 3.2 PVE Services — VLAN 80 (Media)

| Service | IP | Port | Notes |
|---------|-----|------|-------|
| Jellyfin | TBD (10.0.80.X) | 8096 | Movies, TV, Kids, Internet video |
| Audiobookshelf | TBD (10.0.80.X) | 13378 | Audiobooks + podcasts |
| CalibreWeb | TBD (10.0.80.X) | 8083 | Ebook serving; fiction, non-fiction, reference |
| Navidrome | TBD (10.0.80.X) | 4533 | Music streaming |
| Jellyseerr | TBD (10.0.80.X) | 5055 | Family media requests → Radarr/Sonarr |
| Komga | TBD (10.0.80.X) | 25600 | Comics/Manga (deferred) |
| RomM | TBD (10.0.80.X) | 8998 | ROM library + EmulatorJS (deferred) |

IPs assigned at deployment time from the 10.0.80.0/24 range.

### 3.3 Docker VM — VLAN 50 (Lab Services)

A single VM on VLAN 50 hosts all Docker Compose-based services across the homelab. Managed via Ansible; each service is a Docker Compose stack deployed and maintained by its Ansible role.

| Resource | IP | Port | Project |
|----------|----|------|---------|
| Docker VM (host) | TBD (10.0.50.X) | — | Shared infrastructure |
| Portainer Agent | Docker VM IP | 9001 | Management (Server on VLAN 10) |
| Immich | Docker VM IP | 2283 | Media Stack |
| *(future)* Nextcloud | Docker VM IP | 80/443 | Productivity Stack |
| *(future)* Vaultwarden | Docker VM IP | 80/443 | Productivity Stack |

**Docker VM specs:** 4 vCPU, 8GB RAM, 50GB OS disk. All data (photos, uploads) stored on TrueNAS via NFS — not on the VM disk.

**Immich Postgres:** Immich uses its own bundled Postgres instance inside the Docker Compose stack — isolated from the homelab shared Postgres at 10.0.50.14. This is intentional: Immich is opinionated about its Postgres version and schema migrations. Back up the Immich Postgres container data separately.

**Port note (Nextcloud, Vaultwarden):** Multiple Docker services cannot bind to the same host port. Each service exposes on a distinct internal port; NGINX Proxy Manager (DMZ) handles external routing by subdomain. No port conflicts on the Docker VM itself.

### 3.4 TrueNAS Services (Download & File Management)

| Service | Port | Notes |
|---------|------|-------|
| Prowlarr | 9696 | Indexer manager; syncs to all *Arr apps |
| Radarr | 7878 | Movie automation |
| Sonarr | 8989 | TV show automation |
| Lidarr | 8686 | Music automation |
| Readarr | 8787 | Ebook/audiobook automation |
| Bazarr | 6767 | Subtitle automation for Jellyfin |
| qBittorrent | 8080 | Torrent download client |
| Libation | — | Audible audiobook download (desktop app) |
| Calibre | — | Ebook management (headless or desktop) |
| yt-dlp | — | CLI; scripted via n8n or cron for internet video |

### 3.5 Hardware

| Hardware | Role |
|----------|------|
| Xeon E-2378 (main PVE node) | Runs all VLAN 80 LXCs and Docker VM (VLAN 50) |
| R710 TrueNAS (reconnect Phase 1) | All media file storage; TrueNAS Scale apps |
| GPU (future) | Jellyfin hardware transcoding |

---

## 4. File Organization

### 4.1 Philosophy

The *Arr stack enforces naming conventions for everything it manages. Manual imports follow the same conventions. One root media folder per content type on TrueNAS, mounted into every service that needs it. No service maintains a private copy of files.

### 4.2 TrueNAS Directory Structure

```
/mnt/{pool}/media/
├── movies/                        # Radarr-managed
│   └── Movie Name (2024)/
│       └── Movie Name (2024).mkv
├── tv/                            # Sonarr-managed
│   └── Show Name/
│       └── Season 01/
│           └── Show Name - S01E01 - Episode Title.mkv
├── kids-movies/                   # Radarr (separate root folder)
├── kids-tv/                       # Sonarr (separate root folder)
├── internet-video/                # Manual / yt-dlp
│   └── {Channel Name}/
│       └── {Video Title}.mp4
├── audiobooks/                    # ABS + Readarr + Libation
│   └── {Author}/
│       └── {Title}/
│           └── {Title}.m4b
├── music/                         # Lidarr-managed
│   └── {Artist}/
│       └── {Album}/
│           └── {Track} - {Title}.flac
├── ebooks/
│   ├── fiction/                   # Calibre library
│   ├── non-fiction/               # Calibre library
│   └── reference/                 # Calibre library
├── photos/                        # Immich-managed
├── comics/                        # Komga-managed (deferred)
│   └── {Series}/
│       └── {Series} #{Issue}.cbz
├── roms/                          # RomM-managed (deferred)
│   └── {System}/
│       └── {Game}.{ext}
└── downloads/                     # qBittorrent working directory
    ├── complete/
    └── incomplete/
```

### 4.3 NFS Mounts

**TrueNAS → PVE LXCs (VLAN 80):**

| Service | NFS Mount | Access |
|---------|-----------|--------|
| Jellyfin | /media/movies, /media/tv, /media/kids-movies, /media/kids-tv, /media/internet-video | Read-only |
| Audiobookshelf | /media/audiobooks | Read-write (podcast downloads) |
| CalibreWeb | /media/ebooks/fiction, /media/ebooks/non-fiction, /media/ebooks/reference | Read-only |
| Navidrome | /media/music | Read-only |
| Komga | /media/comics | Read-only |
| RomM | /media/roms | Read-only |

**TrueNAS → Docker VM (VLAN 50):**

| Service | NFS Mount | Access |
|---------|-----------|--------|
| Immich | /media/photos | Read-write |

**Read-only principle:** Serving services never write to media directories except where they own the content. Only *Arr apps and download clients write to Arr-managed directories.

---

## 5. The *Arr Stack

### 5.1 Data Flow

```
Family Request
    |
    v
Jellyseerr (request UI)
    |
    v
Radarr / Sonarr
    |
    v
Prowlarr (searches all configured indexers)
    |
    v
qBittorrent (downloads)
    |
    v
Radarr / Sonarr (monitors completion)
    → Renames to standard format
    → Moves to correct media directory on TrueNAS
    → Triggers Jellyfin library scan
    |
    v
Jellyfin (serves to family)
    |
    v
Bazarr (fetches subtitles for new content)
```

### 5.2 Quality Profiles

| Content | Target | Fallback |
|---------|--------|---------|
| Movies | 1080p BluRay (x264/x265) | 1080p WEB-DL |
| TV Shows | 1080p WEB-DL | 720p WEB-DL |
| Kids content | 1080p WEB-DL | 720p |
| Music | FLAC (lossless) | MP3 320kbps |
| Audiobooks | M4B (single file) | MP3 chapters |
| Ebooks | EPUB | MOBI |

**Recyclarr** (deferred): syncs community quality profiles and custom formats into Radarr/Sonarr. Add once the stack is stable.

### 5.3 Lidarr & Music — Special Considerations

Lidarr is album-centric by design, which creates friction with a singles/playlists-heavy library. Mitigation:
- Configure Lidarr to monitor the "singles" album type — creates a virtual `{Artist} - Singles` folder per artist
- For existing disorganized music: import into Navidrome directly; use Lidarr for new acquisitions only
- Playlists are managed in Navidrome — Lidarr does not touch them

### 5.4 Readarr & Books — Special Considerations

Readarr handles acquisition; Calibre manages the library; CalibreWeb serves it. Libation remains preferred for Audible content. Readarr supports all three ebook categories via separate root folder configuration — one root folder per category pointing to the matching Calibre library directory.

---

## 6. Photos — Immich

### 6.1 Role

Immich is the long-term replacement for Google Photos — automatic mobile backup, facial recognition, shared libraries, familiar timeline UI. Runs on the shared Docker VM (VLAN 50) via Docker Compose because its ML container (face recognition, CLIP embeddings) requires Docker and is not practical inside a standard LXC.

### 6.2 Migration Path

```
1. Deploy Immich on Docker VM
2. Configure mobile backup on all family devices
3. Export Google Photos via Google Takeout
4. Bulk import Takeout archive into Immich
5. Verify completeness; confirm family comfortable with Immich UI
6. Disable Google Photos backup on all family devices
7. 90-day hold on Google Photos (read-only safety net)
8. Delete Google Photos library
```

### 6.3 Family Access

Each family member gets their own Immich account. Shared libraries and albums for family photos. Mobile apps (iOS + Android) handle automatic backup.

---

## 7. Podcasts — ABS + Antennapod

Podcasts remain in Audiobookshelf. ABS handles RSS subscriptions, episode downloading, library organization, and progress sync via the gpodder protocol. Antennapod (Android) handles the listening experience — queue management, speed control, skip silence, chapter support — and syncs progress back to ABS.

**Fallback:** If ABS + Antennapod proves insufficient after real-world use, **Pinepods** is the documented next step.

---

## 8. Domain Registry

Three domains are owned and assigned by purpose. All external services are subdomains of the appropriate domain.

| Domain | Purpose | Notes |
|--------|---------|-------|
| sirhexx.com | Personal services — family-facing and homelab external access | Primary domain for all self-hosted service subdomains |
| hexxusweb.com | Professional services — work and portfolio-facing | Reserved for professional/career use |
| bravelittlesalamander.com | Wife's domain | Held for future use |

**Known sirhexx.com subdomains:**

| Subdomain | Service | Status |
|-----------|---------|--------|
| watch.sirhexx.com | Jellyfin | Configured |
| images.sirhexx.com | Immich | Configured |
| audible.sirhexx.com | Audiobookshelf | Configured |
| *(others TBD)* | Jellyseerr, CalibreWeb, Navidrome, Komga, RomM | Assign at deployment |

**Note:** Additional configured subdomains not listed here — inventory at deployment time and update this registry.

---

## 9. Remote Access

All remote-accessible services are exposed via NGINX Proxy Manager (DMZ, VLAN 60). See DMZ Design Doc for full reverse proxy and auth configuration.

| Service | Domain | Auth | Family Access |
|---------|--------|------|---------------|
| Jellyfin | watch.sirhexx.com | Jellyfin native | Yes |
| Immich | images.sirhexx.com | Immich native | Yes |
| Audiobookshelf | audible.sirhexx.com | ABS native | Yes |
| Jellyseerr | TBD.sirhexx.com | Jellyseerr native | Yes |
| CalibreWeb | TBD.sirhexx.com | CalibreWeb native | Optional |
| Navidrome | TBD.sirhexx.com | Navidrome native | Optional |
| Komga | TBD.sirhexx.com | Komga native | Deferred |
| RomM | TBD.sirhexx.com | RomM native | Deferred |

**Never exposed externally:** *Arr apps, qBittorrent, Prowlarr, Bazarr, Calibre, Libation. Internal access only.

**Remaining subdomains to assign** (at deployment time): Jellyseerr, CalibreWeb, Navidrome, Komga, RomM on sirhexx.com.

---

## 10. Existing Library Cleanup

Pre-deployment task — serving services will not scan correctly against unstructured directories.

### 9.1 Priority Order

1. **Movies & TV** — must be clean before Jellyfin + Radarr/Sonarr deployment
2. **Music** — must be organized before Navidrome migration and Lidarr setup
3. **Audiobooks** — Libation re-downloads come pre-organized; non-Audible files need `{Author}/{Title}/{Title}.m4b` structure
4. **Ebooks** — import into Calibre once; Calibre manages structure thereafter
5. **Comics/Manga** — rename to `{Series}/{Series} #{Issue}.cbz` before Komga import (deferred)
6. **ROMs** — organize into `{System}/{Game}.{ext}` folders before RomM import (deferred)

### 9.2 Cleanup Tools

| Content | Tool | Notes |
|---------|------|-------|
| Movies/TV | FileBot | Batch rename against TheMovieDB/TheTVDB; free for CLI use |
| Music | MusicBrainz Picard | Auto-tags and renames against MusicBrainz; free |
| Comics | ComicTagger | Tags CBZ/CBR against ComicVine metadata |
| Ebooks | Calibre (built-in) | Import once; Calibre manages structure thereafter |
| ROMs | Manual | Simple folder-per-system organization |

---

## 11. Deferred & Future Services

| Service | Status | Notes |
|---------|--------|-------|
| Komga | Deferred — post-June | Comics library cleanup required first |
| RomM + EmulatorJS | Deferred — post-June | ROM library organization required first |
| Recyclarr | Deferred | Add after *Arr stack is stable |
| Azuracast | Post-June | Internet radio; pairs with Navidrome music library |
| Pinepods | Contingency | Only if ABS + Antennapod proves insufficient |
| Nextcloud | Post-June (Productivity Stack) | Separate project; may integrate with media directories via WebDAV |

---

## 12. Workflow Status

| Service / Workflow | Status | Notes |
|-------------------|--------|-------|
| VLAN 80 (Media) | Build fresh | pfSense + switch config required |
| Docker VM (VLAN 50) | Build fresh | Shared homelab infrastructure |
| Portainer Server LXC (VLAN 10) | Build fresh | Management plane; connects to Docker VM agent |
| Jellyfin | Migrate → PVE LXC / VLAN 80 | Currently on TrueNAS |
| Immich | Migrate → Docker VM / VLAN 50 | Currently on TrueNAS |
| Audiobookshelf | Migrate → PVE LXC / VLAN 80 | Currently on TrueNAS |
| CalibreWeb | Migrate → PVE LXC / VLAN 80 | Currently on TrueNAS |
| Navidrome | Migrate → PVE LXC / VLAN 80 | Currently on TrueNAS |
| Prowlarr | Build fresh — TrueNAS Scale | New |
| Radarr | Build fresh — TrueNAS Scale | New |
| Sonarr | Build fresh — TrueNAS Scale | New |
| Lidarr | Build fresh — TrueNAS Scale | New |
| Readarr | Build fresh — TrueNAS Scale | New |
| Bazarr | Build fresh — TrueNAS Scale | New |
| qBittorrent | Build fresh — TrueNAS Scale | New |
| Jellyseerr | Build fresh — PVE LXC / VLAN 80 | New |
| Google Photos → Immich migration | Planned | After Immich stable on Docker VM |
| Komga | Deferred | Post-June |
| RomM | Deferred | Post-June |

---

## 13. Deployment Order

Requires R710 TrueNAS reconnected (Phase 1 prerequisite).

**Pre-deployment:**
1. Reconnect R710 TrueNAS; establish NFS exports for all media directories
2. Create VLAN 80 in pfSense + managed switch; set firewall policy
3. Update Network & Services Architecture to v1.4 (add VLAN 80, Docker VM)
4. Clean up Movies + TV library (FileBot) before Jellyfin migration
5. Clean up Music library (MusicBrainz Picard) before Navidrome migration

**Infrastructure:**
6. Provision Docker VM (VLAN 50, 10.0.50.X) via Terraform + Ansible
7. Deploy Immich on Docker VM via Ansible (Docker Compose role)
8. Configure Immich family accounts + mobile backup on all devices

**Core media services (migrate existing):**
9. Migrate Jellyfin → PVE LXC / VLAN 80; mount NFS media directories
10. Migrate Audiobookshelf → PVE LXC / VLAN 80; configure Antennapod gpodder sync
11. Migrate CalibreWeb → PVE LXC / VLAN 80; import existing Calibre library
12. Migrate Navidrome → PVE LXC / VLAN 80; mount NFS music directory

**Download + automation stack (new):**
13. Deploy qBittorrent on TrueNAS Scale
14. Deploy Prowlarr; configure indexers
15. Deploy Radarr + Sonarr; connect Prowlarr + qBittorrent
16. Deploy Lidarr; connect Prowlarr + qBittorrent
17. Deploy Readarr; connect Prowlarr + qBittorrent
18. Deploy Bazarr; connect Sonarr + Radarr
19. Deploy Jellyseerr on PVE LXC / VLAN 80; connect Radarr + Sonarr

**Remote access:**
20. Configure NGINX Proxy Manager subdomains (watch, images, audible + TBD)
21. Test remote access for all family members on all services

**Google Photos migration:**
22. Begin Google Takeout export
23. Import into Immich; verify completeness
24. Disable Google Photos backup on all family devices
25. 90-day hold → delete Google Photos library

**Deferred (post-June):**
26. Deploy Komga + organize comics library
27. Deploy RomM + EmulatorJS + organize ROM library
28. Deploy Azuracast; connect to Navidrome music library

---

## 14. Infrastructure as Code

All PVE-hosted services (LXCs and Docker VM) are provisioned and configured via IaC. TrueNAS Scale apps are managed through the TrueNAS UI. For the full IaC workflow, see the **IaC Runbook v1.0**.

### 13.1 Repository Location

```
homelab-command/
└── infrastructure/
    └── media-stack/
        ├── terraform/       # LXC + Docker VM provisioning
        └── ansible/         # Service configuration + Docker Compose deployment
```

### 13.2 Terraform — What Gets Provisioned

| Resource | Module | VLAN | IP | Notes |
|----------|--------|------|----|-------|
| Docker VM | proxmox-vm | 50 | TBD (10.0.50.X) | 4 vCPU, 8GB RAM, 50GB disk; shared infra |
| Jellyfin LXC | lxc-container | 80 | TBD (10.0.80.X) | 4 vCPU, 4GB RAM, 20GB disk |
| Audiobookshelf LXC | lxc-container | 80 | TBD (10.0.80.X) | 2 vCPU, 2GB RAM, 10GB disk |
| CalibreWeb LXC | lxc-container | 80 | TBD (10.0.80.X) | 2 vCPU, 2GB RAM, 10GB disk |
| Navidrome LXC | lxc-container | 80 | TBD (10.0.80.X) | 2 vCPU, 2GB RAM, 10GB disk |
| Jellyseerr LXC | lxc-container | 80 | TBD (10.0.80.X) | 2 vCPU, 2GB RAM, 10GB disk |
| Komga LXC | lxc-container | 80 | TBD (10.0.80.X) | 2 vCPU, 2GB RAM, 10GB disk (deferred) |
| RomM LXC | lxc-container | 80 | TBD (10.0.80.X) | 2 vCPU, 4GB RAM, 10GB disk (deferred) |

### 13.3 Ansible — What Gets Configured

| Role | Target | Configures |
|------|--------|-----------|
| `docker-vm` | Docker VM | Docker Engine, Docker Compose, NFS mounts |
| `immich` | Docker VM | Immich Docker Compose stack (server, ML, Redis, Postgres) |
| `nfs-mounts` | All media LXCs | Shared role; mounts correct TrueNAS NFS shares per host |
| `jellyfin` | Jellyfin LXC | Jellyfin install, NFS mounts, library paths |
| `audiobookshelf` | ABS LXC | ABS install, NFS audiobook mount, gpodder config |
| `calibreweb` | CalibreWeb LXC | CalibreWeb install, NFS ebook mounts, Calibre library path |
| `navidrome` | Navidrome LXC | Navidrome install, NFS music mount |
| `jellyseerr` | Jellyseerr LXC | Jellyseerr install, Radarr/Sonarr API connection |

### 13.4 Secrets (Ansible Vault)

```
vault_immich_db_password
vault_jellyfin_api_key
vault_calibreweb_admin_password
vault_navidrome_admin_password
vault_jellyseerr_api_key
vault_radarr_api_key            # Used by Jellyseerr role
vault_sonarr_api_key            # Used by Jellyseerr role
```

### 13.5 Playbook Invocations

```bash
# Provision all media stack infrastructure
cd infrastructure/media-stack/terraform/
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply

# Configure all services
cd ../ansible/
ansible-playbook provision.yml --ask-vault-pass

# Deploy/update Immich only (Docker VM)
ansible-playbook provision.yml --limit docker-vm --ask-vault-pass

# Update NFS mounts only (e.g. after TrueNAS IP change)
ansible-playbook provision.yml --tags nfs-mounts --ask-vault-pass

# Ongoing maintenance
ansible-playbook update.yml --ask-vault-pass
```

### 13.6 Recovery

Media Stack deploys after core data services (Postgres, Redis, MinIO) in a full rebuild. Media files survive on TrueNAS ZFS — only services need rebuilding, not content.

Post-recovery steps:
1. Re-establish TrueNAS NFS exports before running Ansible
2. Immich's Postgres instance lives inside the Docker VM — restore from backup before reprovisioning Immich
3. *Arr app configurations live on TrueNAS — back up TrueNAS app data separately from media files
4. Jellyfin metadata cache rebuilds automatically on first scan (slow but automatic)
5. Re-verify all sirhexx.com subdomains resolve correctly through NPM after DNS propagation

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.1 · Network & Services Architecture v1.4 · Project Roadmap v1.2 · Second Brain Design Doc v1.1 · IaC Runbook v1.1 · Argus Design Doc v1.1 · Ariadne Design Doc v1.0*
