# recon — quarantined WordPress recon / detonation box

A single-purpose, throwaway VM for **safely reviewing a CLONE of a compromised
website**. First use: Smith Scale (a client site hacked twice; see the
sales-pipeline project). It runs the site's own code, so it is deliberately
isolated.

| Field | Value |
|-------|-------|
| VMID | 6601 (encodes "VLAN 66, not a normal VM") |
| IP | 10.0.66.10 (VLAN 66 — Sandbox/quarantine) |
| OS | Debian 12 (genericcloud), cloud-init |
| Specs | 4 vCPU / 6 GB / 40 GB |
| On boot | **disabled** — start manually only when in use |
| IaC | Terraform (`terraform/`) + Ansible (`ansible/`) |

## Why a VM, not an LXC (repo convention exception)

This repo prefers unprivileged LXC. Recon is an explicit exception: the workload
is **known-hostile code**, so it gets a full VM — separate kernel and a
hardware-virtualization boundary — rather than a shared-kernel container. Paired
with VLAN 66 isolation and a pre-detonation snapshot, that's the right posture
for detonating a compromised site.

## Isolation model

- **VLAN 66 (Sandbox)** blocks all outbound and (by default-deny) all inbound.
- **Inbound exception:** only the wired VLAN 10 workstation (10.0.10.68) may
  reach the box, SSH only. Implemented in the pfSense firewall role
  (`network/pfsense/.../tasks/recon.yml`) as a MANAGEMENT-interface pass rule
  placed above the `MANAGEMENT_DENIED` block.
- **Outbound:** none, except a **gated provisioning window**
  (`recon_provisioning_egress`) that temporarily allows web + DNS so the box can
  install its toolchain. It must be **closed before any site clone is imported.**

## Order of operations (do not skip)

1. `terraform apply` (creates the VM; it does not auto-start on node reboot).
2. Open the egress window — from `network/pfsense/ansible`:
   `ansible-playbook -i inventory.ini provision.yml -e recon_provisioning_egress=true --tags recon --ask-vault-pass`
3. Provision the toolchain — from `recon/ansible`:
   `ansible-playbook -i inventory.ini provision.yml --ask-vault-pass`
4. **Close** the egress window (`recon_provisioning_egress=false`, re-apply the
   `recon` tag) and **snapshot** the VM in Proxmox ("clean-provisioned").
5. Only now import the site clone into `/srv/recon` and begin analysis.
6. When done: revert to the snapshot or destroy the VM.

## Toolchain (installed by the `recon_box` role)

WP-CLI, WPScan (add a token via `vault_recon_wpscan_api_token` for CVE data),
maldet, ClamAV + YARA, ripgrep/whois/dnsutils, a Playwright venv
(`/opt/recon-venv`) with headless Chromium, whatweb, and a LAMP-ish stack
(nginx + MariaDB + PHP-FPM) to serve the clone for browser recon. Reporting via
pandoc/wkhtmltopdf.
