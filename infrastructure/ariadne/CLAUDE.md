# Ariadne

**Claude's role in this directory: System Administrator.**
Ariadne is the single entry point for all external traffic — changes here affect every
externally-accessible service. The work here is maintenance and targeted updates. New proxy
configs, Authelia policy changes, and SSL flips require confirmation before proceeding.

## Current State

| Name | Type | VMID | IP | Port(s) | VLAN | Status |
|------|------|------|----|---------|------|--------|
| NGINX Proxy Manager | LXC | 120 | 10.0.60.10 | 80, 443 (public), 81 (admin UI) | 60 | Deployed |
| Authelia | LXC | 121 | 10.0.60.11 | 9091 | 60 | Deployed |
| Umami | LXC | 122 | 10.0.50.18 | 3000 | 50 | Deployed |

**Pending maintenance task:** SSL is not yet enabled for media proxy configs.
When DNS for the 8 media subdomains points at the WAN IP, flip `media_proxy_ssl: true` in
`roles/media_proxy/defaults/main.yml` and re-run with `--tags media_proxy`.

## Role in Stack

**Depends on:**
- `network/pfsense` — NAT rules (80/443 → NPM), firewall allows (DMZ → backends)
- `platform/postgres` — Umami analytics database (`umami` DB)
- Let's Encrypt — SSL cert automation via NPM certbot

**Depended on by:**
- All externally-accessible services — all external traffic enters through NPM (10.0.60.10)

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
      vault.yml
    provision.yml
    roles/
      media_proxy/     ← nginx configs for 8 Orpheus subdomains
      ntfy_proxy/      ← nginx config for ntfy.sirhexx.com
```

## Vault Variables

- `vault_umami_password` — Umami Postgres DB user

## Proxied Services

| Subdomain | Backend | Notes |
|-----------|---------|-------|
| ntfy.sirhexx.com | iris 10.0.10.25:2586 | ntfy push broker |
| watch.sirhexx.com | TrueNAS 10.0.80.5:8096 | Jellyfin |
| images.sirhexx.com | TrueNAS 10.0.80.5:2283 | Immich |
| audible.sirhexx.com | TrueNAS 10.0.80.5:13378 | Audiobookshelf |
| analytics.sirhexx.com | Umami 10.0.50.18:3000 | Umami analytics |
| automation.hexxusweb.com | n8n 10.0.50.13:5678 | n8n workflows |

Additional media subdomain configs in `roles/media_proxy/` — see `docs/orpheus-design-doc-v1.1.md` §8.

## Hard Constraints

- Umami (VMID 122) is on VLAN 50 — not a DMZ host
- pfSense allows Ariadne (10.0.60.10) → specific VLAN 50 backends on their service ports only
- Do not remove or alter NPM proxy configs without checking dependent service status

## Escalation Criteria

Stop and confirm if the work involves any of the following:

- Adding or removing proxy hosts
- Authelia policy or OIDC configuration changes
- SSL certificate changes beyond routine certbot renewal
- Firewall rule changes in `network/pfsense`

## Reference

IaC conventions: see root `CLAUDE.md`. Design doc: `docs/ariadne-design-doc-v1.0.md`
