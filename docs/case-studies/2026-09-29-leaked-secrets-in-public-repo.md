# Case Study: Secrets Committed to a Public IaC Repository

Blameless post-incident review of credentials found in this repository's public history on 2026-09-29: how they got there, how they were found, how they were contained, and what changed so it cannot happen the same way again. No secret values appear in this document.

---

## Table of Contents

1. [Summary](#summary)
2. [Impact](#impact)
3. [Timeline](#timeline)
4. [Detection](#detection)
5. [Response](#response)
6. [Root Causes](#root-causes)
7. [What Went Well](#what-went-well)
8. [What Went Poorly](#what-went-poorly)
9. [Corrective Actions](#corrective-actions)
10. [Lessons](#lessons)

---

## Summary

| Field | Value |
|-------|-------|
| Severity | High: live credentials in a public repository for roughly seven months |
| Exposure window | 2026-03-04 → 2026-09-29 |
| Detected | 2026-09-29, during a planned audit of system interfaces |
| Contained | 2026-09-29 (same day): every exposed credential rotated or confirmed stale, each verified against the live system; history rewritten |
| Evidence of abuse | None found |
| Collateral | ~20-minute analytics (Umami) outage caused by the response itself |

Three kinds of file carried secrets into the public history of `SirHexxus/homelab-command`:

- **Plaintext Ansible Vault files.** The repo convention is "encrypt `group_vars/vault.yml` with `ansible-vault`; never commit it." Two files were committed unencrypted on 2026-03-04 and deleted the same day. A third, for the DMZ stack, was committed unencrypted on 2026-03-09 and stayed tracked until the incident.
- **A raw pfSense `config.xml` export**, committed on 2026-03-10 as the firewall's "source of truth." A pfSense export contains credentials by design.
- **Deletion is not removal.** The two files deleted on 2026-03-04 were still retrievable from git history for the entire window.

---

## Impact

| Exposed item | Where | What an attacker could do | Outcome |
|--------------|-------|---------------------------|---------|
| Namecheap Dynamic DNS password (`*.sirhexx.com`) | `config.xml` | Repoint every subdomain; obtain valid TLS certs for them | Rotated; old password confirmed rejected by Namecheap |
| Firewall admin bcrypt hash | `config.xml` | Offline cracking of the firewall admin password | Password changed; live hash confirmed different |
| Firewall web GUI TLS private key | `config.xml` | Impersonate the admin UI on the LAN | Reissued with a new key pair; served public key confirmed different |
| SNMP community, Netgate device key | `config.xml` | Low: LAN-only / identifier | Redacted from history |
| Authelia JWT, session, and storage-encryption secrets | DMZ vault | Forge SSO sessions (Authelia was deployed but not yet protecting anything) | Rotated; store reset |
| Umami database password and app secret | DMZ vault | Read/write analytics data; forge Umami sessions | Rotated |
| n8n database password | 2026-03-04 vaults | Read/modify workflow state and stored credentials (VLAN 50 only) | Rotated; n8n readiness confirmed on the new password |
| Mnemosyne database password | 2026-03-04 vaults | Read/modify the knowledge-base event log (VLAN 50 only) | Already changed after March; confirmed stale |
| Argus database password | 2026-03-04 vaults | None: Argus not yet built | Rotated |

**Exploitability.** The DNS credential was the only one reachable from the internet with no other foothold. The database credentials require network access to VLAN 50, which is not exposed. The wildcard DNS record still pointed at the home WAN address when the incident was found, and no unfamiliar DNS records were present.

---

## Timeline

All dates 2026. Times are Pacific.

| When | Event |
|------|-------|
| Feb 20 | Repository created; public for the whole exposure window as far as GitHub's event history shows |
| Mar 4 | n8n and Postgres `vault.yml` committed in plaintext; deleted in the next commit the same day |
| Mar 9 | DMZ (Ariadne) `vault.yml` committed in plaintext, with the comment "encrypt before committing" |
| Mar 10 | Raw pfSense `config.xml` committed as a config backup |
| Apr 27 | `vault.yml` added to `.gitignore`; the Hermes vault is untracked, but the Ariadne vault stays tracked, because `.gitignore` never applies to files git already tracks |
| Sep 29, afternoon | System-interface audit finds the tracked plaintext DMZ vault; checks the repo is public |
| Sep 29 | Secret-shaped elements counted in `config.xml`; the Dynamic DNS password is identified as the highest risk |
| Sep 29 | DMZ secrets rotated by script; Umami breaks during redeploy, recovered by rollback (~20 min) |
| Sep 29 | History search finds the two March 4 plaintext vaults; the rewrite is widened to cover them |
| Sep 29, ~17:18 | History rewritten (341 commits) and force-pushed after dry run and independent verification |
| Sep 29 | GitHub Support asked to purge cached views of the dereferenced commits |
| Sep 29, evening | Dynamic DNS password, firewall GUI key, and admin password rotated; each verified dead |
| Sep 29, night | Database credentials checked by hash: Mnemosyne already rotated; n8n and Argus rotated and verified |

---

## Detection

The leak was found by a deliberate audit, not by an alert. The audit was building a **generated host inventory** (`infrastructure/mnemosyne/scripts/build-homelab-map`) that reconciles Terraform state, Ansible inventories, the live hypervisor, and the firewall config. Documenting "where each secret lives" for that inventory meant checking each service's vault file. One began with a YAML comment instead of the `$ANSIBLE_VAULT` header.

Existing controls did not catch it:

- **GitHub secret scanning and push protection were enabled**, but they match known *provider* token formats. Generic passwords, bcrypt hashes, and a base64-wrapped PEM key match none of them. Scanning for non-provider patterns was off.
- **No pre-commit or CI secret scanning** ran on this repository.
- **`.gitignore` gave false assurance.** It listed `vault.yml`, but git still tracks and publishes a file that was committed before the ignore rule existed.

---

## Response

**Principles held throughout:** never print a secret (compare hashes, lengths, and header bytes instead); verify every rotation against the live system; keep destructive git operations out of the working checkout; and give the owner a dry run before anything irreversible.

1. **Scope before action.** The committed `config.xml` was counted for secret-shaped elements by tag name only, which surfaced the Dynamic DNS password. Every historical `vault.yml` was checked by reading only its first 14 bytes (encrypted files begin with `$ANSIBLE_VAULT`). That surfaced the two March 4 files.
2. **Rotate the DMZ secrets.** A script generated five new random values, encrypted the vault, reset the database role, and redeployed Authelia and Umami. Authelia was not yet protecting anything, so its encrypted store was reset rather than migrated.
3. **Stop publishing.** The plaintext vault and the raw `config.xml` were untracked. A new `sanitize-config` script now produces a redacted `config.xml.example`. It works on raw text so the redacted copy diffs cleanly (exactly 5 of 1,803 lines differ), and it refuses to write output that still contains a secret. The real export is gitignored and backed up outside git.
4. **Rewrite history.** `git-filter-repo` ran in a throwaway clone, so uncommitted work in the real checkout was never at risk. It removed the three vault files and redacted every past `config.xml`. Before any push, the script verified: no vault paths anywhere in history, no unredacted secret elements, and the final tree **byte-identical** to the pre-rewrite HEAD. An independent check then searched the rewritten history for each of the 14 leaked values taken from the old history: 13 had zero hits. The 14th was a 6-character SNMP community string that also appears elsewhere as an ordinary word, and its secret element was redacted. A full backup bundle was kept until verification finished, then deleted.
5. **Rotate the firewall and DNS secrets, then prove each one is dead.**
   - *Dynamic DNS:* sent a no-op update to Namecheap using the old password; it answered "Passwords do not match."
   - *GUI certificate:* reissued without reusing the key. The public key the firewall now serves differs from the one derived from the leaked private key.
   - *Admin password:* the live bcrypt hash differs from the leaked one (and was confirmed to be a real 60-character hash, not an empty read).
6. **Triage the database credentials by hash.** One-way hashes of the three leaked values were saved before the history copies were destroyed. The Mnemosyne password in use today authenticates and differs from the leaked hash, so it was already rotated. The n8n and Argus roles were rotated by a script that also synced every other role's live password into the Postgres vault, so a later provisioning run cannot quietly reset one. n8n came back and passed its database-backed readiness check on the new password, and the Mnemosyne and Umami roles were confirmed still working.
7. **Purge caches.** GitHub keeps dereferenced commits reachable by SHA until its own garbage collection runs. A purge request was filed with the affected commit URLs, confirming zero forks and zero pull requests.

---

## Root Causes

1. **A manual safeguard with no enforcement.** "Encrypt before committing" was a comment inside the very file it protected. Nothing blocked a plaintext `vault.yml` from being committed.
2. **A raw appliance export used as IaC.** Treating `config.xml` as source of truth is reasonable. Committing it unsanitized is not: pfSense exports embed credentials by design.
3. **Ignore rules applied after the fact.** The April `.gitignore` change untracked one vault (already encrypted) and missed the plaintext one. `.gitignore` cannot untrack files, so the rule looked protective while doing nothing for the file that mattered.
4. **"Deleted" treated as "gone."** The March 4 files were removed from HEAD within minutes but stayed in history for seven months.

**Contributing factors.**
- Scanning covered provider tokens only.
- The playbooks could create database roles but not rotate them: the password tasks only ran on first creation.
- A web-app role tracked its upstream `master` branch without rebuilding. That turned a password redeploy into an outage.

---

## What Went Well

- A systematic audit found the problem; the leak was never found by an attacker first.
- No secret value was printed, logged, or pasted at any point in the response. Every check used hashes, lengths, header bytes, or element counts.
- Every rotation was verified against the live system, not assumed.
- The history rewrite had a dry run, a pre-push verification gate, an independent value search, and a backup. It completed with the working tree and all uncommitted changes intact.
- Findings were turned into tracked tasks as they came up, not left in a chat log.

## What Went Poorly

- **The response caused an outage.** Re-running the full provisioning playbook to deploy new Umami secrets also ran `apt upgrade`, a dotfiles pull, and a `git reset` to upstream `master` with no rebuild. Umami crash-looped (about 96 restarts) until it was rolled back about 20 minutes later. Playbooks that do more than their name suggests are a hazard during incident response.
- **An early status statement was inaccurate.** A draft support request said "all credentials rotated" before that was true. It was corrected before submission.
- **The exposure lasted seven months** because nothing checked for it.

---

## Corrective Actions

| Action | Status |
|--------|--------|
| Rotate all live exposed credentials and verify each is dead | Done |
| Untrack plaintext vault and raw `config.xml`; add `vault.yml.example` and redacted `config.xml.example` | Done |
| `sanitize-config`: redacted export with a built-in secret check | Done |
| Rewrite and force-push history; refresh all known clones | Done |
| Make role-password tasks rotation-capable (`ALTER ROLE` on every run, `no_log`, `--tags db_users`) | Done |
| Generated host inventory with drift detection (`build-homelab-map`) | Done |
| GitHub purge of cached commit views | Requested |
| Pre-commit secret scanning (e.g. gitleaks) plus a CI job, including a check that every `vault.yml` begins with `$ANSIBLE_VAULT` | Open |
| Enable GitHub secret scanning for non-provider patterns | Open |
| Pin the Umami version and rebuild on change; gate `apt upgrade` behind a tag | Open |
| Read-only, least-privilege pfSense export that runs the sanitizer | Open |
| Remove duplicated secrets (the same DB password is held in up to three places) | Open |

---

## Lessons

- **Controls that depend on memory fail silently.** Put the rule in a hook, not in a comment.
- **`.gitignore` protects the future, never the past.** Pair every ignore rule with `git rm --cached` and a check that nothing matching the rule is still tracked.
- **History is part of the repository.** Deleting a secret in the next commit publishes it for as long as the history exists. Rotation is the only real fix; rewriting history only limits who can find it later.
- **Verify the negative.** "I changed the password" becomes a fact only when the old one is shown to fail.
- **Know what your playbooks do before running them in an incident.** A narrowly scoped, tagged task is worth more during response than an idempotent everything-playbook.
