# Phemius Project: Living-Room Media Client Design Doc
**Version:** 1.0
**Last Updated:** 2026-09-09
**Status:** Planned — no hardware purchased. Phase 1 targeted at the living room; Phase 2 (office) gated on the server-closet move.

---

## Table of Contents
1. [Purpose & Philosophy](#1-purpose--philosophy)
2. [Scope & Phasing](#2-scope--phasing)
3. [Hardware & Port Map](#3-hardware--port-map)
4. [Panel Lockdown](#4-panel-lockdown)
5. [Software Stack](#5-software-stack)
6. [Content Sources](#6-content-sources)
7. [Live TV: Tunarr](#7-live-tv-tunarr)
8. [Library Conditioning](#8-library-conditioning)
9. [Profiles & Kid Access](#9-profiles--kid-access)
10. [Network Placement](#10-network-placement)
11. [Control & Input](#11-control--input)
12. [Security Model & Blast Radius](#12-security-model--blast-radius)
13. [Verification Gates](#13-verification-gates)
14. [IaC Integration](#14-iac-integration)
15. [Deployment Order](#15-deployment-order)
16. [Portfolio Notes](#16-portfolio-notes)

---

## 1. Purpose & Philosophy

Phemius is the household's performer — the device that plays what Orpheus holds, in the room
where the family actually gathers. Named for the bard of Odysseus's own hall at Ithaca, who sings
for the household and is the one man Odysseus spares on his return. The distinction from Orpheus
is deliberate and load-bearing: **Orpheus is the library, Phemius is who plays it in the living
room.**

See `docs/homelab-philosophy.md` for the broader goals this service supports. Phemius serves
the family-services and privacy goals directly: it replaces a vendor smart-TV OS with an interface
the household owns, and it removes a telemetry endpoint from the living room rather than merely
firewalling one.

**Design principles:**

- **The panel is a monitor.** The TV's operating system is removed from the equation entirely, not
  configured around. A smart TV that is merely blocked at the firewall is still one setup wizard
  away from being online.
- **The interface belongs to the household.** The device this replaces failed because its parental
  controls belonged to a vendor. Access rules that matter are enforced by content curation here,
  not by a toggle in someone else's product.
- **Self-hosted and commercial content do not share a device.** Anything requiring DRM runs on
  separate hardware on a separate network segment. That keeps the privacy win real instead of
  symbolic.
- **Uniformity by curation, not by re-encoding.** Where the library is inconsistent, the schedule
  works around it. Bulk transcoding is a last resort, not a first step.
- **Fail open.** If Phemius is unreachable or broken, the panel still has working HDMI inputs and
  the family can still watch something. This is the opposite of the Themis posture, and correctly
  so — a locked school tablet should fail closed, a family television should not.

---

## 2. Scope & Phasing

| Phase | Scope | Infrastructure state | Status |
|-------|-------|----------------------|--------|
| **Phase 1** | Living room — Vizio panel lockdown, Kodi client, Tunarr channels, kid profiles | Pre-move; wired to the existing TP-Link switch | Planned |
| **Phase 2** | Office — TCL 65S450G panel, gaming-focused (Batocera/emulation), media client secondary | Post server-closet move | Gated |

Phase 1 answers the immediate need: the living-room TV is a vendor appliance the household does
not control, and the media stack it should be consuming already exists on Orpheus. Phase 2 reuses
the displaced TCL panel and is deliberately deferred — it is a different workload (games first,
media second) and it should not complicate the Phase 1 build.

**One service, multiple hosts.** Phemius is a single service with a shared Ansible role. The
living-room and office machines are hosts within it (`phemius-livingroom`, `phemius-office`), not
separate services. Role variables carry the per-host differences.

**Out of scope:** Dolby Vision playback (see §5), commercial DRM apps on Phemius hardware (see
§3), and any attempt to make the Vizio panel's own OS usable.

---

## 3. Hardware & Port Map

**Panel:** VIZIO VQD65R-1010 — 65" Quantum QLED, 2024, Dolby Vision, 3× HDMI (HDMI 1 = eARC),
optical audio out, ATSC antenna input, USB 2.0 (1A). Assume 60Hz pending confirmation.

The panel has exactly three HDMI inputs and the build uses exactly three. There is no headroom;
any future device displaces one of these.

| Port | Device | Network | Rationale |
|------|--------|---------|-----------|
| HDMI 1 (eARC) | Phemius (N150 mini PC) | Wired, VLAN 80 | eARC is irrelevant with no receiver, so spending it on a source costs nothing |
| HDMI 2 | Nintendo Switch | WiFi, VLAN 20 | Unchanged from current state |
| HDMI 3 | Google TV device (onn 4K Pro) | Wired, quarantined VLAN | Commercial DRM only — see §12 |

**Bill of materials** (prices verified 2026-09-09; treat as estimates):

| Item | Purpose | Est. |
|------|---------|------|
| Intel N150 mini PC, 16GB / 500GB | Kodi host | $239 |
| Universal remote (SofaBaton-class) | One remote across all three inputs | $30–60 |
| Flirc USB | IR receiver — the mini PC has none | ~$25 |
| onn 4K Pro (2026) | DRM + the only path that drives the panel's Dolby Vision | $50–60 |
| Mini Bluetooth keyboard | Setup and search text entry | ~$15 |
| Cat6 ×2, keystones, wall plate | Ethernet runs behind the panel | $30–40 |
| **Total** | | **~$390–440** |

**Two Cat6 runs, not one.** The second run costs a few dollars while the wall is open and avoids
fishing it again for the DRM device. If only one run happens, the DRM device falls back to the
guest SSID (VLAN 70), which achieves the same isolation more slowly.

**Deliberately not purchased:** an Nvidia Shield. It duplicates the onn's role at four times the
price and reintroduces an always-online Android appliance, which is the thing this project exists
to remove.

---

## 4. Panel Lockdown

The goal is a panel that cannot reach the internet and does not want to. Three layers, in order of
reliability:

**Layer 1 — never network it.** During out-of-box setup after a factory reset, skip the network
step entirely. This is the whole strategy; the rest is defence in depth.

**Layer 2 — deny at the firewall.** A deny-all rule on the panel's MAC at pfSense, or placement on
VLAN 40 with no internet route. This lives in `infrastructure/network/pfsense/` and is already
under IaC, so it is reversible, reviewable, and survives a factory reset of the panel. **This is
the control that matters**, because the realistic failure mode is not the TV joining a stranger's
open WiFi — it is a future setup nag or a family member re-entering the WiFi password.

**Layer 3 — physical removal (optional).** With the warranty explicitly disclaimed, the internal
WiFi/BT module may be disconnected. Confirm before committing that it is a discrete card on a
ribbon rather than soldered, and note that on many panels the module is a combined WiFi/Bluetooth
part, so removing it also kills Bluetooth remote pairing.

> **The factory reset is not a privacy control.** ACR is firmware; it survives the reset, and the
> viewing-data toggles return enabled. Reset clears configuration clutter, nothing more.

---

## 5. Software Stack

**Base OS:** Debian 13, per the repo's Debian-first default.

**Kodi:** `kodi-gbm` with the standalone systemd service. No X server, no desktop environment, no
compositor. Boots directly to Kodi.

The common recipe — autologin to a desktop, then launch Kodi fullscreen — is rejected. It stacks a
display server and compositor beneath an application that wants direct control of the display
pipeline, and it is the fragile path for both HDR and audio passthrough. The GBM/KMS path is a
package plus a unit file, which also makes it a clean Ansible target.

**Ubuntu was considered and rejected.** The only substantive argument for Ubuntu over Debian was a
newer kernel and a current Kodi via the team-xbmc PPA — both of which matter *only* for HDR. A scan
of 1,741 library files returned **99.8% SDR** (exactly one Dolby Vision file and one HDR10 file),
so the entire advantage is worth one title. Debian, no PPA, nothing to maintain.

**Video expectations:** SDR output. HDR10 is not pursued. Dolby Vision is unavailable on Linux
regardless, and with one DV file in the library this costs nothing measurable.

**Audio:** PCM over HDMI, terminating at the panel's speakers. There is no AVR or soundbar and none
is planned, so there is no bitstreaming, no passthrough configuration, and no ARC/eARC involvement
— ARC exists to send audio *out* to a receiver, which is not this topology. The DTS:X and Dolby
Atmos badges on the panel are its own speaker-virtualisation DSP and are unreachable from Kodi.

---

## 6. Content Sources

| Source | Service | Kodi integration | Notes |
|--------|---------|------------------|-------|
| Video | Jellyfin (Orpheus, 10.0.80.5) | Jellyfin for Kodi | Actively maintained; the safe core. `JellyCon` is the lighter fallback if DB sync misbehaves |
| Live channels | Tunarr | IPTV Simple Client | See §7 |
| Music | Navidrome (Orpheus) | Subsonic add-on | **Weakest link** — Kodi's Subsonic add-ons are thinly maintained. Jellyfin's own music library is the documented fallback |
| YouTube (adults) | YouTube add-on | Official Kodi add-on | Personal API keys required. The Data API's 10k-unit daily quota is a real ceiling on a shared screen |
| YouTube (kids) | yt-dlp → Jellyfin | Jellyfin for Kodi | Curated allowlist — see §9 |
| SponsorBlock | `script.service.sponsorblock` | Separate add-on | Not a feature of the YouTube plugin |
| Broadcast TV | Panel's own ATSC tuner | None — separate input | Free, works fully offline, no transcoding. Not integrated into Kodi |

**Commercial DRM (Crunchyroll, Prime, Apple TV) is not installed on Phemius.** It runs on the onn
device on HDMI 3. See §12 for why.

---

## 7. Live TV: Tunarr

The original plan named ErsatzTV. **ErsatzTV was archived upstream in February 2026** — final
release, security updates only, with a Rust rewrite ("ErsatzTV Next") in early experimental
development. Building on it now means adopting a frozen project.

**Tunarr** replaces it: actively developed, Jellyfin-native, with a visual schedule editor.
Critically it supports the programming style this project is actually for:

- **Flex** — configurable blocks of time between programs.
- **Filler lists** — bumpers, interstitials, and commercials that play during Flex.
- **Mid-roll breaks** — splitting a long program into segments separated by filler.

That is the Adult Swim pattern: bumps between shows, breaks inside them. Filler content can be
sourced with **metube**, already running on TrueNAS.

**Host:** to be decided by Gate 3. If direct/remux mode holds (§8), Tunarr runs on **Hephaestus**
as a normal Docker service, per the repo's "Docker goes on the Docker host" convention. If full
transcode proves necessary, the N150's Intel graphics are currently the only hardware encoder in
the homelab — the R710's Xeons have no QuickSync and the T150's Xeon E-2378 is a non-G part with no
iGPU — and Tunarr would move onto Phemius as a documented exception.

**Library access:** Tunarr should pull through Jellyfin's API over HTTP on 10.0.80.5. Note that
NFS is exported from the R710's *management* NIC (10.0.10.30), not the media NIC, so file-level
access from VLAN 80 would require reaching into VLAN 10. If direct file access ever becomes
necessary, the correct fix is exporting NFS on `eno4` (10.0.80.5), **not** opening VLAN 80 → VLAN
10.

---

## 8. Library Conditioning

A scan of the movie and show libraries (1,741 files, `bin/scan-hdr-formats --codecs`) found the
library heterogeneous on every axis that matters for remuxing:

| Axis | Dominant value | Distinct values |
|------|----------------|-----------------|
| Resolution | 1920x1080 — 43.6% | **92** |
| Video codec | h264 — 72.8% (mpeg4 24.6%, hevc 2.1%) | 7 |
| Frame rate | 23.976 — 75.5% (29.97 17.8%) | 8 |
| Audio codec | aac — 50.4% (ac3 26.5%, eac3 11.2%, mp3 11.2%) | 10 |
| Audio channels | stereo — 72.9% (5.1 26.9%) | 5 |

Tiers: **1,094 files (62.9%)** are ≥700 lines tall; **498 (28.6%)** are below 500 lines; **427
(24.5%)** are mpeg4, concentrated at 720x408 and 640x352. The fully coherent core — 1080p + h264 +
23.976 — is **458 files (26.3%)**, and even that splits three ways on audio codec.

### 8.1 Strategy: curate per channel

**Uniformity only has to hold within a channel, not across the library.** Tunarr configures output
per channel, so the fix is scheduling rather than encoding:

- Build modern channels from the ≥700-line tier.
- Build a retro / late-night channel from the SD tier. Grainy SD content on a retro channel is a
  **feature** of the target aesthetic, not a defect.
- **Never mix 23.976 and 29.97 within a single channel.** Frame-rate conversion is the ugliest
  transform available and produces visible judder. This is a curation rule, and it costs nothing.

Bulk re-encoding the library is explicitly rejected. Re-encoding a 640x352 XviD produces a 640x352
h264 — generational loss for no gain — and upscaling to 1080p produces larger files with no
additional detail.

### 8.2 The one global pass worth running: audio

Audio is where most of the non-uniformity lives (10 codecs, 5 channel layouts) and it is by far the
cheapest axis to fix:

```
ffmpeg -i input.mkv -c:v copy -c:a ac3 -ac 6 output.mkv
```

Video streams are copied untouched — **no transcode, no quality loss** — and only audio is
re-encoded. This runs on CPU in minutes per file and collapses 10 audio codecs and 5 channel
layouts to one each.

Run this **only if** direct-mode testing (Gate 3) shows glitching at program boundaries. Operate on
copies, verify, and retain originals until the results are confirmed.

### 8.3 Going forward

Set Radarr/Sonarr quality profiles so **new** acquisitions stop adding to the problem. Backfill of
the SD tier, if it ever happens, should be by **re-download rather than re-encode** — replacement
is a genuine upgrade where re-encoding is not. At roughly 4TB for the SD tier, that waits on the
ISP change and on the *Arr reconfiguration already queued in the Orpheus plan.

---

## 9. Profiles & Kid Access

**This is a first-class requirement, not a convenience.** The device Phemius replaces was retired
in part because a child reached YouTube despite configured parental locks. That was not a UI bug;
it was a vendor parental-control failure, and it is the strongest argument for owning the
interface.

**Gate mechanism:** Kodi profiles, mapped onto the existing Jellyfin accounts.

| Kodi profile | Jellyfin account | Reachable |
|--------------|------------------|-----------|
| Kids | Kid account | `kid-movies`, `kid-shows`, curated YouTube library, kid-safe Tunarr channels |
| Adults | Adult account | Everything, including the live YouTube add-on |

Jellyfin-for-Kodi stores credentials per Kodi profile, so the gate is enforced at the server rather
than being cosmetic.

**YouTube for kids is an allowlist, not a filter.** No live YouTube add-on appears in the kids'
profile. Approved channels are pulled by **yt-dlp** into a curated Jellyfin library — a path the
Orpheus design doc already lists as active for Internet Videos — and surfaced as an ordinary
library with no search box reaching the open internet, no recommendation engine, and no ads. A
content allowlist is the only form of parental control that actually holds.

Kids' libraries are always reachable without a gate; the gate exists to keep everything else out.

---

## 10. Network Placement

| Host | VLAN | Addressing | Rationale |
|------|------|------------|-----------|
| `phemius-livingroom` | 80 (Media) | Static / DHCP reservation | Same segment as Jellyfin and Navidrome — no inter-VLAN rules needed for media |
| onn 4K Pro | Quarantine (40, or 70 guest via WiFi) | DHCP | Internet-only, no route inward |
| Vizio panel | None | Deny-all MAC block | See §4 |

Wiring the HTPC removes the constraint recorded at `network-services-architecture.md:100` —
the eero Pro 6's 2-SSID limit only ever applied to wireless clients, so a wired drop to the
TP-Link puts Phemius on any segment.

**Open item:** VLAN 80's outbound internet policy. Phemius needs apt and the YouTube API; VLAN 80
was scoped for media-*serving* services, not clients.

---

## 11. Control & Input

The mini PC exposes no HDMI-CEC. Consumer x86 mini PCs do not wire the CEC pin, so CEC-based
control is unavailable regardless of vendor — this is not an N150 limitation.

**Chosen approach: universal remote + Flirc USB.** Flirc is a USB IR receiver that maps any remote's
buttons to keystrokes Kodi consumes natively. A universal remote then drives all three inputs from
one device, and an activity macro ("Watch Kodi" → TV on, HDMI 1, remote switches to Kodi mode)
reproduces the power/input synchronisation that CEC would have provided.

> **Programming note:** set the remote's Kodi mode to a device profile the Vizio ignores (a Sony or
> Philips code set, for instance). Otherwise each button press drives Kodi *and* raises the panel's
> own OSD.

A Pulse-Eight USB-CEC adapter was the alternative. It was rejected because it controls only one
input, and its availability is inconsistent.

A mini Bluetooth keyboard is retained for setup and for search text entry, which is painful on any
remote.

---

## 12. Security Model & Blast Radius

**What this project removes:** a vendor smart-TV OS with ACR, on the family's most-used screen.

**What it must not quietly add back.** Installing Crunchyroll, Prime, and Apple TV add-ons on
Phemius would reinstall three vendors' telemetry one layer up, on a host with full access to the
media VLAN — and would do so at 720p, because Widevine L3 on Linux commonly caps below 1080p, using
community add-ons that break whenever a provider ships a change.

**Therefore:** commercial DRM runs on the onn device, on a quarantined segment with no route to
VLAN 80. It gets L1 hardware DRM, real 4K, Dolby Vision, and official apps that do not break; the
telemetry is confined to a device that cannot see the library. The trade is explicit and contained
rather than diffuse.

| Concern | Control |
|---------|---------|
| Panel telemetry | Never networked; deny-all MAC block; optional physical module removal (§4) |
| DRM vendor telemetry | Quarantined VLAN, no inward route |
| Phemius → Orpheus | Same VLAN; Jellyfin's own authentication |
| Kid content bypass | Server-side account separation, not client-side filtering (§9) |
| Loss of Phemius | Fails open — panel inputs still work; the Switch and onn are unaffected |
| Logging | Ships to Iris/Argus as a monitored endpoint (Phase 1 plan, Phase 3 delivery) |

---

## 13. Verification Gates

| # | Gate | Why it matters | Blocks |
|---|------|----------------|--------|
| 1 | **Does Debian 13 ship a usable `kodi-gbm`?** | If the packaged Kodi is too old, a backport is needed and the §5 rationale weakens | Phase 1 |
| 2 | **Does Flirc + the chosen universal remote drive Kodi cleanly without raising the panel OSD?** | The entire control story rests on this. Spike it before mounting anything behind the panel | Phase 1 |
| 3 | **Does Tunarr direct/remux mode hold across a real channel built from the coherent core?** | Determines whether Tunarr lands on Hephaestus or Phemius, and whether §8.2 is needed at all | Phase 1 |
| 4 | **Is the Vizio WiFi module a discrete card on a ribbon?** | Determines whether §4 Layer 3 is available; also whether BT remote pairing survives it | Optional |
| 5 | **Does VLAN 80 permit the outbound access Phemius needs (apt, YouTube API)?** | Client on a server segment — the policy was not written with clients in mind | Phase 1 |
| 6 | **Do Kodi profiles bind distinct Jellyfin credentials reliably?** | If profiles share a session, the kid gate is cosmetic and §9 must be redesigned | Phase 1 |
| 7 | **Panel refresh rate and HDMI version** | Recorded as an assumption (60Hz); confirm from the manual or the panel menu | Phase 1 |

---

## 14. IaC Integration

Phemius follows the repo's standard service layout. It is bare metal, so there is no Terraform
target — the **Iris precedent** applies. See `docs/iac-runbook.md` for tooling and workflow.

```
infrastructure/phemius/
├── CLAUDE.md
├── terraform/
│   └── .gitkeep              # bare metal — no Proxmox target
└── ansible/
    ├── ansible.cfg           # roles_path = roles:../../ansible/roles
    ├── inventory.ini         # phemius-livingroom (VLAN 80); phemius-office added in Phase 2
    ├── provision.yml
    ├── group_vars/
    │   └── phemius.yml       # jellyfin_url, tunarr_url, kodi_profiles, addon set
    └── roles/
        ├── kodi_gbm/         # package, systemd unit, no-X boot
        ├── kodi_addons/      # Jellyfin, IPTV Simple, Subsonic, YouTube, SponsorBlock
        ├── kodi_profiles/    # profile creation + per-profile credential binding
        └── flirc/            # IR keymap
```

**Vault variables** (convention: `vault_<service>_<credential>`):

- `vault_phemius_jellyfin_kid_password`
- `vault_phemius_jellyfin_adult_password`
- `vault_phemius_youtube_api_key`

**Not IaC-managed:** Tunarr channel definitions and filler lists (they live in Tunarr's own
database and are authored in its web UI), the universal remote's programming, physical panel
modifications, and the Kodi userdata directory. Kodi userdata should be backed up on a schedule —
the add-on configuration is the real asset — with the target and cadence still to be decided.

---

## 15. Deployment Order

1. Run two Cat6 drops behind the living-room TV. **First** — it is the only item with a lead time
   under your control, and it unblocks the VLAN placement.
2. Purchase the BOM (§3).
3. pfSense: deny-all MAC block for the panel; VLAN 80 rules for Phemius; quarantine segment for the
   onn.
4. Factory reset the Vizio and complete setup with the network step skipped (§4).
5. Install Debian 13 on the N150; provision via Ansible to `kodi-gbm` standalone.
6. Spike Gate 2 (Flirc + remote) before final mounting.
7. Add-ons and Jellyfin binding; create Kodi profiles and verify Gate 6.
8. Stand up the curated kids' YouTube library via yt-dlp/metube (§9).
9. Tunarr on Hephaestus; build one channel from the coherent core; test direct mode (Gate 3).
10. Expand channels per §8.1. Run the audio pass (§8.2) only if Gate 3 requires it.
11. onn 4K Pro on HDMI 3, quarantined segment, DRM apps only.
12. Ship logs to Iris/Argus.
13. **Phase 2:** office host, TCL panel, Batocera/emulation-first.

---

## 16. Portfolio Notes

Phemius is small, and its value as a portfolio piece is in the reasoning rather than the scale.

**Requirements derived from a failure.** The kid-access design (§9) exists because the previous
device failed at exactly that, and the fix is architectural — a server-enforced allowlist instead
of a client-side filter. Tracing a design requirement back to a concrete incident, rather than to a
feature list, is the transferable habit.

**Measurement before remediation.** The library conditioning strategy (§8) is built on a scan of
1,741 files rather than an assumption about what the library contained. That measurement reversed
two earlier decisions: it killed the Ubuntu-for-HDR argument outright (99.8% SDR), and it replaced
a proposed bulk re-encode with per-channel curation plus a targeted audio-only pass. Cheap
measurement changing an expensive plan is the point.

**Dependency currency as a design input.** ErsatzTV was the original plan and had been for some
time. Checking its upstream status before building on it surfaced that it was archived — the
difference between adopting a maintained tool and inheriting a frozen one.

**Isolation that survives convenience.** The DRM decision (§12) is the design's real test: the
easy path installs streaming add-ons on the box that is already there. Putting them on separate
hardware on a separate segment costs $50 and one HDMI port, and it is the only reason the privacy
work in §4 means anything.

**Fail-open as a deliberate choice.** Themis fails closed and Phemius fails open, for documented
reasons rooted in what each device is for. Recognising that the correct failure direction is a
property of the use case, not a house style, is the judgement worth showing.

---

*Part of the Homelab Command Project. Companion documents: Orpheus Design Doc v1.3 · Network & Services Architecture v1.9 · IaC Runbook v1.5 · Hardware Catalog v1.3 · Homelab Philosophy v1.0 · Themis Design Doc v1.0*
