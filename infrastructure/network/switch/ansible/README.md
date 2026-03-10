# TP-Link T1600G-28PS — Ansible IaC

Ansible playbook to provision VLANs and port configuration on the TP-Link
T1600G-28PS managed switch at `10.0.10.50`.

---

## SSH Host Key Issue (Read Before Running)

### The problem

The switch ships with a firmware-generated DSA host key that has a non-standard
p bit length. Both OpenSSH 10.x (the system SSH client) and paramiko 4.x reject
this key outright — OpenSSH refuses to negotiate the key exchange, and paramiko
raises an OpenSSL validation error during DSA key parsing.

Paramiko 3.5 also rejects the key due to the same underlying OpenSSL validation.

### The workaround

A proper RSA host key was imported via the switch web UI
(Security → SSH → Host Key). A switch reboot is required to activate the new
key. After rebooting:

1. Confirm the RSA key is active: `ssh -o HostKeyAlgorithms=ssh-rsa admin@10.0.10.50`
2. If the connection is accepted, the RSA key is live and Ansible should work.

### Why paramiko

The `ansible.netcommon.network_cli` connection plugin supports two SSH backends:
the system `ssh` binary and paramiko. Because the system SSH binary (OpenSSH 10.x)
rejects the switch's key at the transport layer before any key type negotiation,
the playbook uses paramiko via `ansible_connection: ansible.netcommon.network_cli`
with the legacy SSH algorithm flags passed through `ansible_ssh_common_args`.

If the RSA key import + reboot fix has been applied and the connection still
fails, confirm the installed paramiko version:

```bash
python3 -c "import paramiko; print(paramiko.__version__)"
```

If paramiko 4.x is installed, downgrade to 3.x:

```bash
pip install 'paramiko<4'
```

---

## Prerequisites

### 1. Install Ansible collections

```bash
ansible-galaxy collection install -r requirements.yml
```

### 2. Create the vault

```bash
cp group_vars/vault.yml.example group_vars/vault.yml
ansible-vault encrypt group_vars/vault.yml
# Then edit with the real password:
ansible-vault edit group_vars/vault.yml
```

Set `vault_switch_password` to the switch admin password.

---

## Usage

```bash
# Full provisioning run (VLANs + ports + save)
ansible-playbook provision.yml --ask-vault-pass

# VLANs only
ansible-playbook provision.yml --ask-vault-pass --tags vlans

# Trunk port only
ansible-playbook provision.yml --ask-vault-pass --tags trunk

# Access ports only
ansible-playbook provision.yml --ask-vault-pass --tags access_ports

# Dry-run (no changes applied)
ansible-playbook provision.yml --ask-vault-pass --check
```

---

## What this playbook configures

| Object | State after provisioning |
|--------|--------------------------|
| VLANs 10, 20, 30, 40, 50, 60, 66, 70 | Created with correct names |
| Port 1/0/1 (trunk → pfSense) | General mode; all 8 VLANs tagged |
| Port 1/0/21 | Access; PVID 20 (PERSONAL) |
| Port 1/0/22 | Access; PVID 30 (WORK) |
| Ports 1/0/2–20, 1/0/23–28 | Untouched |
| Startup config | Updated (copy running-config startup-config) |

VLAN 1 (System-VLAN, switch management) is never modified. The trunk task
adds tagged VLANs additively — it does not replace or remove existing entries.

---

## Adding ports or VLANs

All configuration is data-driven through `group_vars/switch.yml`. To add a
new VLAN, append an entry to `switch_vlans`. To configure a new access port,
append an entry to `switch_access_ports`. No role task files need editing.
