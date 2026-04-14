# Proxmox

**Claude's role in this directory: System Administrator.**
This is the hypervisor — every LXC and VM in the stack runs here. Changes to puppetmaster
affect the entire homelab. Treat all work here as high-consequence. If any task involves
bridge configuration, storage pool changes, or PVE version upgrades, stop and confirm.

## Current State

| Field | Value |
|-------|-------|
| Host | puppetmaster (T150) — bare metal |
| IP | 10.0.10.2/24, VLAN 10 |
| PVE version | 9.1.0 (kernel 6.17.9-1-pve) |
| WAN bridge | vmbr0 (eno8303) — no IP, no VLAN awareness |
| LAN/trunk bridge | vmbr1 (eno8403) — 10.0.10.2/24, VLAN-aware (bridge-vids 2-4094) |
| Storage — ZFS | `general-store` (11.5TB, 4× 3TB SAS RAIDZ1) |
| Storage — LVM thin | `local-lvm` (1.7TB SSD) |
| Storage — dir | `local` (98GB) |
| DNS | 10.0.10.1, 1.1.1.1, 8.8.8.8; search: homelab.internal |

Ansible-managed post-install configuration only. No Terraform — puppetmaster is bare metal.

## Role in Stack

**Depends on:** Nothing — this is the hypervisor

**Depended on by:** Every service in the repo

## IaC Layout

```
infrastructure/proxmox/
  ansible/
    inventory.ini
    ansible.cfg        ← roles_path: roles:../../ansible/roles
    group_vars/
      all.yml
      vault.yml
    provision.yml
    roles/
      proxmox_base/
        tasks/
          main.yml
          repos.yml    ← disables enterprise repo, enables no-subscription, Ceph fix,
                          removes subscription nag, disables HA services
```

## Vault Variables

- Proxmox users: `root@pam`, `hexxus@pam`, `hexxus@pve`, `ansible_mgr@pam`, `terraform@pve`

## Hard Constraints

- HA services (corosync, pve-ha-lrm, pve-ha-crm) remain disabled — single-node setup
- Do not alter vmbr0 or vmbr1 bridge configuration without explicit direction — all VLAN
  routing depends on vmbr1
- Do not modify storage pool definitions without explicit direction

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- PVE version upgrades
- Bridge or network interface configuration
- Storage pool additions, removals, or reconfiguration
- User or permission changes on the PVE node
- Kernel parameters or host-level system configuration

## Reference

IaC conventions: see root `CLAUDE.md`.
See `docs/homelab-philosophy-v1.0.md` for the values and principles behind all homelab decisions.
