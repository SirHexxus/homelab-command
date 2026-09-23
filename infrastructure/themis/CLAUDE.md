# themis — Android endpoint management (MDM)

**Wiki page:** [[Project - Themis]]

The homelab's device management plane. Distributes policy to managed Android
endpoints: a child's school tablet now, family phones later. Full design in
`docs/themis-design-doc.md`.

| Field | Value |
|-------|-------|
| VMID | 111 |
| IP | 10.0.50.23 (VLAN 50 — Lab Services) |
| Hostname | themis.sirhexx.com |
| OS | Debian 13 |
| Stack | Tomcat 9 + Headwind MDM + PostgreSQL |
| IaC | Ansible (`ansible/`), host prep in `bin/`; `terraform/` deferred until the rack move |
| Status | **MVP in progress** — off-rack PoC on the ThinkPad; see design doc §14 for the order |

## Current state: off-rack PoC

The Proxmox node goes dark for an ISP change and the move to the server closet
within weeks of the MVP. The MVP runs in an **Incus system container on the
ThinkPad** — not Docker, not KVM — so the tablets stay manageable through the
outage. A Proxmox LXC is an LXC, so the same Ansible role transfers to VMID 111
unchanged; Docker would mean writing the role twice, and the laptop has no swap
and little free RAM, which rules out a comfortable VM.

Bring-up order (details in design doc §14):

```bash
sudo bin/incus-poc-up                      # incus, adb, swap, container, SSH, ports
cd ansible && ansible-vault create group_vars/vault.yml   # 4 vault_themis_* values
ssh root@10.0.60.10 rpadd themis.sirhexx.com 127.0.0.1:9   # Ariadne issues the cert
ansible-playbook -i inventory.ini cert-sync.yml            # copy it into the container
ansible-playbook -i inventory.ini provision.yml --ask-vault-pass
```

`bin/sophy-switch <device> school|free|lock|admin` is the control plane (cron +
NFC macro); it reads `THEMIS_URL`/`THEMIS_USER`/`THEMIS_PASSWORD` from the
environment. Parents use the same thing from a phone at
`https://themis.sirhexx.com/sophy/` — a static page plus `bin/sophy-web`
(loopback JSON API) behind nginx basic auth, deployed by `roles/sophy_web`.
Both scripts import `lib/sophy_headwind.py`; change the switching logic there.
Admin mode opens everything but **cannot turn USB debugging on** (Headwind has
no call for it) — a human toggles it in Developer options.

`bin/sophy-harden` reapplies the device-side settings Headwind *cannot* express
— per-package appops and runtime permissions, set over ADB. Each entry is there
because something broke in production (Jellyfin's PiP zombie task, ABC Mouse's
leaked background audio), and a factory reset or re-enrollment loses all of them
silently, with nothing in the panel to say so. It is declarative and idempotent:
`--check` reports drift and exits non-zero, `--dry-run` shows the changes, no
flag applies them. Run it after any reset, re-enrollment, or new app install,
with the tablet in Admin and USB debugging on.

Migration to the rack is an inventory swap and a re-run. Keep every environment
difference in `group_vars/themis.yml`:

| Variable | PoC | Rack |
|----------|-----|------|
| `postgres_host` | localhost | 10.0.50.14 (LXC 105) |
| `themis_proxy_mode` | local nginx | Ariadne (10.0.60.10) |
| `themis_domain` | themis.sirhexx.com | unchanged — deliberately |

## Rules that are easy to get wrong

1. **Enroll against the DNS name, never an IP.** The server URL is baked into
   the client at enrollment. An IP-based enrollment orphans the tablet when the
   address changes during the rack move, and recovery costs a factory reset.
2. **The certificate comes from Ariadne and must exist before the first
   enrollment — ADB path included.** `rpadd themis.sirhexx.com 127.0.0.1:9` on
   Ariadne issues it through the normal HTTP-01 flow (wildcard DDNS → WAN →
   pfSense → Ariadne); `ansible/cert-sync.yml` copies it into the container.
   Re-run cert-sync after each renewal. `nginx_local` deliberately has no
   self-signed fallback: the launcher is enrolled against
   `https://themis.sirhexx.com` and a cert it once rejected costs a factory
   reset. QR provisioning additionally needs the chain to be publicly trusted
   (setup wizard uses the system store) — Let's Encrypt satisfies both. For
   local iteration, sideload and use
   `adb shell dpm set-device-owner com.hmdm.launcher/.AdminReceiver`.
3. **The QR payload needs `PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM`.**
   Provisioning fails silently-ish without it.
4. **Device Owner is not root and is not permanent.** A factory reset from
   recovery removes it. The kiosk profile must also set `DISALLOW_FACTORY_RESET`,
   `DISALLOW_SAFE_BOOT`, and `DISALLOW_DEBUGGING_FEATURES` — verify Headwind
   exposes them and record whatever it does not as accepted risk.
5. **Device Owner never goes on an adult's daily driver.** Work Profile is the
   correct mode for peers, and it must stay self-removable.
6. **Nothing identifying goes in this repo.** It is public. Device serials, the
   enrollment payload, and child-identifying detail — including which child
   uses which tablet — live in the Headwind database and the private wiki, not
   in git. Device numbers are neutral (`sophy-01`, `sophy-02`).
7. **On the LAN, `themis.sirhexx.com` resolves to the Themis host directly**
   (pfSense host override, mirrored in `infrastructure/network/pfsense/config.xml`).
   MQTT push on `:31000` is raw TCP the Ariadne proxy cannot carry, and the
   tablets must keep working when the rack is down.
8. **Not all device state is Headwind's.** Appops and runtime permissions live
   below the MDM layer; the panel neither shows nor restores them, so a factory
   reset loses them with no visible signal. They belong in `bin/sophy-harden`,
   never in a one-off ADB command. Note that permission-backed appops cannot be
   driven through `appops set` — `POST_NOTIFICATION` is slaved to the
   `POST_NOTIFICATIONS` runtime permission and silently ignores the write; use
   `pm grant`/`pm revoke` for those (verified 2026-09-23).

## Spike before you build

`docs/themis-design-doc.md` §12 lists seven verification gates. Gate 1 (one
authenticated call reassigns `configurationId` and pushes it) was answered from
the Headwind source on 2026-09-13 — `PUT /rest/private/devices` with
`{"ids":[id],"configurationId":N}`; `bin/sophy-switch` wraps it. What is still
unmeasured is the push latency on real hardware (Gate 4) and which user
restrictions Headwind actually exposes (Gate 5); record both in §12 as they
are tested.

## Naming

Themis is the service (Titaness of law and settled order — policy distribution,
not surveillance; Argus does the watching). **Sophy** is the kiosk policy
family for the children's tablets, after Sophrosyne — one `School` / `Free
Time` configuration pair per device, named by device number (`sophy-01:
School`). The full name **Sophrosyne** is reserved for a future
content-moderation service and should not be spent here.
