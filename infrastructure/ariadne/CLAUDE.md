# Ariadne

The homelab DMZ and perimeter layer — NGINX Proxy Manager handles SSL termination and subdomain
routing; Authelia provides SSO/OIDC; all external service exposure routes through here.
No internal service is directly internet-accessible.

## Components

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| NGINX Proxy Manager | LXC | 120 | 10.0.60.10 | 80, 443 (public), 81 (admin UI) | 60 | Deployed |
| Authelia | LXC | 121 | 10.0.60.11 | 9091 | 60 | Deployed |
| Umami | LXC | 122 | 10.0.50.18 | 3000 | 50 | Deployed |

**Planned (pfSense packages — no dedicated LXC):**
- WireGuard VPN — pfSense package
- Crowdsec IPS — pfSense package
- Squid forward proxy — pfSense package

## Role in Stack

**Depends on:**
- `network/pfsense` — NAT rules (80/443 → NPM), firewall allows (DMZ → backends)
- `platform/postgres` — Umami analytics database (`umami` DB, user `vault_umami_password`)
- Let's Encrypt — SSL cert automation via NPM certbot

**Depended on by:**
- All externally-accessible services — Jellyfin, Immich, ABS, ntfy, n8n, Umami, etc.
  All external traffic enters through NPM (10.0.60.10)

## IaC Layout

```
infrastructure/ariadne/
  terraform/
    main.tf            ← LXC definitions for NPM, Authelia, Umami
    outputs.tf
    provider.tf
    variables.tf
    locals.tf
    terraform.tfvars   ← gitignored
    .terraform/        ← gitignored (provider binaries ~27MB)
  ansible/
    inventory.ini
    group_vars/
      all.yml
      vault.yml        ← ansible-vault encrypted
    provision.yml      ← master playbook
    roles/
      media_proxy/     ← nginx configs for 8 Orpheus subdomains
      ntfy_proxy/      ← nginx config for ntfy.sirhexx.com
```

## Vault Variables

- `vault_umami_password` — Umami Postgres DB user

## Proxied Services (NPM configs)

| Subdomain | Backend | Notes |
|-----------|---------|-------|
| ntfy.sirhexx.com | iris 10.0.10.25:2586 | ntfy push broker |
| watch.sirhexx.com | TrueNAS 10.0.80.5:8096 | Jellyfin |
| images.sirhexx.com | TrueNAS 10.0.80.5:2283 | Immich |
| audible.sirhexx.com | TrueNAS 10.0.80.5:13378 | Audiobookshelf |
| analytics.sirhexx.com | Umami 10.0.50.18:3000 | Umami analytics |
| automation.hexxusweb.com | n8n 10.0.50.13:5678 | n8n workflows |

Additional media subdomain configs in `roles/media_proxy/` — see Orpheus Design Doc §8 for
full subdomain registry.

## Design Doc

`docs/ariadne-design-doc-v1.0.md` — full DMZ architecture, Authelia OIDC config, WireGuard
VPN plan, Crowdsec + Fail2ban perimeter defense.

## Notes

- Umami (VMID 122) sits on VLAN 50 (Lab Services) despite being Ariadne-managed — it's a
  backend service, not a DMZ-facing host
- pfSense allows Ariadne (10.0.60.10) → specific VLAN 50 backends on their service ports
- SSL: `media_proxy_ssl: false` in `roles/media_proxy/defaults/main.yml` — flip to `true`
  once DNS points 8 media domains at WAN IP, then re-run `--tags media_proxy`
- See root `CLAUDE.md` for IaC conventions (provider version, roles_path, vault naming)
