# Themis Project: Mobile Device Management Design Doc
**Version:** 1.5
**Last Updated:** 2026-10-05
**Status:** **MVP live** on the off-rack PoC — both tablets enrolled as Device Owner, per-device School/Free Time profiles, shared parent lock and Admin mode, 20:00/06:00 schedule, parent control page at `/sophy/`. Rack migration pending the server-closet move.

---

## Table of Contents
1. [Purpose & Philosophy](#1-purpose--philosophy)
2. [Scope & Phasing](#2-scope--phasing)
3. [Architecture Overview](#3-architecture-overview)
4. [Policy Groups](#4-policy-groups)
5. [Server Stack: Headwind MDM](#5-server-stack-headwind-mdm)
6. [Managed Endpoints & Enrollment Modes](#6-managed-endpoints--enrollment-modes)
7. [Control Plane](#7-control-plane)
8. [Certificate & Domain Strategy](#8-certificate--domain-strategy)
9. [MVP Deployment: Off-Rack PoC](#9-mvp-deployment-off-rack-poc)
10. [Migration to Proxmox](#10-migration-to-proxmox)
11. [Security Model & Blast Radius](#11-security-model--blast-radius)
12. [Verification Gates](#12-verification-gates)
13. [IaC Integration](#13-iac-integration)
14. [Deployment Order](#14-deployment-order)
15. [Portfolio Notes](#15-portfolio-notes)

---

## 1. Purpose & Philosophy

Themis is the endpoint management plane of the homelab — the service that decides what a managed device is allowed to be, and when. Named for the Titaness of divine law, custom, and established order, who in Homer convenes and dissolves the assembly of the gods. Themis is not punishment (that is Nemesis) and not surveillance (that is Argus); she is the settled order that a group agrees to operate under. That distinction is the charter: Themis distributes policy to a fleet, it does not watch people.

See `docs/homelab-philosophy.md` for the broader goals this service supports. Themis serves the family services and skill-building goals: a child's tablet that stays on task during school hours without a parent physically holding it, and a managed-mobility competency that transfers directly to enterprise work.

**Design principles:**

- **Policy is distributed, not improvised.** Device state is the product of an assigned policy group, not of someone having changed a setting on the device.
- **Enrollment mode matches the relationship.** A child's school tablet is fully managed. An adult's personal phone gets a work profile they can remove. The tool does not decide this; the relationship does.
- **The control plane is never publicly exposed.** Themis holds device-owner authority over family hardware. It reaches devices over the VPN, not over a port-forward.
- **Every locked device has a documented way out.** A dead server must never mean a bricked tablet.
- **Fail closed.** If Themis is unreachable, a device holds its last policy. For the school tablet that means it stays locked, which is the correct direction to fail.

---

## 2. Scope & Phasing

Themis is scoped in two phases with a hard verification gate between them. The MVP answers an immediate family need; the fleet phase is the portfolio piece.

| Phase | Scope | Enrollment mode | Status |
|-------|-------|-----------------|--------|
| **MVP** | One child's Onn tablet — Acellus-only kiosk with parent-triggered free time | Device Owner (fully managed) | Planned — off-rack PoC first |
| **Fleet** | James's and wife's Android phones/tablets — OS updates, app lifecycle, policy baselines | Work Profile (profile owner) | Gated — see §12 |

The MVP is deliberately narrow: restrict one tablet to educational use during school hours, unlock recreation on parental trigger, and re-lock nightly. The fleet phase generalises Themis into a household management plane and is where the portfolio value sits.

> [!IMPORTANT]
> The two phases may not share a backend. Headwind MDM is Device-Owner-centric and its Work Profile support is unverified. If it proves thin, the fleet phase moves to a self-hosted controller built against Google's Android Management API. See §12, Gate 2.

**Out of scope:** iOS/iPadOS (will not be used personally), Intune (deliberately not replicated in the homelab), and content filtering / social media moderation. That last one is a separate future service — the name **Sophrosyne** is reserved for it, since "soundness of mind" describes cultivated judgment rather than an imposed device lock.

---

## 3. Architecture Overview

```
[ Parent phone ]            [ Themis cron ]
  NFC tag / shortcut              |
  → Tasker/MacroDroid             |
        |                         |
        └──► HTTPS POST ──────────┘
             themis.sirhexx.com
                    |
                    ▼
        [ nginx — TLS termination ]
          MVP: local to Themis host
          Rack: Ariadne (10.0.60.10)
                    |
                    ▼
        [ Tomcat 9 — Headwind MDM ]  ◄──►  [ PostgreSQL ]
             10.0.50.23 (VLAN 50)            MVP: local
                    |                        Rack: 10.0.50.14
        (QR enrollment / client check-in)
                    ▼
        [ Onn tablet — VLAN 20 ]
          Device Owner; com.hmdm.launcher
```

**Control flow — manual profile switch:**

```
Parent taps NFC tag → Tasker fires HTTP POST as the dedicated `themis-api` user
→ nginx → Headwind REST API → reassign device configurationId in Postgres
→ tablet picks up new policy on next check-in → launcher applies profile
```

**Control flow — scheduled lock:**

```
cron (PoC: ThinkPad; rack: Themis host) → `bin/sophy-switch` → Headwind REST API
→ reassign to Sophy: School → MQTT push → kiosk returns to foreground
```

> [!NOTE]
> Policy application is **not instantaneous.** The Headwind client picks up changes on a check-in/push interval, and Android Doze can stretch that. Budget seconds to minutes and design the free-time unlock so a delay is not a fight. Measuring actual latency is an MVP deliverable (§12, Gate 4).

---

## 4. Policy Groups

Device state is expressed as a named policy group. The MVP defines one group with two modes.

### 4.1 Sophy — the children's tablets

Named for Sophrosyne, the Greek virtue of moderation and self-command. Sophy is the household name for the kiosk policy; it is what the family actually says out loud ("Sophy locked the tablet"). The service is Themis; Sophy is the family of policy groups inside it.

There are two tablets, and their school apps differ by age, so **each tablet has its own pair of configurations**, named after its Headwind device number: `sophy-01: School`, `sophy-01: Free Time`, `sophy-02: School`, `sophy-02: Free Time`. Which child holds which number, and which school app each School profile carries, is panel content — it is never written down in this repo. `bin/sophy-switch` derives the configuration name from the device number, so the control plane is identical for both.

**`<number>: School`** — default state

| Setting | Value |
|---------|-------|
| Kiosk engine | Enabled — `com.hmdm.launcher` is the device launcher |
| App whitelist | The tablet's school app (Acellus on one, ABC Mouse on the other — packages TBD, §12 Gate 3), system calculator, PDF reader |
| Status bar | Notification shade locked out |
| Navigation | Home, Back, and Recents disabled or hijacked by the launcher |
| Settings | Hidden behind the launcher administrator password |

**`<number>: Free Time`** — unlocked state

| Setting | Value |
|---------|-------|
| Kiosk engine | Disabled |
| App whitelist | Still a whitelist, just a wider one. Identical on both tablets as of 2026-09-21: the camera, ABC Mouse, Jellyfin (Orpheus, per-child account with parental limits), Mouse Timer, and Bible App for Kids. No browser, no YouTube, no Play Store |
| Status bar | Restored |
| Navigation | Native Android navigation and launcher restored |

**`Sophy: Locked`** — shared parent lock

One configuration for every tablet: kiosk mode with the Headwind launcher itself as the pinned app and an empty app list, status bar blocked, School's restrictions, and a "This tablet is locked. Ask a parent." header. Headwind's own device-lock flag is a premium-side feature the community server never sets, so a configuration is the equivalent. It serves bedtime, family time, and consequences alike. `unlock` always releases to School (fail-closed); Free Time is a deliberate parent action and is never scheduled. Locked → School is a kiosk-to-kiosk change the launcher ignores while pinned as its own content app, so `sophy-switch` bounces that transition through Free Time for a few seconds (observed and fixed 2026-09-13).

**`Sophy: Admin`** — shared parent administration

One configuration for every tablet, for setting a tablet up rather than for using it: kiosk off, status bar free, `lockSafeSettings` off, USB storage allowed, **no user restrictions**, and every registered app visible — the school apps, the Free Time set, Khan Academy Kids, **Settings**, **Aurora Store**, and **Chrome** (Play Services whitelisted but hidden). A distinct dark-red background makes the state obvious at arm's length. It exists because the launcher has no un-managed state: without it, signing into a school app that hands off to a browser, or fixing a permission, needed ADB. On the way out, School re-applies its restrictions.

**USB debugging stays a manual toggle.** Headwind cannot switch it on: the launcher's only `DevicePolicyManager.setGlobalSetting` call is `AUTO_TIME_ZONE`, and its remote-command hook runs unrooted as the app UID (`hmdm-android`, `Utils.java` / `SystemUtils.java`, checked 2026-09-13). Admin clears `no_debugging_features` so the Developer-options switch works again; a human still taps it. Recorded as accepted risk in §11.

**Schedule (laptop cron during the PoC):** 20:00 → `Sophy: Locked`, 06:00 → `<number>: School`, both tablets, every day. The 06:00 job also releases a consequence lock; a lock that must survive the morning is a follow-up.

The tablets reach Jellyfin through `watch.sirhexx.com` (Ariadne), not by IP; the direct path is 10.0.80.5:30013 — TrueNAS publishes the app on 30013, 8096 is only its container port — across VLAN 20 → 80, which the existing "Allow Personal to Media" pfSense rule permits. Each child signs into the Jellyfin app once, in Free Time, with their own restricted Jellyfin user (the same accounts Phemius plans for its Kids profile); the credentials live in Jellyfin and on the tablet, not here.

A family messaging client is queued as its own service, **Medon** (closed Matrix server on Hephaestus, FluffyChat on the tablets — see the roadmap). When it lands it is whitelisted in **both School and Free Time**, not Locked, so the children can always reach a parent.

**Required user restrictions.** The kiosk profile is not self-protecting. Device Owner is a privileged app, **not root**, and it is removed by a factory reset from recovery — which is the first workaround a motivated child finds. The Sophy: School profile must therefore also set:

- `DISALLOW_FACTORY_RESET`
- `DISALLOW_SAFE_BOOT`
- `DISALLOW_DEBUGGING_FEATURES`

Which of these Headwind actually exposes is an MVP verification item (§12, Gate 5). Anything it does not expose is an open door and must be recorded as accepted risk.

### 4.2 Fleet policy groups (Phase 2)

Deferred until Gate 2 resolves. Expected shape: an `Adults` group carrying update rings, a managed app baseline, and compliance state — with no kiosk and no navigation restrictions.

---

## 5. Server Stack: Headwind MDM

**Application server:** Apache Tomcat 9
**Database:** PostgreSQL — local to the host in MVP, shared Postgres (10.0.50.14) after migration
**Client:** Headwind MDM launcher, `com.hmdm.launcher`
**Licence:** open-source community edition

Headwind is the right tool for the MVP specifically because it is Device-Owner-centric — the kiosk, launcher replacement, and app whitelist are its core competency. It is chosen for the MVP on that basis, not as a committed long-term platform for the fleet phase.

Tomcat heap is capped (`-Xmx768m`) during the laptop PoC; see §9.

> [!WARNING]
> **Use the `master` launcher build, not `os`.** The installer hard-codes the open-source `hmdm-<ver>-os.apk`, in which `ProUtils.kioskModeRequired()` is a stub returning `false` — apps are whitelisted but never pinned. Kiosk mode is a Community-edition feature; it lives in the closed-source `hmdm-<ver>-master.apk`, signed with the same key (verified 2026-09-13), so it installs over `os` as a plain update with Device Owner intact. `group_vars` pins `headwind_launcher_variant: master` and the role points the launcher's version record at it.
>
> The `master` build signs its MQTT login with a secret that is not the server default, so with `mqtt.auth=1` its push connection is refused and it degrades to 15-minute polling. The broker runs with `mqtt.auth=0` (§11).

---

## 6. Managed Endpoints & Enrollment Modes

| Device | Owner | Mode | Rationale |
|--------|-------|------|-----------|
| Onn Android tablet | Child | Device Owner | Full control required; device exists for schooling |
| Galaxy S24 FE | James | Work Profile | Personal daily driver; container only |
| Galaxy S23 FE | Wife | Work Profile | Personal daily driver; must be self-removable |
| Wife's future tablet | Wife | Work Profile | Possible laptop replacement — treat as personal |

> [!WARNING]
> Device Owner must never be applied to an adult's daily driver. It requires a factory reset to provision and hands Themis total control of a personal device. Work Profile is the correct mode for peers, and the ability to remove it is a feature, not a gap.

### 6.1 Enrollment paths

**QR provisioning (target path).** Factory-reset the tablet, tap the welcome screen six to seven times to launch the setup wizard's QR reader, and scan a provisioning payload carrying the server URL, network parameters, and the DPC download location. The device downloads the launcher over HTTPS and assigns Device Owner.

Two requirements the original proposal missed:

- The payload must include `android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM`. Provisioning fails without it.
- The download URL must present a **publicly trusted** certificate. The setup wizard uses the system trust store, and no CA can be installed before the wizard runs, so a self-signed cert or a private CA will fail. See §8.

**ADB provisioning (MVP shortcut).** On a factory-reset device with no accounts added, sideload the APK over USB and run:

```bash
adb shell dpm set-device-owner com.hmdm.launcher/.AdminReceiver
```

This bypasses the HTTPS chicken-and-egg entirely and unblocks profile testing immediately. It does not exercise the QR flow, which must still be validated before final deployment.

> [!IMPORTANT]
> **Finish every ADB task before the tablet's first School switch.** School applies `no_debugging_features`, which switches USB debugging off; clearing the restriction later does not switch it back on — that takes a human in Developer options. Order used on 2026-09-13: install the `master` launcher, `set-device-owner`, `stay_on_while_plugged_in`, sideload Aurora Store and the apps, pull APK backups, *then* enroll. A fully managed device cannot add a personal Google account (the flow demands a managed one), so the Play Store is unusable; Aurora Store's anonymous mode installs the same apps, and Headwind whitelists them by package name with no URL.

> [!TIP]
> Every QR enrollment attempt costs a factory reset. Iterate on the payload against an emulator or a spare device before spending resets on the actual tablet.

---

## 7. Control Plane

### 7.1 Manual switching

A parent opens **the Sophy page** on their phone (§7.3) — or, for the NFC/Tasker path still planned, fires an authenticated HTTP POST at `themis.sirhexx.com` — and Headwind's REST API reassigns the tablet's `configurationId`.

**Credential handling:** Headwind has no API tokens — the private REST API authenticates panel users with a JWT (`POST /rest/public/jwt/login`, MD5 of the password). The macro therefore uses a dedicated panel user, `themis-api`, never the admin credential. Tasker stores its password in plaintext on the phone, so the user must be independently disable-able and hold the least role that still carries `edit_devices` (verify whether the built-in *User* role qualifies; otherwise *Admin* until a custom role is defined).

**The call itself** (`server/.../DeviceResource.java`, `updateDevice`):
`PUT /rest/private/devices` with `{"ids": [<deviceId>], "configurationId": <cfgId>}` updates the assignment and calls `pushService.notifyDeviceOnSettingUpdate` for each device — one authenticated request, push included. `infrastructure/themis/bin/sophy-switch` wraps login → lookup → PUT; the logic lives in `infrastructure/themis/lib/sophy_headwind.py`, which is the single backend for the CLI, the cron lock, and the parent page's API.

### 7.2 Scheduled automation

A cron job (on the ThinkPad during the PoC, on the Themis host after the rack move) runs `bin/sophy-switch <device> school` at the lock time. The kiosk launcher returns to the foreground on the next check-in, closing whatever recreational app is open.

**Gaps to close before this is dependable:**

| Gap | Resolution |
|-----|-----------|
| Only the nightly lock is defined | Add a morning school-hours lock; define weekend and holiday behaviour |
| No timezone/DST handling | Pin cron to local time and document DST behaviour |
| Tablet offline at 20:00 | Policy applies at next check-in — acceptable, document it |
| Cron host asleep at lock time | Lock does not fire. Not dependable until Themis is on the rack (§9) |

**Nightly reboot (server-side, live 2026-10-01).** Every tablet reboots at 10:00 UTC through a Headwind push-plugin scheduled task (`messageType: reboot`). Mode switches swap the configuration but never restart an app, so without it a process lives for the tablet's whole uptime. On 2026-10-01 ABC Mouse had been running in one process for about 29 hours and reached 2.5 GB on a 3.9 GB tablet, and the child heard harsh, distorted noise during play. A daily reboot caps every app's lifetime at one day. It also clears zombie tasks like the Jellyfin picture-in-picture one (§7.5).

The task runs on the Themis server itself, not on the laptop cron, so it fires even when the ThinkPad is asleep. The server runs on UTC, so the reboot drifts with daylight saving: 03:00 PDT, then 02:00 PST. Both are overnight, so the drift is accepted. The schedule exists only in the Headwind database, so `bin/sophy-schedule` holds it as a declarative table: `--check` reports drift and exits non-zero, `--dry-run` shows the changes, and no flag applies them. Run it after any rebuild or the rack migration.

### 7.3 Parent control page

`https://themis.sirhexx.com/sophy/` — one screen, one card per tablet showing the child's name, the **current mode**, and four buttons (School / Free Time / Locked / Admin), plus an "All tablets" row. Admin is a two-tap action. The page auto-refreshes so it doubles as a status board. Added to a phone's home screen it behaves like an app (web manifest, standalone display).

| Layer | Where | Notes |
|-------|-------|-------|
| Static page | `infrastructure/themis/web/` → `/opt/sophy/web/` | Vanilla HTML/CSS/JS; names come from the device `description` at runtime, never from the repo |
| API | `bin/sophy-web` → `sophy-web.service` on loopback `:8081` | stdlib `http.server`; `GET /state`, `POST /switch {number\|all, mode}`; imports `lib/sophy_headwind.py`, so the Locked → School bounce is shared |
| Auth | nginx `auth_basic` on `/sophy/` and `/sophy/api/`, over the existing TLS | One shared parent account (`parent`, `vault_themis_parent_password`); the API credential (`themis-api`) stays on the server in `/etc/sophy/env` |
| Deploy | `roles/sophy_web` + two locations in `nginx_local` | Runs on the Themis host on purpose: it must work through the rack outage and moves to LXC 111 with the rest |

Why not n8n or a separate LXC: both live on the rack, which goes dark for weeks around the server-closet move — the same reason Themis itself is off-rack. Reach is LAN-only (VLAN 20 → the host override in §8); remote access is a later Ariadne question. After the rack move the two `/sophy/` locations and the htpasswd move into Ariadne's vhost for `themis.sirhexx.com`.

**The page holds one JWT, it does not re-authenticate per poll.** The page refreshes every 30 s, and `GET /state` originally called `login()` each time — one full auth round-trip per poll, ~2,880 a day from a single open tab, which buried the Headwind audit log under 99.3% `jwt.login` rows and made it worthless both as a security record and as an Iris feed (§7.6). The token now lives on the handler class behind a lock and is renewed only on a 401; measured at 1 login per 10 polls instead of 10. Retrying a `/switch` after a 401 is safe because `switch()` no-ops when a device already holds the target configuration.

### 7.4 Off-home traffic: WireGuard back to home (queued)

**Status: queued, not built.** Away from the house — grandparents, a hotel, a friend's Wi-Fi — the tablets should behave exactly as they do at home: same DNS, same firewall policy, same reach to Jellyfin and to Themis itself. The design is a full tunnel to pfSense that engages on every network except the home SSID.

| Layer | Component | Notes |
|-------|-----------|-------|
| Server | pfSense native WireGuard package, one tunnel, UDP 51820 forwarded on WAN, endpoint = the DDNS name | Tunnel subnet `10.0.90.0/24`; one peer per tablet. Lives in `infrastructure/network/pfsense/config.xml` like every other rule |
| Policy | Firewall rules on the WG interface **mirror VLAN 20 (Personal)** | Away tablets get precisely the at-home reach: Orpheus, Themis (including MQTT `:31000`, so lock/unlock keeps working remotely), pfSense DNS, internet via the home WAN. The `themis.sirhexx.com` host override applies because DNS is pfSense's |
| Client | **WG Tunnel** (FOSS; F-Droid / Play), not the stock WireGuard app | The official app has no network-awareness on Android. WG Tunnel adds auto-tunnel on any Wi-Fi except a trusted-SSID list, a kill switch, and start-on-boot. Home SSID → trusted; everything else → `AllowedIPs = 0.0.0.0/0` |
| Lockdown | Android always-on VPN with "block connections without VPN" | Set over ADB (`settings put secure always_on_vpn_app` / `always_on_vpn_lockdown 1`) or by Device Owner. The child cannot disable it; tunnel down off-home means no traffic at all |
| Headwind | WG Tunnel whitelisted in every Sophy configuration, icon hidden; location permission granted via a `grantPermissions` push (Android needs it to read the SSID) | Same permission mechanism as any Aurora-installed app |

Accepted trade-offs, recorded so they are not rediscovered:

- "Home" is an SSID match. Adequate for a child; not a defence against a deliberately spoofed SSID. Anyone able to do that has bigger levers.
- The peer private key lives on the tablet. Kiosk protects it in practice; rotate the peer on any lost or reset tablet.
- Off-home throughput is bounded by the home upload; the children's Jellyfin users get a transcode ceiling.
- Setup needs one more ADB session per tablet (Admin + the manual USB-debugging toggle), so it rides along with the next Admin trip rather than earning its own.

Tailscale with an exit node was considered and passed over: simpler key management, but it cannot express "off only at home", and WireGuard on pfSense keeps the perimeter self-hosted and in IaC, which is the standing principle.

### 7.5 Device-side hardening: the layer below the MDM

Headwind distributes policy — which apps exist, which restrictions apply — but some of what keeps a tablet usable lives below it, in Android's per-package **appops** and **runtime permissions**. Headwind has no call for either. It neither shows them nor restores them, so a factory reset, a re-enrollment, or a "clear data" wipes them **silently**: the panel still reads green while the tablet carries known faults again. Device Owner is lost on any recovery-mode reset, so this is a realistic path, not a hypothetical one.

`bin/sophy-harden` is the answer — a declarative, idempotent table applied over ADB, with each entry carrying the incident that produced it:

| Package | Setting | Mechanism | Why |
|---------|---------|-----------|-----|
| `org.jellyfin.mobile` | `PICTURE_IN_PICTURE` → ignore | appop | A video in PiP when the 20:00 lock landed left an invisible, un-raisable task; Jellyfin would not open (2026-09-14) |
| `com.aofl.abcmouse` | `RUN_ANY_IN_BACKGROUND` → ignore | appop | ~20 AAudio streams left `state:started` after backgrounding played unattributable noise (2026-09-23). Necessary but not sufficient: it does not cover a foreground app with the screen off, nor the 2026-10-01 memory-starvation noise, which the nightly reboot (§7.2) handles |
| `com.bible.kids` | `POST_NOTIFICATIONS` → granted | permission | Pre-granted so no runtime dialog is ever raised at a child inside the kiosk |

`--check` reports drift and exits non-zero (usable from a health check); `--dry-run` shows the changes; no flag applies them. Every write is re-read to confirm it stuck, because both mechanisms accept writes they then discard.

**Two traps worth recording.** First, a permission-backed appop cannot be driven through `appops set`: `POST_NOTIFICATION` is slaved to the `POST_NOTIFICATIONS` runtime permission and silently ignores the write, so those entries must go through `pm grant` / `pm revoke` (verified 2026-09-23). Second, the diagnostic that found the audio fault generalises — **"audible but unattributable" on Android means an app playing without audio focus**, since focus is what populates the media notification and gives the volume control a target. `dumpsys audio` names the package in seconds; the screen never will. The sound itself tells the two ABC Mouse faults apart. Clean audio from an app that is no longer on screen is a leak. Harsh, distorted noise during play is the app missing its audio deadlines; check its memory (`am_pss` in the events log) before blaming audio.

Running it needs Admin plus the manual USB-debugging toggle (School sets `no_debugging_features` and kills ADB), so it rides along with other Admin trips rather than earning its own. Add an entry the day a new ADB-only fix is found, not later.

### 7.6 Telemetry and notifications: Iris integration (surveyed, partly blocked)

The intent is two-directional, over **one notification service** — Iris/ntfy — rather than a different mechanism per application:

- **Devices → parents.** Alert before a child is upset or out of policy: launcher escape (`defaultLauncher: false` / `mdmMode: false`), `sophy-switch` failures (today a failed 20:00 lock is invisible outside `cron.log`), check-in gaps, low battery, app-inventory changes, and `sophy-harden --check` drift.
- **Parents → devices.** "Locking in 15 minutes, are you ready to brush your teeth?", "battery below 20%, where is your charger?", "an update is coming, bring it to Dad."

**What Headwind actually exposes** (surveyed 2026-09-23). The device record (`GET /private/devices/number/{n}`) is the entire telemetry surface: `batteryLevel`, `lastUpdate` (the check-in heartbeat), `applications[]` (package + version), `kioskMode` / `mdmMode` / `defaultLauncher`, and `androidVersion` / `model` / `serial` / `permissions`. Installed plugins are **audit** and **messaging**; **devicelog** and **photo** return 404. There is no location, app-usage, or screen-time data — that is an edition and architecture gap, **not something a later phase of this project delivers**.

**The messaging plugin does not work.** `POST /plugins/messaging/private/send` exists and accepts, and the rows persist (`status: 0`), but **neither test message ever appeared on a tablet**. Do not build the device-bound direction on it.

**Open question that gates the device-bound half:** §4.1 locks the notification shade in kiosk mode, which is exactly the surface ntfy delivers to — and Locked and School are the modes where a bedtime warning matters most. Test ntfy on one tablet in each of Free Time, School and Locked before any design work. If the shade is suppressed, the choice is relaxing that lockout for a mode or finding an overlay mechanism. Tracked as an ADMIN task in Mnemosyne.

**Prerequisite, now fixed:** the audit log was 99.3% `jwt.login` noise (~2,900 rows/day) because `bin/sophy-web` authenticated on every `/state` poll. Forwarding it to Iris before fixing that would have shipped mostly noise. See §7.3.

### 7.7 App update pipeline (designed, not built)

**Status: designed 2026-10-05, not built.** Today every app on the tablets except the launcher was installed through Aurora, by hand, in Admin, one tablet at a time. Headwind's catalog knows those apps' package names but holds no APK for them, so it cannot install or update them. Nothing watches for new versions. A fix the vendor ships reaches a tablet only when someone remembers to open Aurora on it. The pipeline below closes that gap: watch for updates, fetch and verify them off the tablets, and hand Headwind a file it can distribute, with a parent approving each release.

**Worked through by hand on 2026-10-05.** ABC Mouse 1.70.1 was pulled from sophy-02, packaged as an XAPK, and staged on the Themis server for sophy-01. Every stage except watching and approval was done manually that day, and these facts came out of it:

| Fact | Consequence for the pipeline |
|------|------------------------------|
| Play apps ship as **split APKs** (ABC Mouse: base + `arm64_v8a` + `mdpi` + `en` + `es`). Headwind's own "split" flag is unrelated: it means one APK per CPU architecture | Distribute as **XAPK**: a zip of the splits plus a `manifest.json`. The server's `APKFileAnalyzer` reads `package_name`, `version_code`, `version_name` and `name` from the manifest, and launcher 6.39 has `XapkUtils` to install it |
| nginx caps request bodies at 200 MB (`client_max_body_size 200m`); the ABC Mouse XAPK is 260 MiB | Skip the panel upload. Write the file into `/opt/hmdm/files/` (served at `https://themis.sirhexx.com/files/`) and point the catalog version's `url` at it. Downloads are not capped |
| A new version is two calls: `PUT /private/applications/versions` (`applicationId`, `version`, `versionCode`, `url`), then `PUT /private/configurations/application/upgrade` with `{configurationId, applicationId}` in the body, once per configuration that uses the app. The panel's resource template reads `/configurations/:id/application/:appId/upgrade`, but those placeholders are never filled; that path returns 404 | The publish step is plain REST through `lib/sophy_headwind.py`; no panel automation. Take routes from the server classes, not the panel's URL templates |
| The launcher installs only the apps of the configuration the tablet is **currently** in | An update reaches a tablet the next time it enters a configuration that lists the app, not instantly. ABC Mouse is not in sophy-01's School, so sophy-01 updates in Free Time or Admin |
| An update must be signed with the same key as the installed app, or Android refuses it | Signature pinning is free to enforce and is the pipeline's main security control (below) |

**Stages.**

| # | Stage | What it does |
|---|-------|--------------|
| 1 | Watch | Nightly: for each app in the update table, compare the latest upstream version with the newest catalog version in Headwind |
| 2 | Fetch | Download the new release: split APKs from Google Play through `gplayapi` (Aurora Store's library) with anonymous login, or the upstream release directly for apps published outside Play |
| 3 | Verify | Signature pin, `libpairipcore.so` check, version-code check (below). Any failure stops the release and alerts |
| 4 | Package | Build the XAPK for split apps, or keep a single APK as is; record its SHA-256 |
| 5 | Stage | Write the file into `/opt/hmdm/files/` and add the catalog version. **No configuration is upgraded yet** |
| 6 | Approve | ntfy (Iris) alert: app, old → new version, size, signature fingerprint. A parent approves from the phone |
| 7 | Release | Upgrade every configuration that lists the app. Confirm per tablet from the device record's `applications[]` on its next check-in |

**Source per app.** Prefer the vendor's own channel and use Play only when there is no other. Jellyfin publishes signed releases on GitHub and F-Droid, so it needs no Play access at all. ABC Mouse, Bible App for Kids and Acellus are Play-only. The update table records each app's source, so a source can change without code changes.

**Play access: `gplayapi`, anonymous.** Aurora Store is not a separate store. It is a different client for the same Play backend, so its APKs are byte-for-byte what Play serves. Driving the Aurora *app* would need an Android VM and UI scripting, which is heavy and fragile. Its JVM library, `gplayapi`, runs headless on a server and supports two things the pipeline wants:

- **Anonymous login.** Aurora's token dispenser hands out shared accounts, so the pipeline holds no Google credential of ours and none of our accounts can be banned.
- **A device profile.** Play then serves exactly the splits an Onn 7" Core needs (`arm64_v8a`, `mdpi`, the device languages), the same set that arrived on sophy-02.

The dispenser is a third-party service. It has outages and rate limits, and Google periodically blocks the shared accounts. For a nightly check, a failed night is a retry, not an incident: alert after three consecutive fetch failures for the same app. Trusting the dispenser for logins does not mean trusting it for content, because stage 3 verifies every file whatever its source. A misbehaving source can cause a failed fetch, never a bad install. **Fallback:** a dedicated throwaway Google account, used only if the dispenser proves unreliable in practice.

**Security controls.** This pipeline puts new code on a child's Device Owner tablet, so the controls are not optional:

- **Signature pinning.** The pinned value is each app's signing-certificate SHA-256, taken once from the copy already installed and working on a tablet (`apksigner verify --print-certs`). A release whose certificate differs is rejected, whatever its source claims. This stops a tampered or swapped APK even when the download channel is compromised. Android would refuse to install it anyway, but failing on the server keeps a bad file out of the catalog altogether.
- **Play licensing check.** Reject any release containing `libpairipcore.so`. A release that newly adds Play Integrity licensing would fail on the kiosk tablets the way Minno did (2026-09-14), so it must not ship over a working version.
- **Version codes only increase.** A downgrade is a rollback attack or a fetch error; either way it stops.
- **A human approves every release.** Nothing is released to the tablets unattended, consistent with the household rule for autonomous actions. Approval is one tap; the notification carries the signature fingerprint and the version change.
- **No family account ever touches Play access.** Anonymous dispenser tokens are the default; the fallback account holds nothing and belongs to no one. Scripted Play downloads breach Google's terms either way; with anonymous login the realistic consequence is a failed fetch when a shared account is blocked. Accepted.

**Where it runs.** A separate unprivileged container, not the Themis host. The downloader handles untrusted input and talks to a third-party token service (and would hold the fallback Google credential); Themis holds Device Owner over the tablets. Keeping them apart means a compromised downloader can only offer files. It can put nothing in the catalog except through stage 3, and it cannot upgrade a configuration without approval. During the PoC it is a second Incus container on the ThinkPad. After the rack move it becomes its own LXC on VLAN 50, with an allocation recorded in the roster. The hand-off to `/opt/hmdm/files/` is the only write path into Themis, and it must not be able to touch anything else on that host.

**Rollback.** Keep the previous catalog version and its file for every app. Rolling back is a configuration pointing at the older version, but Android will not downgrade an installed app in place, so a bad release on a tablet means uninstall and reinstall. That is a reason for the approval step, not a gap in it.

**Open before building:**

- Whether launcher 6.39 installs an XAPK pushed through Headwind end to end. The first real test is the ABC Mouse 1.70.1 rollout to sophy-01. Record the result here.
- How the hand-off writes into `/opt/hmdm/files/`. Likely candidates are an Incus or Proxmox shared directory, or SSH with a forced command; the requirement is that the downloader can write that one directory and nothing else.
- The approval channel. ntfy action buttons can call back to a small endpoint, and `bin/sophy-web` already runs a loopback API behind the parent page's authentication (§7.3). Extending it with "pending releases" is the obvious candidate.

**Build order.** Signature pinning and the update table first, run by hand against the 1.70.1 rollout; then fetch and package; then the approval path; automation last.

---

## 8. Certificate & Domain Strategy

**Hostname:** `themis.sirhexx.com`

> [!IMPORTANT]
> Enroll against a DNS name, never an IP. The server URL is baked into the client at enrollment. With the ISP change and rack move pending, an IP-based enrollment orphans the tablet the moment the address changes and costs a factory reset to recover. A DNS name makes the migration a record edit the tablet simply follows.

**Certificate:** Let's Encrypt, **issued and renewed by Ariadne** exactly like every other `sirhexx.com` host. The pfSense DDNS client publishes a wildcard `*.sirhexx.com` A record at the WAN address and forwards 80/443 to Ariadne, so `rpadd themis.sirhexx.com 127.0.0.1:9` on Ariadne completes the normal HTTP-01 flow with no DNS or firewall changes. The upstream is a deliberate dead end: Themis is not internet-facing (§9); Ariadne's only job here is to own the certificate. `ansible/cert-sync.yml` copies `fullchain.pem`/`privkey.pem` into the PoC container for `nginx_local`; re-run it after each renewal (certbot renews ~30 days before expiry).

This satisfies the same three requirements the original DNS-01 plan targeted — a publicly trusted chain for QR provisioning, a stable name, and migration survival — without a Namecheap API credential. **DNS-01** (`acme.sh --dns dns_namecheap`) remains the fallback if Ariadne is unavailable when the certificate is needed; it requires Namecheap API eligibility and a whitelisted WAN IPv4.

> [!IMPORTANT]
> The certificate must exist **before the first enrollment**, ADB path included. The launcher is enrolled against `https://themis.sirhexx.com`; a self-signed placeholder it once trusted is not something it can be talked out of later. `nginx_local` refuses to start without the synced certificate for this reason.

**LAN resolution:** on the LAN, `themis.sirhexx.com` must resolve to the Themis host directly, not to the WAN address — the tablets need a straight TCP path for MQTT push on `:31000`, which an HTTP reverse proxy cannot carry, and they must keep working while the rack is down. A pfSense Unbound host override (`themis.sirhexx.com → 10.0.20.103` for the PoC, `10.0.50.23` after the move) does this; `config.xml` in `infrastructure/network/pfsense/` mirrors it. Unbound's `custom_options` already carries `private-domain: "sirhexx.com"`, so DNS-rebinding protection does not strip the private answer (Gate 7).

---

## 9. MVP Deployment: Off-Rack PoC

The Proxmox node is expected to go dark within weeks of the MVP for an ISP change and a move to a dedicated air-conditioned server closet. The MVP therefore runs on the ThinkPad, which already sits on the homelab network at 10.0.20.103 (VLAN 20) and 10.0.10.68 (VLAN 10), so the tablets stay manageable through the outage. The tablet joins the family SSID and lands on VLAN 20 alongside it — same L2 segment, no inter-VLAN routing, no firewall rules, no ingress. While the rack is still up, Ariadne is used opportunistically for the certificate (§8).

**No external availability is required for the MVP.**

### 9.1 Host constraints

| Resource | Reading | Consequence |
|----------|---------|-------------|
| RAM | 15 GiB total, ~2.9 GiB available, **no swap** | Binding constraint. Rules out a comfortable KVM VM |
| Disk | 28 GB free on a 75%-full root | Adequate for a container, tight for a VM image |
| Virtualisation | VMX present; `/dev/kvm` ACL grants access | KVM available but not the right choice |

### 9.2 Incus system container, not Docker or KVM

The PoC runs in an **Incus system container** (`incus 6.0.4`, Debian 13 repos) running Debian 13. Rationale: it shares the host kernel so nothing is preallocated, it runs systemd like a real host, and — decisively — a Proxmox LXC *is* an LXC. An Ansible role that provisions an Incus container transfers to LXC 111 essentially unchanged.

A Docker Compose stack would prove Headwind runs but would teach nothing about the eventual deployment, and the role would have to be written twice.

Cap the Tomcat heap given the absence of swap. Adding a swapfile before starting is cheap insurance. `bin/incus-poc-up` does the host preparation idempotently: packages, a 4 GiB swapfile, `incus admin init --minimal`, the container, root SSH, and the port exposure below.

**Networking:** the container sits on Incus's NAT bridge (`incusbr0`). macvlan is not an option over Wi-Fi, so the two ports the tablets need are exposed with Incus proxy devices on the laptop's addresses — `:443` (nginx) and `:31000` (MQTT push). Tomcat's `:8080` stays container-local. Ansible reaches the container at its bridge address; the laptop is both the Incus host and the controller.

### 9.3 Known limitations of the PoC

- Laptop suspend halts check-ins; the nightly lock is not dependable off-rack.
- When the laptop leaves the house the tablet holds its last policy — fails closed if in Sophy: School, but free-time unlock is unavailable.
- Off-network and cellular control is untested until the VPN path exists.

---

## 10. Migration to Proxmox

**Allocation:** LXC VMID 111, 10.0.50.23, VLAN 50.

The PoC is not a throwaway. Because the Ansible role targets a Debian system container from the outset, migration is an inventory swap and a re-run — not a rebuild. Every environment difference lives in `group_vars`:

| Variable | PoC value | Rack value |
|----------|-----------|-----------|
| `postgres_host` | localhost (in-container) | 10.0.50.14 (shared Postgres, LXC 105) |
| `themis_proxy_mode` | local nginx | Ariadne (`rpadd themis.sirhexx.com 10.0.50.23:8080`) |
| `themis_domain` | themis.sirhexx.com | themis.sirhexx.com *(unchanged — this is the point)* |

Terraform is deferred until there is a Proxmox target to describe; `terraform/` carries a `.gitkeep` in the interim, as Iris does.

**Post-migration additions:** pfSense rules for the tablet's segment, Ariadne proxy host, log forwarding to Iris/Argus, and Postgres backup coverage.

---

## 11. Security Model & Blast Radius

**Accepted risks recorded 2026-09-13 (PoC):**

- **MQTT push without authentication** (`mqtt.auth=0`, §5). The channel carries "re-fetch your configuration" nudges and the other push types the launcher understands (reboot, run app, exit kiosk); policy itself is fetched over HTTPS. Reachable only on the LAN via the Incus proxy device. Revisit if Headwind documents the `master` build's signing secret.
- **Launcher admin password = panel admin password**, on the tablets. Chosen for a 7" screen; a compromised tablet would expose the panel credential. Split them before the fleet phase.
- **Aurora Store remains installed** on both tablets for app updates; it is only reachable from `Sophy: Admin`, and `no_install_unknown_sources` blocks it while any other profile is active.
- **`Sophy: Admin` is a fully open tablet** — Settings, a browser, the store, no restrictions. It is a parent action behind the page password, and the 20:00 lock ends it; the risk is a tablet left in Admin during the day. USB debugging cannot be enabled remotely (§4.1), so Admin does not by itself expose ADB.
- **One shared parent password** on the control page (nginx basic auth over TLS, LAN-only). It can only move tablets between the five Sophy configurations; it cannot reach the panel.

The MVP's worst case is an annoyed child. The fleet phase's worst case is materially different: an attacker holding the Themis admin credential would have app-install, remote-wipe, and location authority over every daily-driver phone in the household. The controls below are proportionate to the fleet phase and are **required before any adult device is enrolled.**

| Control | Requirement |
|---------|-------------|
| Network exposure | No port-forward. Devices reach Themis over WireGuard; Device Owner can enforce always-on VPN. Enrollment happens on home Wi-Fi |
| Admin authentication | MFA on the Headwind console; Authelia in front where it does not break client API paths |
| API credentials | Scoped, revocable tokens for automation. Never the admin credential |
| Backups | Postgres included in the homelab backup set, with a **tested** restore |
| Break-glass | Documented per-device un-enrolment. A dead Themis must never mean a bricked tablet |
| Consent | Wife's work profile is self-removable. Enrollment of an adult device is asked for, not imposed |

> [!NOTE]
> Publishing an MDM control plane to the open internet would contradict the standing perimeter principle recorded in the Network & Services Architecture: no internal service is directly exposed. Themis is not an exception to that rule.

---

## 12. Verification Gates

Open questions that must be resolved by testing, not assumption. Gates 1 and 3–5 are MVP work and are all answerable on the laptop PoC.

| # | Gate | Why it matters | Blocks |
|---|------|----------------|--------|
| 1 | **Does the Headwind REST API reassign `configurationId` in a single authenticated call?** | **Passed 2026-09-13** — from source (`DeviceResource.updateDevice`, bulk branch; §7.1) and on hardware: `sophy-switch` flipped `sophy-01` and the tablet acted on it | MVP |
| 2 | **Does Headwind support Work Profile adequately?** | If not, the fleet phase moves to a self-hosted Android Management API controller | Fleet |
| 3 | **School-app package names and network behaviour** | **Passed for Acellus 2026-09-13** — `com.acellus.acellus` confirmed; two lessons completed inside the kiosk with the single-app whitelist. ABC Mouse (`com.aofl.abcmouse`) on the second tablet: package confirmed, signed in 2026-09-13, lesson run pending | MVP |
| 4 | **Actual check-in / push latency** | **Measured 2026-09-13: 1.2 s** from API call to the tablet's check-in, over MQTT push on the LAN (Onn 7" Core, Android 16, launcher 6.39). "Instant" is a fair expectation on-network; Doze behaviour off-charger still to observe. **2026-10-01, sophy-02:** an immediate `reboot` push reached the tablet in about 10–15 s, and it was fully booted about 80 s after the push. A scheduled push task went out about 1 minute after its cron minute (the plugin's scheduler granularity) | MVP |
| 5 | **Which user restrictions Headwind exposes** | **Passed 2026-09-13** — the configuration's `restrictions` field is a comma-separated list applied verbatim via `addUserRestriction`, so `no_factory_reset`, `no_safe_boot`, `no_debugging_features` (plus `no_install_unknown_sources`, `no_modify_accounts`) are all set; kiosk additionally blocks the status bar, screenshots, USB storage, and Settings | MVP |
| 6 | **Does the Onn model support QR provisioning?** | Budget MediaTek and Android Go tablets are inconsistent here | MVP |
| 7 | **Does the LAN resolve a public name to a private IP?** | **Answered 2026-09-13** — Unbound already exempts `sirhexx.com` via `private-domain`; a host override supplies the private answer (§8). Verify with `dig @10.0.20.1` from VLAN 20 | MVP |

---

## 13. IaC Integration

Themis follows the repo's standard service layout. See `docs/iac-runbook.md` for tooling, secrets management, and workflow standards.

```
infrastructure/themis/
├── CLAUDE.md
├── bin/
│   ├── incus-poc-up          # ThinkPad host prep (idempotent, --dry-run)
│   ├── sophy-switch          # CLI: school / free / lock / admin, --all, --status, --dry-run
│   └── sophy-web             # JSON API behind the parent page (loopback, --dry-run)
├── lib/
│   └── sophy_headwind.py     # Headwind client shared by both scripts (login → lookup → PUT)
├── web/                      # the parent control page (static; served under /sophy/)
├── terraform/
│   └── .gitkeep              # no Proxmox target until the rack move completes
└── ansible/
    ├── ansible.cfg           # roles_path = roles:../../ansible/roles
    ├── inventory.ini         # [themis]: PoC container or 10.0.50.23; [ariadne]: cert source
    ├── provision.yml
    ├── cert-sync.yml         # Ariadne → container copy of the Let's Encrypt files
    ├── group_vars/
    │   ├── all.yml           # themis_domain, themis_cert_dir (shared with Ariadne play)
    │   └── themis.yml        # postgres_host, themis_proxy_mode, Tomcat/Headwind versions
    └── roles/
        ├── java_tomcat/      # OpenJDK 21 + upstream Tomcat 9 tarball, loopback-only
        ├── postgres_local/   # PoC only; skipped when postgres_host is remote
        ├── headwind_mdm/     # replicates hmdm_install.sh idempotently
        ├── nginx_local/      # PoC only; Ariadne takes over after migration
        └── sophy_web/        # sophy-web service, static page, parent htpasswd
```

**Vault variables** (convention: `vault_<service>_<credential>`):

- `vault_themis_postgres_password`
- `vault_themis_admin_password`
- `vault_themis_api_password` — the `themis-api` panel user (§7.1)
- `vault_themis_parent_password` — the shared login for the control page (§7.3)

**Not IaC-managed:** the QR provisioning payload, device enrollment itself, policy group contents authored in the Headwind console, and the Tasker/MacroDroid macros on the parent phone. Device identifiers, the enrollment payload, and child-identifying detail stay **out of this repo** — it is public. Policy content lives in the Headwind database; this doc describes its shape only.

---

## 14. Deployment Order

**MVP — laptop PoC:**

1. `sudo bin/incus-poc-up` on the ThinkPad; set `ansible_host` in `inventory.ini`; create `group_vars/vault.yml`.
2. On Ariadne: `rpadd themis.sirhexx.com 127.0.0.1:9`. pfSense host override `themis.sirhexx.com → 10.0.20.103` (GUI, mirrored in `config.xml`). Verify Gate 7 with `dig`.
3. `cert-sync.yml`, then `provision.yml` — Tomcat 9 (heap capped), PostgreSQL, Headwind, nginx.
4. In the panel: change nothing about `admin` (Ansible set its password); create `themis-api`; add devices `sophy-01` and `sophy-02`; create the four configurations (`<number>: School` and `<number>: Free Time` for each), with the right school app in each School profile and Jellyfin in each Free Time profile.
5. Enroll the first tablet via ADB (§6.1) against `https://themis.sirhexx.com`.
6. **Gate 1 on hardware:** `bin/sophy-switch sophy-01 free` — record the push latency (Gate 4).
7. Verify restrictions (Gate 5) and the school app's behaviour (Gate 3); enroll the second tablet and repeat with its school app.
8. Cron lock/unlock on the ThinkPad; Tasker/NFC macro on the parent phone; test both on the LAN.
9. Validate the QR provisioning payload, including the signature checksum, on an emulator (Gate 6); one real QR enrollment to confirm.

**Rack migration (post server-closet move):**

11. Provision LXC 111 at 10.0.50.23 via Terraform.
12. Re-point `group_vars` at the shared Postgres; migrate the database.
13. Re-run `provision.yml` against the new inventory target.
14. Update the `themis.sirhexx.com` A record; confirm the tablet reconnects without re-enrollment.
15. Add the Ariadne proxy host; retire the local nginx role.
16. Add pfSense rules for the tablet's segment; forward logs to Iris/Argus.
17. Add Themis Postgres to the backup set and **test the restore**.

**Fleet phase:** gated on Gate 2 and on the §11 controls being in place.

---

## 15. Portfolio Notes

Themis demonstrates managed-mobility competency without touching Intune or iOS — which matters, because the team is shifting toward Mobility as a Service on exactly that stack.

**The competency transfers because the substrate is the same.** Intune manages Android through Android Enterprise. Building against Device Owner, Work Profile, provisioning payloads, and policy groups exercises the identical primitives an Intune administrator configures through a different console. The vocabulary is deliberately mirrored in this document — enrollment modes, policy baselines, compliance state, app lifecycle, update rings — so the work maps cleanly onto enterprise MDM language in an interview.

**Enrollment architecture:** two enrollment modes chosen by relationship rather than convenience, with a documented rationale for why a fully-managed profile is correct for one device and inappropriate for another. This is the judgement call that distinguishes MDM practitioners from MDM operators.

**Blast-radius analysis:** the security posture scales with scope rather than being fixed at design time (§11). The controls required to manage one child's tablet and the controls required to manage a household's daily drivers are explicitly different, and the difference is documented rather than discovered.

**Verification discipline:** §12 records what was assumed versus what was tested, including an assumption serious enough to invalidate the design if it fails (Gate 1). Spiking the highest-risk unknown before building on it is the habit worth demonstrating.

**Migration under constraint:** the MVP was built off-rack, on a laptop, during an infrastructure move, in a way that migrates by inventory swap rather than rebuild (§10). Designing for the environment you have rather than the one you are waiting for is the transferable lesson.

---

*Part of the Homelab Command Project. Companion documents: Network & Services Architecture v1.9 · IaC Runbook v1.5 · Ariadne Design Doc v1.0 · Argus Design Doc v1.2 · Homelab Philosophy v1.0 · Project Roadmap v2.4*
