# Iris ansible

Baseline hardening playbooks for the Iris bare metal log collector project
(Helm v2 device; syslog-ng + Vector, Phase 3).

## Device Overview

| Field    | Value                            |
|----------|----------------------------------|
| Hostname | helm-log                         |
| Role     | syslog-ng + Vector log collector |
| Hardware | Helm v2b (HPS20)                 |
| IP       | 10.0.10.25                       |
| MAC      | \<see pfSense DHCP leases\>      |
| VLAN     | 10                               |
| SSH port | 22                               |

## Prerequisites

### 1. Generate SSH key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/homelab_ed25519
```

### 2. Copy key to device

After first boot (default Armbian root password is `1234`):

```bash
ssh-copy-id -i ~/.ssh/homelab_ed25519.pub root@10.0.10.25
```

### 3. Set DHCP reservation in pfSense

Add a static DHCP lease for the device MAC → 10.0.10.25 in the pfSense DHCP
server for VLAN 10.

### 4. Confirm hostname (first boot only)

The playbook sets the hostname idempotently via `hostnamectl`. To confirm
beforehand:

```bash
ssh root@10.0.10.25 hostnamectl set-hostname helm-log
```

## Running the Playbook

### Provision (first-time setup)

```bash
ansible-playbook -i inventory.ini provision.yml
```

Dry-run first:

```bash
ansible-playbook -i inventory.ini provision.yml --check --diff
```

### Update (periodic maintenance)

```bash
ansible-playbook -i inventory.ini update.yml
```

## Phase 3 Additions

The following will be added when the log stack is deployed:

- `roles/syslog_ng/` — syslog-ng service configuration
- `roles/vector/` — Vector log collector and pipeline config
- `roles/wazuh_agent/` — Wazuh agent for SIEM integration
- `group_vars/vault.yml` — Ansible Vault for syslog-ng/Vector secrets

## Troubleshooting

### SSH refuses connections after baseline playbook

If helm-log returns `kex_exchange_identification: read: Connection reset by peer` and port 22 is TCP-reachable (nc succeeds), SSH broke during the baseline run — not a firewall issue.

Use the serial console (USB-C, 115200 baud) to recover. Full diagnostic steps and fixes are in [ssh-fix-runbook.md](./ssh-fix-runbook.md).

---

## Reflashing

If the device needs a fresh Armbian image, use the `flash-helm` script in
`~/projects/helm-conversion/`.

### Physical steps to enter maskrom mode

1. Ensure the Helm is fully booted and connected to power and ethernet.
2. Press and hold the power button for **25 seconds**.
3. Unplug the power cable, press and hold the power button, then re-insert
   the power cable. Keep holding for **6 seconds** after insertion, then
   release.
4. Connect a USB-C cable from one of the two USB-C ports on the right side
   of the ethernet port (viewed from the back) to your Linux host.

### Verify maskrom mode

```bash
lsusb | grep RK3399
# Expected: Fuzhou Rockchip Electronics Company RK3399 in Mask ROM mode
```

### Run the flash script

```bash
cd ~/projects/helm-conversion

# Dry-run first
./flash-helm --variant v2b --dry-run

# Live flash
./flash-helm --variant v2b
```

After flashing, wait ~2 minutes for Armbian to boot, then provision:

```bash
ssh-copy-id -i ~/.ssh/homelab_ed25519.pub root@10.0.10.25
ansible-playbook -i inventory.ini provision.yml
```
