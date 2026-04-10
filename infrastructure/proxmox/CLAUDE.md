# Proxmox

Post-install Ansible configuration for the puppetmaster Proxmox node — disables enterprise
repos, enables no-subscription repo, fixes Ceph sources, removes subscription nag, disables
HA services, and applies baseline hardening.

## Components

| Name | Type | VMID | IP | VLAN | Status |
|------|------|------|----|------|--------|
| puppetmaster (T150) | Bare metal | — | 10.0.10.2 | 10 | Deployed |

## Role in Stack

**Depends on:**
- Nothing — this is the hypervisor; all LXC/VM services run on it

**Depended on by:**
- Every service in the repo — all LXC containers and VMs run on puppetmaster

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
                          removes sub nag, disables HA services (corosync, pve-ha-*)
```

No Terraform — puppetmaster is bare metal, not a Proxmox resource.

## Key Facts

| Field | Value |
|-------|-------|
| PVE version | 9.1.0 |
| Kernel | 6.17.9-1-pve |
| WAN bridge | vmbr0 (eno8303) — no IP, no VLAN awareness |
| LAN/trunk bridge | vmbr1 (eno8403) — 10.0.10.2/24, VLAN-aware (bridge-vids 2-4094) |
| Storage — ZFS | `general-store` (11.5TB, 4× 3TB SAS RAIDZ1) |
| Storage — LVM thin | `local-lvm` (1.7TB SSD) |
| Storage — dir | `local` (98GB) |
| DNS | 10.0.10.1, 1.1.1.1, 8.8.8.8; search: homelab.internal |

## Vault Variables

- Proxmox users: `root@pam`, `hexxus@pam`, `hexxus@pve`, `ansible_mgr@pam`, `terraform@pve`

## Notes

- `repos.yml` role was added 2026-03-18 to fill gaps vs. the PVE post-install script
- HA services (corosync, pve-ha-lrm, pve-ha-crm) are disabled — this is a single-node setup
- See root `CLAUDE.md` for IaC conventions
