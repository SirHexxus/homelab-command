# Media Library Guide — v1.0 (2026-03-18)

## Overview

This document defines where every type of media lives, naming conventions, associated tools,
and migration rules from external storage (Seagate) to the NAS (TrueNAS R710 at `10.0.80.5`).

**NAS media root:** `/mnt/general_pool/media` (NFS-mounted on laptop at `/mnt/truenas-media`)

---

## Library Map

| Directory | Content | Tool | VLAN |
|-----------|---------|------|------|
| `movies/` | All films not approved for unsupervised kid viewing | Jellyfin | 80 |
| `shows/` | Live-action TV series | Jellyfin | 80 |
| `anime-shows/` | Anime series (AniDB metadata) | Jellyfin (separate library) | 80 |
| `kid-movies/` | Kids' films (any format, curated) | Jellyfin (separate library) | 80 |
| `kid-shows/` | Kids' TV series | Jellyfin (separate library) | 80 |
| `audiobooks/` | Audiobooks (Libation + others) | Audiobookshelf (ABS) | 80 |
| `podcasts/` | Podcast episodes | Audiobookshelf (ABS) | 80 |
| `songs/` | Music library | Navidrome | 80 |
| `manga/` | Manga series (CBZ) | Komga | 80 |
| `comics/` | Western comics (CBZ) | Komga | 80 |
| `books/` | eBooks (epub, mobi, pdf) | CalibreWeb | 80 |
| `photos/` | Personal photos | Immich | 50 |
| `roms/` | ROM files by system | RomM | 80 |
| `playlists/` | M3U playlists | — | — |
| `documents/` | Personal documents | — | — |
| `uploads/` | Incoming — Sonarr/Radarr staging | Arr stack | 80 |
| `temp/` | Scratch space — clear after use | — | — |
| `videos/` | Misc video clips (not shows/movies) | — | — |
| `backups/` | Backup archives | — | — |
| `thumbs/` | Thumbnail cache | Jellyfin | — |

---

## Anime Split Rule

**Anime series require a separate Jellyfin library** because they use AniDB/AniList metadata,
not TMDB/TVDB. Mixing anime and non-anime in the same library causes incorrect artwork,
wrong episode numbering, and broken season detection.

- Anime **series** go in `anime-shows/` — never in `shows/`
- Anime **films** go in `movies/` or `kid-movies/` based on kid-access rules — not a separate directory
- Apply Jellyfin's **"Other" → AniList** scraper on the `anime-shows/` library only
- Kid content goes in `kid-shows/` / `kid-movies/` regardless of format (anime or otherwise)

---

## Naming Conventions

### Movies
```
movies/
  Movie Title (Year)/
    Movie Title (Year).mkv
```
Examples:
- `Fight Club (1999)/Fight Club (1999).mkv`
- `2001 A Space Odyssey (1968)/2001 A Space Odyssey (1968).mkv`

### TV Shows
```
shows/
  Show Name/
    Season 01/
      Show Name - S01E01 - Episode Title.mkv
```

### Anime Shows
```
anime-shows/
  Series Name/
    Season 01/
      Series Name - S01E01.mkv
```

### Audiobooks
```
audiobooks/
  Author Last, First/
    Series Name/
      01 - Book Title/
        01 - Book Title.m4b       ← preferred format (chapters + metadata)
        cover.jpg
    Standalone Title/
      Standalone Title.m4b
        cover.jpg
```
- Libation exports go directly into this tree
- Non-Libation audiobooks: organize manually under `Author Last, First/`
- `.aax` files: Libation converts to `.m4b` — never store raw `.aax` on NAS
- Podcasts: separate from audiobooks — goes in `podcasts/`

### Music
```
songs/
  Artist Name/
    Album Title (Year)/
      01 - Track Title.flac       ← FLAC preferred; MP3 acceptable
      cover.jpg
```

### Manga
```
manga/
  Series Title/
    Series Title v01.cbz
    Series Title v02.cbz
    ...
    Series Title v01 c001.cbz     ← if chapter-level granularity needed
```
- All archives must be CBZ (ZIP-based). Convert RAR/ZIP → CBZ before ingesting.
- One archive per volume (preferred) or per chapter if volumes unavailable
- Folder = series title (romanized for Japanese titles; no special characters)

### Comics
```
comics/
  Publisher/
    Series Title/
      Series Title 001.cbz
      Series Title 002.cbz
      ...
```
- Same CBZ requirement as manga
- Group by publisher (Marvel, DC, Dark Horse, Image, etc.) → then series

### Books (eBooks)
```
books/
  Author Last, First/
    Book Title (Year).epub
```
- Calibre manages metadata — let CalibreWeb handle organization within its library

### ROMs
```
roms/
  {system}/
    {rom files}
```
Standard system directory names for RomM:
- `gba/` — Game Boy Advance
- `gbc/` — Game Boy Color
- `gb/` — Game Boy
- `nes/` — Nintendo Entertainment System
- `snes/` — Super Nintendo Entertainment System
- `ps1/` — PlayStation
- `neogeo/` — Neo Geo MVS/AES
- `genesis/` — Sega Genesis/Mega Drive
- `gamegear/` — Sega Game Gear
- `n64/` — Nintendo 64

ROM files stay in their original archival format (.zip, .7z, .chd, .cue+bin).
Do NOT extract ROMs — emulators read archives directly.

---

## Seagate Migration Plan

The Seagate drive (`/mnt/seagate`) holds the original unorganized archive.
Migration is handled by the `media-scripts` Python suite (`infrastructure/media-scripts/`).

### Content Map (Seagate → NAS)

| Seagate Path | Size | NAS Target | Notes |
|---|---|---|---|
| `masterFilePersonal/Videos/Movies/` | 306G | `movies/` or `kid-movies/` | Anime films → `movies/` or `kid-movies/` per access rules |
| `masterFilePersonal/Videos/Shows/` | 928G | `shows/` + `anime-shows/` | Split: anime series vs live-action |
| `masterFilePersonal/Videos/Videos/` | 1.9G | `videos/` | Misc clips |
| `masterFilePersonal/myGames/Emulators and Roms/ROMs/ROM Repositories/` | ~498G | `roms/{system}/` | See ROM systems below |
| `masterFilePersonal/myBooks/zip/` | 282G | `manga/` | ZIP manga archives → CBZ |
| `masterFilePersonal/myBooks/comicsAndManga/manga/` | 109G | `manga/` | Already in folders — needs CBZ audit |
| `masterFilePersonal/myBooks/comicsAndManga/comics/` | 8.1G | `comics/` | Mix of folders + .rar → CBZ |
| `masterFilePersonal/myBooks/Audiobooks/` | 92G | `audiobooks/` | Reorganize under Author/Series |
| `masterFilePersonal/Music/` | 19G | `songs/` | Reorganize Artist/Album |
| `masterFilePersonal/myBooks/pdf/` | 998M | `books/` | Import to Calibre |
| `masterFilePersonal/myBooks/standardBooks/` | 628M | `books/` | Import to Calibre |
| `masterFileGaming/` | 73G | `roms/` + review | Verify content type |

### ROM Systems on Seagate
| Directory | System | NAS Target |
|---|---|---|
| `[ReDump] Sony PlayStation (NTSC-U) (20150524)/` | PS1 | `roms/ps1/` |
| `[No-Intro] Nintendo - Game Boy Advance (14-03-2018)/` | GBA | `roms/gba/` |
| `[No-Intro] Super Nintendo Entertainment System (17-05-2018)/` | SNES | `roms/snes/` |
| `1G1R - MAMEdevs - Neo Geo MVS-AES/` | Neo Geo | `roms/neogeo/` |
| `[No-Intro] Nintendo - Game Boy Color (17-05-2018)/` | GBC | `roms/gbc/` |
| `[No-Intro] Nintendo Entertainment System (17-05-2018)/` | NES | `roms/nes/` |
| `[No-Intro] Nintendo - Game Boy (17-05-2018)/` | GB | `roms/gb/` |
| `[No-Intro] Sega Game Gear (17-05-2018)/` | Game Gear | `roms/gamegear/` |
| Individual GBA titles (not in repos) | GBA | `roms/gba/` |
| Individual GB/GBC titles | GB/GBC | `roms/gb/` or `roms/gbc/` |

**PS1 note:** The ReDump PS1 collection is 476G — largest single archive. Ingest last.
Many PS1 games will be in `.bin/.cue` or `.img` format; convert to `.chd` to save ~40% space
(use `chdman createcd --input game.cue --output game.chd`).

---

## Kids Content Access Management

### Strategy

The `kid-movies/` and `kid-shows/` libraries serve as a **human-curated approved list** —
not a ratings-filtered view. The content in these directories has been explicitly chosen as
appropriate for unsupervised viewing by the kids, regardless of official rating. This is
intentionally separate from TMDB/MPAA ratings, which are too coarse for household use.

### Jellyfin Profile Structure

| Profile | Libraries Visible | Notes |
|---|---|---|
| Adult (owner) | All libraries | Full access, no restrictions |
| Kids | `kid-movies/`, `kid-shows/` only | No access to `movies/` or `shows/` |

Kids profiles are configured in Jellyfin with library access restricted to `kid-movies/`
and `kid-shows/` only. No content rating cap is applied — the filesystem is the control.

### Content Placement Rules

- **kid-movies/ only** — films appropriate for unsupervised viewing by the kids
- **movies/ only** — films not approved for unsupervised viewing
- **No duplication** — a film lives in exactly one location. Adults can see `kid-movies/`
  through their profile, so nothing is inaccessible to them.
- **Straddling films** (e.g. The Nightmare Before Christmas, Labyrinth) go in `kid-movies/`
  if approved for unsupervised viewing — the deciding factor is parental judgement, not genre.

### Phased Access Plan

As the kids get older, access is expanded in stages rather than all at once:

1. **Current** — kid-movies/kid-shows only. Curated list grows as more films are approved;
   approved films are moved from `movies/` to `kid-movies/` as appropriate.

2. **Intermediate** — when ready, grant access to `movies/` with a content rating cap
   (e.g. max PG-13) configured on their Jellyfin profile. The kid-movies library remains
   as an override — films approved below the rating cap stay accessible regardless.

3. **Full access** — rating cap removed. At this point `kid-movies/` can be retired or
   kept as a "recommended for the family" collection.

### Adding a Newly Approved Film

1. Move the folder from `movies/` to `kid-movies/` on the NAS
2. In Radarr: update the movie's root folder from `/movies` to `/kid-movies`
3. Jellyfin will pick it up automatically on next library scan

---

## Tools Reference

| Tool | URL | Purpose |
|---|---|---|
| Jellyfin | `watch.sirhexx.com` | Video streaming (movies, shows, anime) |
| Audiobookshelf | `audible.sirhexx.com` | Audiobooks + podcasts |
| Navidrome | `music.sirhexx.com` | Music streaming |
| CalibreWeb | `books.sirhexx.com` | eBook library |
| Komga | *(TrueNAS app — planned)* | Manga + comics reader |
| RomM | *(TrueNAS app — planned)* | ROM library manager |
| Jellyseerr | `request.sirhexx.com` | Media request portal |
| Sonarr | `:30011` (local only) | TV show automation |
| Radarr | `:30021` (local only) | Movie automation |

---

## Ongoing Rules

1. **Uploads dir is staging only** — Sonarr/Radarr/qBittorrent deposit to `uploads/`, then
   Arr stack moves to `shows/` or `movies/`. Never treat `uploads/` as permanent storage.

2. **No mixed content in library dirs** — Anime never in `shows/` or `movies/`.
   Kids' content never in `shows/` or `movies/`. Adult content never anywhere in this tree.

3. **CBZ-only for manga/comics** — No .rar, .cbr, .zip allowed in Komga library dirs.
   Convert on import.

4. **Audiobooks: m4b preferred** — .mp3 folders acceptable but m4b (single file + chapters)
   is the target format. Convert loose mp3 folders when processing.

5. **Photos stay in Immich** — Personal photos do not go in the Jellyfin library.
   Immich handles photos/videos from phones; Jellyfin handles curated video content only.

6. **NAS is authoritative** — Seagate is source/archive. After successful migration and
   verification of each content type, the Seagate copy can be considered archived/redundant.

---

## Version History

| Version | Date | Changes |
|---|---|---|
| v1.2 | 2026-03-27 | Correct anime structure: anime-shows/ for series; films go in movies/kid-movies per access rules; movies/ is all non-kid-approved films |
| v1.1 | 2026-03-26 | Add kids content access management strategy and phased access plan |
| v1.0 | 2026-03-18 | Initial guide — full library map, Seagate migration plan, naming conventions |
