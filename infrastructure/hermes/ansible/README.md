# Hermes Ansible

Ansible playbooks for provisioning and maintaining the Hermes AI agent LXC container.

---

## Prerequisites

- Terraform has already created the LXC container (VMID 110, IP 10.0.50.17)
- SSH access to the container as root
- Ansible 2.10+ installed on the control machine
- Ansible Vault password available

---

## Quick Start

```bash
# 1. Copy and update the inventory
cp inventory.ini.example inventory.ini

# 2. Copy and fill in vault secrets
cp group_vars/vault.yml.example group_vars/vault.yml
ansible-vault encrypt group_vars/vault.yml

# 3. Provision
ansible-playbook -i inventory.ini provision.yml --ask-vault-pass

# 4. Update (pull latest code + restart)
ansible-playbook -i inventory.ini update.yml --ask-vault-pass
```

---

## Playbooks

| Playbook | Purpose |
|----------|---------|
| `provision.yml` | Full initial provisioning from a blank LXC |
| `update.yml` | Pull latest code, update deps, restart service |

---

## Vault Variables

| Variable | Description |
|----------|-------------|
| `gemini_api_key` | Google Gemini API key (Phase 2) |
| `telegram_token_personal` | Telegram bot token — personal context (Phase 3) |
| `telegram_token_professional` | Telegram bot token — professional context (Phase 3) |
| `purelymail_personal_password` | PurelyMail password — personal account |
| `purelymail_professional_password` | PurelyMail password — professional account |
| `second_brain_db_password` | Postgres password for Second Brain DB at 10.0.50.14 |
