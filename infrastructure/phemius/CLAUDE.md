# phemius — living-room media client (Kodi HTPC)

**Wiki page:** [[Project - Phemius]]

The household's performer: the device that plays what Orpheus holds, in the
room where the family gathers. **Orpheus is the library; Phemius is who plays
it in the living room.** It replaces the vendor smart-TV OS with an interface
the household owns and removes a telemetry endpoint rather than firewalling
one. Full design in `docs/phemius-design-doc.md`.

| Field | Value |
|-------|-------|
| Host | Intel N150 mini PC (16GB / 500GB), bare metal — no Proxmox target |
| Hostname | `phemius-livingroom` (Phase 1); `phemius-office` (Phase 2) |
| IP | VLAN 80 (Media), DHCP reservation — **TBD**, allocated after the Cat6 drop |
| Panel | VIZIO VQD65R-1010, HDMI 1 — never networked (deny-all MAC block at pfSense) |
| OS | Debian 13 |
| Stack | `kodi-gbm` standalone (no X) + Jellyfin / IPTV Simple / Subsonic / YouTube / SponsorBlock add-ons; Tunarr on Hephaestus |
| IaC | Ansible (`ansible/`, Iris precedent); `terraform/` is a placeholder |
| Status | **Planned.** No hardware purchased; Cat6 drops are the first step |

## Scope

- **Phase 1 — living room:** panel lockdown, Kodi client, Tunarr virtual
  channels, kid profiles. Wired to the existing TP-Link switch, pre-move.
- **Phase 2 — office:** the displaced TCL 65S450G, gaming-first
  (Batocera/emulation) with media secondary. Gated on the server-closet move.

One service, multiple hosts: both machines are hosts in the `phemius` group
sharing one role set; per-host differences go in `host_vars/`.

## IaC layout

```
infrastructure/phemius/
  ansible/
    inventory.ini            ← [phemius] phemius-livingroom (ansible_host TBD)
    provision.yml            ← roles: kodi_gbm, kodi_addons, kodi_profiles, flirc (tag-gated)
    group_vars/phemius.yml   ← jellyfin_url, tunarr_url, kodi_profiles, kodi_addons
    roles/                   ← stubs — see "Spike before you build"
  terraform/.gitkeep         ← bare metal, no Proxmox resource
```

## Gotchas

1. **No X server, no desktop, no compositor.** `kodi-gbm` with the standalone
   systemd unit. The autologin-to-desktop-then-launch-Kodi recipe is rejected —
   it is the fragile path for both HDR and audio.
2. **SDR output.** The library scan was 99.8% SDR (one DV file, one HDR10).
   HDR10 is not pursued; Dolby Vision is unavailable on Linux regardless.
3. **PCM over HDMI to the panel speakers.** No AVR, no soundbar, no
   passthrough, no ARC/eARC. The panel's DTS:X/Atmos badges are its own DSP.
4. **The panel is never a network client.** Factory reset with the network
   step skipped; deny-all MAC block. It is a dumb display.
5. **No commercial DRM on Phemius.** Crunchyroll/Prime/Apple TV run on the onn
   4K Pro on HDMI 3, on a quarantined segment with no route to VLAN 80.
6. **Kid access is server-side.** Kodi profiles bind separate Jellyfin
   accounts; kids' YouTube is a yt-dlp allowlist surfaced as a Jellyfin
   library, not a filtered live add-on.
7. **VLAN 80 outbound policy is an open item (Gate 5).** Phemius needs apt and
   the YouTube API; VLAN 80 was scoped for media *servers*, not clients.
8. **No HDMI-CEC** — x86 mini PCs do not wire the pin. Control is a universal
   remote + Flirc USB; program the remote's Kodi mode to a code set the Vizio
   ignores or every press also raises the panel OSD.

## Spike before you build

`docs/phemius-design-doc.md` §13 lists seven gates. These block Phase 1:

- **Gate 1:** Debian 13 ships a usable `kodi-gbm` (else the §5 rationale weakens)
- **Gate 2:** Flirc + the chosen remote drive Kodi without raising the panel OSD —
  spike before mounting anything
- **Gate 3:** Tunarr direct/remux mode holds on a real channel — decides whether
  Tunarr lands on Hephaestus or Phemius
- **Gate 6:** Kodi profiles bind distinct Jellyfin credentials reliably — else the
  kid gate is cosmetic

## Vault variables

- `vault_phemius_jellyfin_kid_password`
- `vault_phemius_jellyfin_adult_password`
- `vault_phemius_youtube_api_key`

## Naming

Phemius is the bard of Odysseus's own hall at Ithaca — he sings for the
household, and is the one man Odysseus spares. Orpheus (the library) and
Phemius (the player) are deliberately distinct services.
