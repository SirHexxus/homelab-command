# Themis Project: Mobile Device Management Design Doc
**Version:** 1.0
**Last Updated:** September 2026
**Status:** Planned — no infrastructure deployed. MVP (Sophy kiosk) targeted at an off-rack laptop PoC pending the ISP change and server-closet move.

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

Themis is the endpoint management plane of the homelab — the service that decides what a managed
device is allowed to be, and when. Named for the Titaness of divine law, custom, and established
order, who in Homer convenes and dissolves the assembly of the gods. Themis is not punishment
(that is Nemesis) and not surveillance (that is Argus); she is the settled order that a group
agrees to operate under. That distinction is the charter: Themis distributes policy to a fleet,
it does not watch people.

See `docs/homelab-philosophy.md` for the broader goals this service supports. Themis serves
the family services and skill-building goals: a child's tablet that stays on task during school
hours without a parent physically holding it, and a managed-mobility competency that transfers
directly to enterprise work.

**Design principles:**

- **Policy is distributed, not improvised.** Device state is the product of an assigned policy
  group, not of someone having changed a setting on the device.
- **Enrollment mode matches the relationship.** A child's school tablet is fully managed. An
  adult's personal phone gets a work profile they can remove. The tool does not decide this;
  the relationship does.
- **The control plane is never publicly exposed.** Themis holds device-owner authority over
  family hardware. It reaches devices over the VPN, not over a port-forward.
- **Every locked device has a documented way out.** A dead server must never mean a bricked
  tablet.
- **Fail closed.** If Themis is unreachable, a device holds its last policy. For the school
  tablet that means it stays locked, which is the correct direction to fail.

---

## 2. Scope & Phasing

Themis is scoped in two phases with a hard verification gate between them. The MVP answers an
immediate family need; the fleet phase is the portfolio piece.

| Phase | Scope | Enrollment mode | Status |
|-------|-------|-----------------|--------|
| **MVP** | One child's Onn tablet — Acellus-only kiosk with parent-triggered free time | Device Owner (fully managed) | Planned — off-rack PoC first |
| **Fleet** | James's and wife's Android phones/tablets — OS updates, app lifecycle, policy baselines | Work Profile (profile owner) | Gated — see §12 |

The MVP is deliberately narrow: restrict one tablet to educational use during school hours,
unlock recreation on parental trigger, and re-lock nightly. The fleet phase generalises Themis
into a household management plane and is where the portfolio value sits.

> [!IMPORTANT]
> The two phases may not share a backend. Headwind MDM is Device-Owner-centric and its Work
> Profile support is unverified. If it proves thin, the fleet phase moves to a self-hosted
> controller built against Google's Android Management API. See §12, Gate 2.

**Out of scope:** iOS/iPadOS (will not be used personally), Intune (deliberately not replicated
in the homelab), and content filtering / social media moderation. That last one is a separate
future service — the name **Sophrosyne** is reserved for it, since "soundness of mind" describes
cultivated judgment rather than an imposed device lock.

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
Parent taps NFC tag → Tasker fires HTTP POST with scoped API token
→ nginx → Headwind REST API → reassign device configurationId in Postgres
→ tablet picks up new policy on next check-in → launcher applies profile
```

**Control flow — scheduled lock:**

```
cron (Themis host, 20:00 local) → curl → Headwind REST API
→ reassign to Sophy: School → tablet check-in → kiosk returns to foreground
```

> [!NOTE]
> Policy application is **not instantaneous.** The Headwind client picks up changes on a
> check-in/push interval, and Android Doze can stretch that. Budget seconds to minutes and
> design the free-time unlock so a delay is not a fight. Measuring actual latency is an MVP
> deliverable (§12, Gate 4).

---

## 4. Policy Groups

Device state is expressed as a named policy group. The MVP defines one group with two modes.

### 4.1 Sophy — the child's tablet

Named for Sophrosyne, the Greek virtue of moderation and self-command. Sophy is the household
name for the kiosk policy; it is what the family actually says out loud ("Sophy locked the
tablet"). The service is Themis; Sophy is one policy group inside it.

**Sophy: School** — default state

| Setting | Value |
|---------|-------|
| Kiosk engine | Enabled — `com.hmdm.launcher` is the device launcher |
| App whitelist | Acellus (package TBD — see §12, Gate 3), system calculator, PDF reader |
| Status bar | Notification shade locked out |
| Navigation | Home, Back, and Recents disabled or hijacked by the launcher |
| Settings | Hidden behind the launcher administrator password |

**Sophy: Free Time** — unlocked state

| Setting | Value |
|---------|-------|
| Kiosk engine | Disabled |
| App whitelist | Broadened — YouTube, games, browser |
| Status bar | Restored |
| Navigation | Native Android navigation and launcher restored |

**Required user restrictions.** The kiosk profile is not self-protecting. Device Owner is a
privileged app, **not root**, and it is removed by a factory reset from recovery — which is the
first workaround a motivated child finds. The Sophy: School profile must therefore also set:

- `DISALLOW_FACTORY_RESET`
- `DISALLOW_SAFE_BOOT`
- `DISALLOW_DEBUGGING_FEATURES`

Which of these Headwind actually exposes is an MVP verification item (§12, Gate 5). Anything it
does not expose is an open door and must be recorded as accepted risk.

### 4.2 Fleet policy groups (Phase 2)

Deferred until Gate 2 resolves. Expected shape: an `Adults` group carrying update rings, a
managed app baseline, and compliance state — with no kiosk and no navigation restrictions.

---

## 5. Server Stack: Headwind MDM

**Application server:** Apache Tomcat 9
**Database:** PostgreSQL — local to the host in MVP, shared Postgres (10.0.50.14) after migration
**Client:** Headwind MDM launcher, `com.hmdm.launcher`
**Licence:** open-source community edition

Headwind is the right tool for the MVP specifically because it is Device-Owner-centric — the
kiosk, launcher replacement, and app whitelist are its core competency. It is chosen for the
MVP on that basis, not as a committed long-term platform for the fleet phase.

Tomcat heap is capped (`-Xmx768m`) during the laptop PoC; see §9.

---

## 6. Managed Endpoints & Enrollment Modes

| Device | Owner | Mode | Rationale |
|--------|-------|------|-----------|
| Onn Android tablet | Child | Device Owner | Full control required; device exists for schooling |
| Galaxy S24 FE | James | Work Profile | Personal daily driver; container only |
| Galaxy S23 FE | Wife | Work Profile | Personal daily driver; must be self-removable |
| Wife's future tablet | Wife | Work Profile | Possible laptop replacement — treat as personal |

> [!WARNING]
> Device Owner must never be applied to an adult's daily driver. It requires a factory reset to
> provision and hands Themis total control of a personal device. Work Profile is the correct
> mode for peers, and the ability to remove it is a feature, not a gap.

### 6.1 Enrollment paths

**QR provisioning (target path).** Factory-reset the tablet, tap the welcome screen six to seven
times to launch the setup wizard's QR reader, and scan a provisioning payload carrying the server
URL, network parameters, and the DPC download location. The device downloads the launcher over
HTTPS and assigns Device Owner.

Two requirements the original proposal missed:

- The payload must include `android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM`.
  Provisioning fails without it.
- The download URL must present a **publicly trusted** certificate. The setup wizard uses the
  system trust store, and no CA can be installed before the wizard runs, so a self-signed cert or
  a private CA will fail. See §8.

**ADB provisioning (MVP shortcut).** On a factory-reset device with no accounts added, sideload
the APK over USB and run:

```bash
adb shell dpm set-device-owner com.hmdm.launcher/.AdminReceiver
```

This bypasses the HTTPS chicken-and-egg entirely and unblocks profile testing immediately. It
does not exercise the QR flow, which must still be validated before final deployment.

> [!TIP]
> Every QR enrollment attempt costs a factory reset. Iterate on the payload against an emulator
> or a spare device before spending resets on the actual tablet.

---

## 7. Control Plane

### 7.1 Manual switching

A parent taps an NFC tag or a home-screen shortcut on their own phone. Tasker or MacroDroid
fires an authenticated HTTP POST at `themis.sirhexx.com`, and Headwind's REST API reassigns the
tablet's `configurationId`.

**Credential handling:** the macro uses a scoped API token, never the admin console credential.
Tasker stores it in plaintext on the phone, so the token must be independently revocable and
limited to configuration reassignment.

### 7.2 Scheduled automation

A cron job on the Themis host reassigns the tablet to Sophy: School at 20:00 local. The kiosk
launcher returns to the foreground on the next check-in, closing whatever recreational app is
open.

**Gaps to close before this is dependable:**

| Gap | Resolution |
|-----|-----------|
| Only the nightly lock is defined | Add a morning school-hours lock; define weekend and holiday behaviour |
| No timezone/DST handling | Pin cron to local time and document DST behaviour |
| Tablet offline at 20:00 | Policy applies at next check-in — acceptable, document it |
| Themis host offline at 20:00 | Lock does not fire. Not dependable until Themis is on the rack (§9) |

---

## 8. Certificate & Domain Strategy

**Hostname:** `themis.sirhexx.com`

> [!IMPORTANT]
> Enroll against a DNS name, never an IP. The server URL is baked into the client at enrollment.
> With the ISP change and rack move pending, an IP-based enrollment orphans the tablet the moment
> the address changes and costs a factory reset to recover. A DNS name makes the migration a
> record edit the tablet simply follows.

**Certificate:** Let's Encrypt via **DNS-01** challenge. DNS-01 requires no inbound reachability,
so a genuinely trusted certificate can be issued for a host that only exists on the LAN, with a
public A record pointing at a private address. This single decision satisfies three requirements
at once: the trusted chain that QR provisioning demands, a stable name, and migration survival.

`sirhexx.com` DNS is managed via the pfSense DDNS client against Namecheap (see Ariadne Design
Doc §3.1); DNS-01 additionally requires provider API credentials.

> [!CAUTION]
> Some routers strip private-IP answers for public hostnames as DNS-rebinding protection. Test
> resolution with `dig` from the tablet's VLAN before committing to this path.

---

## 9. MVP Deployment: Off-Rack PoC

The Proxmox node is unavailable pending an ISP change and a move to a dedicated air-conditioned
server closet. The MVP therefore runs on the ThinkPad, which already sits on the homelab network
at 10.0.20.103 (VLAN 20) and 10.0.10.68 (VLAN 10). The tablet joins the family SSID and lands on
VLAN 20 alongside it — same L2 segment, no inter-VLAN routing, no firewall rules, no ingress.

**No external availability is required for the MVP.**

### 9.1 Host constraints

| Resource | Reading | Consequence |
|----------|---------|-------------|
| RAM | 15 GiB total, ~2.9 GiB available, **no swap** | Binding constraint. Rules out a comfortable KVM VM |
| Disk | 28 GB free on a 75%-full root | Adequate for a container, tight for a VM image |
| Virtualisation | VMX present; `/dev/kvm` ACL grants access | KVM available but not the right choice |

### 9.2 Incus system container, not Docker or KVM

The PoC runs in an **Incus system container** (`incus 6.0.4`, Debian 13 repos) running Debian 13.
Rationale: it shares the host kernel so nothing is preallocated, it runs systemd like a real
host, and — decisively — a Proxmox LXC *is* an LXC. An Ansible role that provisions an Incus
container transfers to LXC 111 essentially unchanged.

A Docker Compose stack would prove Headwind runs but would teach nothing about the eventual
deployment, and the role would have to be written twice.

Cap the Tomcat heap given the absence of swap. Adding a swapfile before starting is cheap
insurance.

### 9.3 Known limitations of the PoC

- Laptop suspend halts check-ins; the nightly lock is not dependable off-rack.
- When the laptop leaves the house the tablet holds its last policy — fails closed if in
  Sophy: School, but free-time unlock is unavailable.
- Off-network and cellular control is untested until the VPN path exists.

---

## 10. Migration to Proxmox

**Allocation:** LXC VMID 111, 10.0.50.23, VLAN 50.

The PoC is not a throwaway. Because the Ansible role targets a Debian system container from the
outset, migration is an inventory swap and a re-run — not a rebuild. Every environment
difference lives in `group_vars`:

| Variable | PoC value | Rack value |
|----------|-----------|-----------|
| `postgres_host` | localhost (in-container) | 10.0.50.14 (shared Postgres, LXC 105) |
| `themis_proxy_mode` | local nginx | Ariadne (`rpadd themis.sirhexx.com 10.0.50.23:8080`) |
| `themis_domain` | themis.sirhexx.com | themis.sirhexx.com *(unchanged — this is the point)* |

Terraform is deferred until there is a Proxmox target to describe; `terraform/` carries a
`.gitkeep` in the interim, as Iris does.

**Post-migration additions:** pfSense rules for the tablet's segment, Ariadne proxy host, log
forwarding to Iris/Argus, and Postgres backup coverage.

---

## 11. Security Model & Blast Radius

The MVP's worst case is an annoyed child. The fleet phase's worst case is materially different:
an attacker holding the Themis admin credential would have app-install, remote-wipe, and
location authority over every daily-driver phone in the household. The controls below are
proportionate to the fleet phase and are **required before any adult device is enrolled.**

| Control | Requirement |
|---------|-------------|
| Network exposure | No port-forward. Devices reach Themis over WireGuard; Device Owner can enforce always-on VPN. Enrollment happens on home Wi-Fi |
| Admin authentication | MFA on the Headwind console; Authelia in front where it does not break client API paths |
| API credentials | Scoped, revocable tokens for automation. Never the admin credential |
| Backups | Postgres included in the homelab backup set, with a **tested** restore |
| Break-glass | Documented per-device un-enrolment. A dead Themis must never mean a bricked tablet |
| Consent | Wife's work profile is self-removable. Enrollment of an adult device is asked for, not imposed |

> [!NOTE]
> Publishing an MDM control plane to the open internet would contradict the standing perimeter
> principle recorded in the Network & Services Architecture: no internal service is directly
> exposed. Themis is not an exception to that rule.

---

## 12. Verification Gates

Open questions that must be resolved by testing, not assumption. Gates 1 and 3–5 are MVP work
and are all answerable on the laptop PoC.

| # | Gate | Why it matters | Blocks |
|---|------|----------------|--------|
| 1 | **Does the Headwind REST API reassign `configurationId` in a single authenticated call?** | The entire manual-switch and cron workflow rests on this. Spike it against a throwaway device before building any macro or script | MVP |
| 2 | **Does Headwind support Work Profile adequately?** | If not, the fleet phase moves to a self-hosted Android Management API controller | Fleet |
| 3 | **Acellus package name and network behaviour** | `com.acellus.acellus` is an assumption. Acellus leans on WebView, Play Services, and external content; too tight a whitelist breaks lessons mid-school-day | MVP |
| 4 | **Actual check-in / push latency** | Determines whether "instant" unlock is a reasonable expectation | MVP |
| 5 | **Which user restrictions Headwind exposes** | Factory reset, safe boot, and USB debugging restrictions determine whether the kiosk is actually enforceable | MVP |
| 6 | **Does the Onn model support QR provisioning?** | Budget MediaTek and Android Go tablets are inconsistent here | MVP |
| 7 | **Does the LAN resolve a public name to a private IP?** | DNS-rebinding protection would break the §8 certificate strategy | MVP |

---

## 13. IaC Integration

Themis follows the repo's standard service layout. See `docs/iac-runbook.md` for tooling,
secrets management, and workflow standards.

```
infrastructure/themis/
├── CLAUDE.md
├── terraform/
│   └── .gitkeep              # no Proxmox target until the rack move completes
└── ansible/
    ├── ansible.cfg           # roles_path = roles:../../ansible/roles
    ├── inventory.ini         # PoC: Incus container. Rack: 10.0.50.23
    ├── provision.yml
    ├── group_vars/
    │   └── themis.yml        # postgres_host, themis_domain, themis_proxy_mode
    └── roles/
        ├── java_tomcat/
        ├── postgres_local/   # PoC only; skipped when postgres_host is remote
        ├── headwind_mdm/
        └── nginx_local/      # PoC only; Ariadne takes over after migration
```

**Vault variables** (convention: `vault_<service>_<credential>`):

- `vault_themis_postgres_password`
- `vault_themis_admin_password`
- `vault_themis_api_key`

**Not IaC-managed:** the QR provisioning payload, device enrollment itself, policy group contents
authored in the Headwind console, and the Tasker/MacroDroid macros on the parent phone. Device
identifiers, the enrollment payload, and child-identifying detail stay **out of this repo** — it
is public. Policy content lives in the Headwind database; this doc describes its shape only.

---

## 14. Deployment Order

**MVP — laptop PoC:**

1. Install `incus`; launch a Debian 13 system container; add a swapfile on the host.
2. Write the Ansible role set against the container via `inventory.ini`.
3. Provision Tomcat 9, PostgreSQL, and Headwind MDM; cap the Tomcat heap.
4. **Spike Gate 1** — confirm the `configurationId` reassignment API call works. Stop here if it
   does not; the design changes.
5. Issue the Let's Encrypt DNS-01 certificate for `themis.sirhexx.com`; verify LAN resolution
   (Gate 7).
6. Factory-reset the tablet; enroll via ADB (§6.1) to unblock testing.
7. Build the Sophy: School and Sophy: Free Time policy groups; verify restrictions (Gate 5) and
   Acellus behaviour (Gate 3).
8. Measure check-in latency (Gate 4).
9. Wire the Tasker/NFC macro and the cron lock; test both end to end on the LAN.
10. Validate the QR provisioning payload, including the signature checksum, on an emulator or
    spare device (Gate 6). Re-enroll the tablet via QR.

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

Themis demonstrates managed-mobility competency without touching Intune or iOS — which matters,
because the team is shifting toward Mobility as a Service on exactly that stack.

**The competency transfers because the substrate is the same.** Intune manages Android through
Android Enterprise. Building against Device Owner, Work Profile, provisioning payloads, and
policy groups exercises the identical primitives an Intune administrator configures through a
different console. The vocabulary is deliberately mirrored in this document — enrollment modes,
policy baselines, compliance state, app lifecycle, update rings — so the work maps cleanly onto
enterprise MDM language in an interview.

**Enrollment architecture:** two enrollment modes chosen by relationship rather than convenience,
with a documented rationale for why a fully-managed profile is correct for one device and
inappropriate for another. This is the judgement call that distinguishes MDM practitioners from
MDM operators.

**Blast-radius analysis:** the security posture scales with scope rather than being fixed at
design time (§11). The controls required to manage one child's tablet and the controls required
to manage a household's daily drivers are explicitly different, and the difference is documented
rather than discovered.

**Verification discipline:** §12 records what was assumed versus what was tested, including an
assumption serious enough to invalidate the design if it fails (Gate 1). Spiking the highest-risk
unknown before building on it is the habit worth demonstrating.

**Migration under constraint:** the MVP was built off-rack, on a laptop, during an infrastructure
move, in a way that migrates by inventory swap rather than rebuild (§10). Designing for the
environment you have rather than the one you are waiting for is the transferable lesson.

---

*Part of the Homelab Command Project. Companion documents: Network & Services Architecture v1.9 · IaC Runbook v1.5 · Ariadne Design Doc v1.0 · Argus Design Doc v1.2 · Homelab Philosophy v1.0 · Project Roadmap v2.3*
