# helm-log SSH Fix Runbook

Operational runbook for recovering SSH access to helm-log (10.0.10.25) via serial console,
then completing the Ansible provision run (dotfiles + ntfy).

---

## 1. Connect via Serial Console

Find the serial device (USB-C cable to helm-log):

```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

Connect at 115200 baud:

```bash
screen /dev/ttyUSB0 115200
# alternative: minicom -D /dev/ttyUSB0 -b 115200
```

Login as `root`.

---

## 2. Diagnose SSH

Run these in order — stop at the first positive finding:

```bash
# Is sshd running?
systemctl status sshd

# Config syntax check
sshd -t

# Is sshd listening on port 22?
ss -tlnp | grep :22

# Recent sshd log output
journalctl -u sshd -n 50

# TCP wrappers
cat /etc/hosts.deny
cat /etc/hosts.allow
```

---

## 3. Fix

Apply the fix that matches your finding:

### Config syntax error (`sshd -t` fails)

The baseline role sets `PasswordAuthentication no` and `PermitRootLogin prohibit-password`
via `lineinfile`. If a duplicate entry was introduced, `sshd -t` will catch it.

```bash
# Show what sshd sees
sshd -T 2>&1 | head -20

# Edit sshd_config — remove any duplicate directives
nano /etc/ssh/sshd_config

# Verify then restart
sshd -t && systemctl restart sshd
```

### sshd not running (failed/dead)

```bash
systemctl start sshd
systemctl status sshd
```

### TCP wrappers blocking (`/etc/hosts.deny` has `ALL:ALL` or `sshd:ALL`)

```bash
# Allowlist SSH and reload
echo "sshd: ALL" >> /etc/hosts.allow
# or: remove the blocking line from /etc/hosts.deny with nano
```

### sshd running and config clean but still rejecting

```bash
# Check for address or user restrictions
grep -i "listenaddress\|addressfamily\|allowusers\|allowgroups" \
    /etc/ssh/sshd_config

# Test from within the host
ssh -v root@localhost
```

---

## 4. Verify SSH from Your Workstation

Once fixed, confirm before starting Ansible:

```bash
ssh -i ~/.ssh/homelab_ed25519 root@10.0.10.25
```

> [!IMPORTANT]
> Do not proceed to Step 5 until SSH is confirmed working from your workstation.

---

## 5. Run Ansible Provision

```bash
cd infrastructure/iris/ansible/
ansible-playbook -i inventory.ini provision.yml
```

Dry-run first if you want to preview changes:

```bash
ansible-playbook -i inventory.ini provision.yml --check --diff
```

### Expected outcome

| Role | What happens |
|------|--------------|
| `baseline` | Idempotent re-run — no changes expected |
| `dotfiles` | Bare git repo deployed to `/root`, login-hook installed |
| `ntfy` | ntfy 2.17.0 installed, service enabled, listening on port 2586 |

---

## 6. Verify ntfy

```bash
# Health check
curl http://10.0.10.25:2586/v1/health
# Expected: {"healthy":true}

# Send a test notification
curl -d "helm-log provisioning complete" \
    http://10.0.10.25:2586/provisioning
```

---

## Key Files

| File | Purpose |
|------|---------|
| `provision.yml` | Main playbook (baseline → dotfiles → ntfy) |
| `inventory.ini` | Host: helm-log at 10.0.10.25, key: `~/.ssh/homelab_ed25519` |
| `group_vars/iris.yml` | ntfy_version, port, topics |
| `roles/baseline/tasks/main.yml` | SSH hardening tasks |
| `roles/ntfy/tasks/main.yml` | ntfy install + service |
