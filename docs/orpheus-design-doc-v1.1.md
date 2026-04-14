# Orpheus Design Doc
**Version:** 1.3
**Last Updated:** 2026-04-03
**Status:** Living Document

---

## 1. Purpose & Philosophy

See `docs/homelab-philosophy-v1.0.md` for the broader goals this service supports. Orpheus is the most direct expression of the family services and cost-saving goals: it gives family members real, accessible alternatives to paid streaming and cloud services, owned and operated locally.

The Orpheus provides a self-hosted, family-accessible media platform covering video, photos, audiobooks, ebooks, music, podcasts, comics/manga, and ROMs. It replaces cloud services (Google Photos, Audible, streaming) with owned infrastructure wherever practical.

**Design principles:**
- Files live on TrueNAS (ZFS - data integrity, RAID protection). Services run as TrueNAS Scale apps, co-located with storage for direct ZFS dataset access.
- Every content type has exactly one authoritative service. No duplication of function.
- File organization is standardized and enforced by automation - not manual effort.
- Remote access for family is a first-class requirement, not an afterthought.
- Active content types (video, photos, audiobooks, music, podcasts) are fully built out. Lower-priority types (comics, ROMs) are documented and deployable but not blocking.

**Hosting split:**
- **TrueNAS Scale apps** - all media delivery and management services: Jellyfin, Audiobookshelf, CalibreWeb, Navidrome, Immich, Jellyseerr, Komga, RomM, Azuracast, *Arr stack, qBittorrent, Calibre, Libation
- **TrueNAS ZFS** - all media files; apps access datasets directly via bind mounts (no NFS hop)

**Note:** Docker-native homelab services (wger, future Nextcloud, Vaultwarden) run on **Hephaestus** (shared Docker VM, 10.0.50.30, VLAN 50) - a separate homelab project with its own IaC. Orpheus has no services running on Hephaestus.

---

## 2. Content Types & Service Map

| Content Type | Serving Service | Host | Management (TrueNAS) | Download | Priority |
|---|---|---|---|---|---|
| Movies (incl. anime) | Jellyfin | TrueNAS Scale app | Radarr | qBittorrent | Active |
| TV Shows | Jellyfin | TrueNAS Scale app | Sonarr | qBittorrent | Active |
| Kids Movies/Shows | Jellyfin (separate libraries) | TrueNAS Scale app | Radarr / Sonarr | qBittorrent | Active |
| Anime Shows | Jellyfin (separate library) | TrueNAS Scale app | Sonarr | qBittorrent | Active |
| Internet Videos | Jellyfin (separate library) | TrueNAS Scale app | Manual / yt-dlp | yt-dlp | Active |
| Photos | Immich | TrueNAS Scale app | Immich (self-managing) | - | Active |
| Audiobooks | Audiobookshelf | TrueNAS Scale app | Libation / Readarr | qBittorrent | Active |
| Ebooks (Fiction) | CalibreWeb | TrueNAS Scale app | Calibre / Readarr | qBittorrent | Active |
| Ebooks (Non-Fiction) | CalibreWeb | TrueNAS Scale app | Calibre / Readarr | qBittorrent | Active |
| Ebooks (Reference) | CalibreWeb | TrueNAS Scale app | Calibre / Readarr | qBittorrent | Active |
| Music | Navidrome | TrueNAS Scale app | Lidarr | qBittorrent | Active |
| Podcasts | Audiobookshelf | TrueNAS Scale app | ABS (native) | ABS (native) | Active |
| Comics/Manga | Komga | TrueNAS Scale app | Manual import | Manual | Deferred |
| ROMs | RomM + EmulatorJS | TrueNAS Scale app | Manual import | Manual | Deferred |
| Internet Radio | Azuracast | TBD | - | - | Post-June |

---

## 3. Infrastructure

### 3.1 VLAN 80: Media (New)

VLAN 80 is created specifically for media-serving services. It has its own firewall policy distinct from Lab Services (VLAN 50) and DMZ (VLAN 60), allowing family device access without routing through infrastructure VLANs.

**Firewall policy (VLAN 80):**
- Allow: access from trusted family devices (personal device VLAN)
- Allow: outbound internet (metadata fetching, subtitle downloads)
- Block: access to VLAN 10 (Management), VLAN 50 (Lab), VLAN 60 (DMZ) except via defined rules
- Remote access via NGINX Proxy Manager (DMZ) only - not direct external access

**Note:** VLAN 80 is documented in Network & Services Architecture v1.6.

### 3.2 TrueNAS Scale Apps: Media Delivery (VLAN 80)

All media delivery services run as TrueNAS Scale apps on the R710, accessible via eno4 (10.0.80.5). They access media datasets directly via ZFS bind mounts - no NFS hop.

| Service | Port | Notes |
|---------|------|-------|
| Jellyfin | 8096 | Movies (incl. anime), TV, kids, anime shows, internet video |
| Audiobookshelf | 13378 | Audiobooks + podcasts |
| CalibreWeb | 8083 | Ebook serving; fiction, non-fiction, reference |
| Navidrome | 4533 | Music streaming |
| Immich | 2283 | Photo library; Google Photos replacement |
| Jellyseerr | 5055 | Family media requests → Radarr/Sonarr |
| Komga | 25600 | Comics/Manga (deferred) |
| RomM | 8998 | ROM library + EmulatorJS (deferred) |
| Azuracast | TBD | Internet radio (post-June) |

### 3.3 Hephaestus (Docker VM): VLAN 50 (Lab Services)

Hephaestus (10.0.50.30) is the homelab-wide shared Docker VM - a separate project with its own IaC (`infrastructure/hephaestus/`). Orpheus has no services running on Hephaestus. Future Productivity Stack services (Nextcloud, Vaultwarden) will run there but are out of scope for this document. See the Hephaestus Design Doc (planned).

### 3.4 TrueNAS Scale Apps: Download and File Management

| Service | Port | Notes |
|---------|------|-------|
| Prowlarr | 9696 | Indexer manager; syncs to all *Arr apps |
| Radarr | 7878 | Movie automation |
| Sonarr | 8989 | TV show automation |
| Lidarr | 8686 | Music automation |
| Readarr | 8787 | Ebook/audiobook automation |
| Bazarr | 6767 | Subtitle automation for Jellyfin |
| qBittorrent | 8080 | Torrent download client |
| Libation | - | Audible audiobook download (desktop app) |
| Calibre | - | Ebook management (headless or desktop) |
| yt-dlp | - | CLI; scripted via n8n or cron for internet video |

### 3.5 Hardware

| Hardware | Role |
|----------|------|
| Xeon E-2378 (main PVE node) | Hephaestus Docker VM (VLAN 50); no Orpheus services |
| R710 TrueNAS | All media files (ZFS) + all Orpheus services (TrueNAS Scale apps) |
| GPU (future) | Jellyfin hardware transcoding - would live in R710 or as PCI passthrough |

---

## 4. File Organization

### 4.1 Philosophy

The *Arr stack enforces naming conventions for everything it manages. Manual imports follow the same conventions. One root media folder per content type on TrueNAS; all services access datasets directly via ZFS bind mounts. No service maintains a private copy of files.

### 4.2 TrueNAS Directory Structure

```
/mnt/{pool}/media/
├── movies/                        # Radarr-managed
│   └── Movie Name (2024)/
│       └── Movie Name (2024).mkv
├── shows/                         # Sonarr-managed
│   └── Show Name/
│       └── Season 01/
│           └── Show Name - S01E01 - Episode Title.mkv
├── kids-movies/                   # Radarr (separate root folder)
├── kid-shows/                     # Sonarr (separate root folder)
├── anime-shows/                   # Sonarr (separate root folder)
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
├── books/
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

### 4.3 Storage Access

All Orpheus services are TrueNAS Scale apps running on the same host as the ZFS pools. Each app is configured with direct bind mounts to the relevant dataset paths - no NFS involved.

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

### 5.3 Lidarr & Music - Special Considerations

Lidarr is album-centric by design, which creates friction with a singles/playlists-heavy library. Mitigation:
- Configure Lidarr to monitor the "singles" album type - creates a virtual `{Artist} - Singles` folder per artist
- For existing disorganized music: import into Navidrome directly; use Lidarr for new acquisitions only
- Playlists are managed in Navidrome - Lidarr does not touch them

### 5.4 Readarr & Books - Special Considerations

Readarr handles acquisition; Calibre manages the library; CalibreWeb serves it. Libation remains preferred for Audible content. Readarr supports all three ebook categories via separate root folder configuration - one root folder per category pointing to the matching Calibre library directory.

---

## 6. Photos - Immich

### 6.1 Role

Immich is the long-term replacement for Google Photos - automatic mobile backup, facial recognition, shared libraries, familiar timeline UI. Runs as a TrueNAS Scale app alongside the rest of the Orpheus media stack, with direct access to the photos dataset on ZFS.

### 6.2 Migration Path

```
1. Configure mobile backup on all family devices
2. Export Google Photos via Google Takeout
3. Bulk import Takeout archive into Immich
4. Verify completeness; confirm family comfortable with Immich UI
5. Disable Google Photos backup on all family devices
6. 90-day hold on Google Photos (read-only safety net)
7. Delete Google Photos library
```

### 6.3 Family Access

Each family member gets their own Immich account. Shared libraries and albums for family photos. Mobile apps (iOS + Android) handle automatic backup.

---

## 7. Podcasts - ABS + Antennapod

Podcasts remain in Audiobookshelf. ABS handles RSS subscriptions, episode downloading, library organization, and progress sync via the gpodder protocol. Antennapod (Android) handles the listening experience - queue management, speed control, skip silence, chapter support - and syncs progress back to ABS.

**Fallback:** If ABS + Antennapod proves insufficient after real-world use, **Pinepods** is the documented next step.

---

## 8. Domain Registry

Three domains are owned and assigned by purpose. All external services are subdomains of the appropriate domain.

| Domain | Purpose | Notes |
|--------|---------|-------|
| sirhexx.com | Personal services - family-facing and homelab external access | Primary domain for all self-hosted service subdomains |
| hexxusweb.com | Professional services - work and portfolio-facing | Reserved for professional/career use |
| bravelittlesalamander.com | Wife's domain | Held for future use |

**Known sirhexx.com subdomains:**

| Subdomain | Service | Status |
|-----------|---------|--------|
| watch.sirhexx.com | Jellyfin | Configured |
| images.sirhexx.com | Immich | Configured |
| audible.sirhexx.com | Audiobookshelf | Configured |
| *(others TBD)* | Jellyseerr, CalibreWeb, Navidrome, Komga, RomM | Assign at deployment |

**Note:** Additional configured subdomains not listed here - inventory at deployment time and update this registry.

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

Pre-deployment task - serving services will not scan correctly against unstructured directories.

### 9.1 Priority Order

1. **Movies & TV** - must be clean before Jellyfin + Radarr/Sonarr deployment
2. **Music** - must be organized before Navidrome migration and Lidarr setup
3. **Audiobooks** - Libation re-downloads come pre-organized; non-Audible files need `{Author}/{Title}/{Title}.m4b` structure
4. **Ebooks** - import into Calibre once; Calibre manages structure thereafter
5. **Comics/Manga** - rename to `{Series}/{Series} #{Issue}.cbz` before Komga import (deferred)
6. **ROMs** - organize into `{System}/{Game}.{ext}` folders before RomM import (deferred)

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
| Komga | Deferred - post-June | Comics library cleanup required first |
| RomM + EmulatorJS | Deferred - post-June | ROM library organization required first |
| Recyclarr | Deferred | Add after *Arr stack is stable |
| Azuracast | Post-June | Internet radio; pairs with Navidrome music library |
| Pinepods | Contingency | Only if ABS + Antennapod proves insufficient |
| Nextcloud | Post-June (Productivity Stack) | Separate project; may integrate with media directories via WebDAV |

---

## 12. Workflow Status

| Service / Workflow | Status | Notes |
|-------------------|--------|-------|
| VLAN 80 (Media) | ✅ Done | pfSense + switch config applied |
| Hephaestus Docker VM (VLAN 50) | Separate project | See Hephaestus Design Doc (planned) |
| Jellyfin | Keep - configure in place | Already on TrueNAS Scale |
| Audiobookshelf | Keep - configure in place | Already on TrueNAS Scale |
| CalibreWeb | Keep - configure in place | Already on TrueNAS Scale |
| Navidrome | Keep - configure in place | Already on TrueNAS Scale |
| Immich | Keep - configure in place | Already on TrueNAS Scale |
| Jellyseerr | Build fresh - TrueNAS Scale | New |
| Prowlarr | Build fresh - TrueNAS Scale | New |
| Radarr | Build fresh - TrueNAS Scale | New |
| Sonarr | Build fresh - TrueNAS Scale | New |
| Lidarr | Build fresh - TrueNAS Scale | New |
| Readarr | Build fresh - TrueNAS Scale | New |
| Bazarr | Build fresh - TrueNAS Scale | New |
| qBittorrent | Build fresh - TrueNAS Scale | New |
| Google Photos → Immich migration | Planned | After Immich configured and stable |
| Komga | Deferred | Post-June |
| RomM | Deferred | Post-June |

---

## 13. Deployment Order

Requires R710 TrueNAS reconnected (Phase 1 prerequisite).

**Pre-deployment:**
1. ✅ Reconnect R710 TrueNAS - live at 10.0.10.30
2. ✅ Create VLAN 80 in pfSense + managed switch; set firewall policy
3. Clean up Movies + TV library (FileBot) before reconfiguring Radarr/Sonarr
4. Clean up Music library (MusicBrainz Picard) before reconfiguring Navidrome/Lidarr

**Configure existing media services (TrueNAS Scale - in place):**
5. Configure Immich family accounts + mobile backup on all devices
6. Reconfigure Jellyfin libraries (movies, TV, kids, anime shows, internet video)
7. Reconfigure Audiobookshelf; set up Antennapod gpodder sync
8. Reconfigure CalibreWeb; verify Calibre library path
9. Reconfigure Navidrome; verify music library path

**Download + automation stack (new):**
10. Deploy qBittorrent on TrueNAS Scale
11. Deploy Prowlarr; configure indexers
12. Deploy Radarr + Sonarr; connect Prowlarr + qBittorrent
13. Deploy Lidarr; connect Prowlarr + qBittorrent
14. Deploy Readarr; connect Prowlarr + qBittorrent
15. Deploy Bazarr; connect Sonarr + Radarr
16. Deploy Jellyseerr on TrueNAS Scale; connect Radarr + Sonarr

**Remote access:**
17. Configure NGINX Proxy Manager subdomains (watch, images, audible + TBD)
18. Test remote access for all family members on all services

**Google Photos migration:**
19. Begin Google Takeout export
20. Import into Immich; verify completeness
21. Disable Google Photos backup on all family devices
22. 90-day hold → delete Google Photos library

**Deferred (post-June):**
23. Deploy Komga + organize comics library
24. Deploy RomM + EmulatorJS + organize ROM library
25. Deploy Azuracast; connect to Navidrome music library

---

## 14. Infrastructure as Code

All Orpheus services are TrueNAS Scale apps - configured through the TrueNAS UI, not via Terraform or Ansible. There is no `infrastructure/orpheus/` IaC directory.

The only IaC touching Orpheus is:
- **pfSense Terraform** - VLAN 80 firewall rules (`infrastructure/network/pfsense/`)
- **Switch Ansible** - VLAN 80 port assignments (`infrastructure/network/switch/`)
- **Ariadne Ansible** - reverse proxy configs for Orpheus subdomains (`infrastructure/ariadne/`)

### 14.1 Recovery

Media files survive on TrueNAS ZFS - only service configurations need rebuilding after a TrueNAS failure.

Post-recovery steps:
1. Redeploy TrueNAS Scale; restore app configurations from TrueNAS backup
2. *Arr app configurations and Immich database live on TrueNAS - include in TrueNAS backup strategy
3. Jellyfin metadata cache rebuilds automatically on first scan (slow but automatic)
4. Re-verify all sirhexx.com subdomains resolve correctly through Ariadne after DNS propagation

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.2 · Network & Services Architecture v1.6 · Project Roadmap v1.3 · Mnemosyne Design Doc v1.1 · IaC Runbook v1.2 · Argus Design Doc v1.2 · Ariadne Design Doc v1.0*
