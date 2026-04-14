# Network

IaC for the two physical network devices: pfSense (router/firewall VM) and the TP-Link managed
switch. All VLAN definitions, firewall rules, and port assignments live here.

## Components

| Name | Type | VMID | IP | VLAN | Status |
|------|------|------|----|------|--------|
| pfSense CE | VM | 200 | 10.0.10.1 | 10 | Deployed |
| TP-Link T1600G-28PS | Hardware switch | — | 10.0.10.50 | 10 | Deployed |

## Role in Stack

**Depends on:**
- Nothing — foundational layer; everything else depends on it

**Depended on by:**
- Every service in the repo — VLAN routing, firewall rules, and DHCP are prerequisites
  for all LXC/VM deployments

## IaC Layout

```
infrastructure/network/
  pfsense/
    terraform/         ← pfSense VM definition (Proxmox resource)
    ansible/
      roles/
        pfsense_firewall/
          tasks/
            vlan_10.yml, vlan_20.yml ... vlan_80.yml
            media.yml  ← VLAN 80 rules
      ansible.cfg      ← roles_path: roles:../../../ansible/roles
  switch/
    ansible/
      roles/
        tplink_switch/
      ansible.cfg      ← roles_path: roles:../../../ansible/roles
```

## Key Facts

- pfSense is a **VM on the puppetmaster Proxmox node** (VMID 200) — not bare metal
  - pfSense sees: `vtnet0` (WAN, attached to Proxmox bridge vmbr0/eno8303)
  - pfSense sees: `vtnet1` (LAN/trunk, attached to Proxmox bridge vmbr1/eno8403, VLAN-aware)
- pfSense VMID is **200** — never reassign this VMID
- pfSense uses `~/.ssh/homelab_ed25519` (not the default `id_rsa`)
- Switch uses `~/.ssh/homelab_ed25519`
- All VLANs (10/20/30/40/50/60/66/70/80) are trunked on vmbr1
- `vault_switch_password` — switch admin credential

## Firewall Summary

Key cross-VLAN allows (non-obvious rules):
- DMZ (VLAN 60) → ntfy :2586 on iris (10.0.10.25) — Ariadne proxy needs this
- DMZ (VLAN 60) → n8n :5678 on VLAN 50 — Ariadne proxy for automation.hexxusweb.com
- DMZ (VLAN 60) → all VLAN 80 media service ports — Ariadne proxy for media subdomains
- Management (VLAN 10) → all VLANs — full admin access

See `docs/network-services-architecture-v1.6.md` §4 for complete firewall rules.

## Notes

- `roles_path` for network services is 3-level: `roles:../../../ansible/roles`
- See root `CLAUDE.md` for full VLAN topology and IaC conventions
- See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.
