# themis — Android endpoint management (MDM)

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
| IaC | Ansible (`ansible/`); `terraform/` deferred until the rack move |
| Status | **Not deployed.** MVP runs off-rack on the ThinkPad first |

## Current state: off-rack PoC

The Proxmox node is unavailable pending an ISP change and the move to the server
closet. The MVP runs in an **Incus system container on the ThinkPad** — not
Docker, not KVM. A Proxmox LXC is an LXC, so the same Ansible role transfers to
VMID 111 unchanged; Docker would mean writing the role twice, and the laptop has
~2.9 GiB RAM free and no swap, which rules out a comfortable VM.

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
2. **QR provisioning needs a publicly trusted certificate.** The setup wizard
   uses the system trust store and no CA can be installed before it runs, so a
   self-signed cert or private CA fails. Use Let's Encrypt DNS-01 (no inbound
   reachability required). For local iteration, sideload and use
   `adb shell dpm set-device-owner com.hmdm.launcher/.AdminReceiver` instead.
3. **The QR payload needs `PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM`.**
   Provisioning fails silently-ish without it.
4. **Device Owner is not root and is not permanent.** A factory reset from
   recovery removes it. The kiosk profile must also set `DISALLOW_FACTORY_RESET`,
   `DISALLOW_SAFE_BOOT`, and `DISALLOW_DEBUGGING_FEATURES` — verify Headwind
   exposes them and record whatever it does not as accepted risk.
5. **Device Owner never goes on an adult's daily driver.** Work Profile is the
   correct mode for peers, and it must stay self-removable.
6. **Nothing identifying goes in this repo.** It is public. Device serials, the
   enrollment payload, and child-identifying detail live in the Headwind
   database, not in git.

## Spike before you build

`docs/themis-design-doc.md` §12 lists seven verification gates. **Gate 1 blocks
everything else:** confirm the Headwind REST API can reassign a device's
`configurationId` in a single authenticated call. Every workflow in the design —
the NFC macro, the cron lock, the whole control plane — assumes it can. Spike it
against a throwaway device before writing a line of automation.

## Naming

Themis is the service (Titaness of law and settled order — policy distribution,
not surveillance; Argus does the watching). **Sophy** is the kiosk policy group
for the child's tablet, after Sophrosyne. The full name **Sophrosyne** is
reserved for a future content-moderation service and should not be spent here.
