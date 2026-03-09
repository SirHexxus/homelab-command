# pfSense Ansible IaC

Ansible automation for pfSense CE 2.8.1 using the `pfsensible.core` collection.
Manages VLANs, interface assignments, and firewall rules.

## Prerequisites

### One-time manual setup on pfSense

SSH into pfSense and run:

```sh
pkg install python311
ln -s /usr/local/bin/python3.11 /usr/local/bin/python3
```

This is required because `pfsensible.core` needs Python on the target to execute
pfSense PHP commands. This step cannot be automated since Ansible itself needs Python
to bootstrap the connection.

### Control machine setup

```sh
# Install the pfsensible.core collection
ansible-galaxy collection install -r requirements.yml

# Create and encrypt the vault file
cp group_vars/vault.yml.example group_vars/vault.yml
ansible-vault encrypt group_vars/vault.yml
# Edit with: ansible-vault edit group_vars/vault.yml
```

## Usage

### PoC — VLAN 60 (DMZ) only

```sh
# Dry-run first
ansible-playbook -i inventory.ini provision.yml --ask-vault-pass --check --tags dmz

# Apply
ansible-playbook -i inventory.ini provision.yml --ask-vault-pass --tags dmz
```

### Full run — all non-existing VLANs

```sh
ansible-playbook -i inventory.ini provision.yml --ask-vault-pass
```

### Verify current state

```sh
ansible-playbook -i inventory.ini verify.yml
```

## VLAN Table

| ID | Name         | Gateway    | Managed |
|----|--------------|------------|---------|
| 10 | MANAGEMENT   | 10.0.10.1  | no (pre-existing) |
| 20 | PERSONAL     | 10.0.20.1  | no (pre-existing) |
| 30 | WORK         | 10.0.30.1  | no (pre-existing) |
| 40 | IOT          | 10.0.40.1  | no (pre-existing) |
| 50 | LAB_SERVICES | 10.0.50.1  | no (pre-existing) |
| 60 | DMZ          | 10.0.60.1  | **yes** |
| 66 | SANDBOX      | 10.0.66.1  | **yes** |
| 70 | GUEST        | 10.0.70.1  | **yes** |

## Post-apply steps for VLAN 60

1. Run the PoC provision: `--tags dmz`
2. In pfSense UI: **Interfaces > Assignments** — find the interface assigned to `vtnet1.60`
   and note its name (e.g. `OPT5`)
3. Update `pfsense_dmz_interface` in `group_vars/pfsense.yml` to match
4. Re-run with `--tags firewall` to apply DMZ firewall rules
5. Run `verify.yml` — all assertions should pass
6. Flip `existing: false` → `existing: true` for VLAN 60 in `group_vars/pfsense.yml`

## DMZ Firewall Policy

Rules applied in order:

1. **Block** DMZ → MANAGEMENT (10.0.10.0/24)
2. **Block** DMZ → PERSONAL (10.0.20.0/24)
3. **Block** DMZ → WORK (10.0.30.0/24)
4. **Block** DMZ → IOT (10.0.40.0/24)
5. **Block** DMZ → LAB_SERVICES (10.0.50.0/24)
6. **Allow** DMZ → pfSense DNS resolver (10.0.60.1:53)
7. **Allow** DMZ → any (internet outbound)

## Manual verification after VLAN 60 is live

From a host assigned to VLAN 60:

```sh
ping 10.0.20.1           # must FAIL (blocked by rule 2)
curl https://example.com # must SUCCEED (rule 7)
dig @10.0.60.1 example.com  # must SUCCEED (rule 6)
```
