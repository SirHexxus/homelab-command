# Repository Consistency Audit — 2026-06-11

Three-way audit of homelab-command: documentation ↔ IaC code ↔ PKM (Mnemosyne wiki), plus
read-only live infrastructure verification. Deliverable is this ticket list — no fixes were
applied during the audit.

**Ticket owners:**

- `sprint-session` — doc edits, IaC fixes, and migrations for James + Claude Code sprints
- `hermes-functional-test` — live-state checks suitable for handing to Hermes-Agent (Chiron) as
  recurring functionality tests
- `needs-james` — a human decision is required before anyone can fix it

---

## Summary

| Severity | Count | Themes |
|----------|-------|--------|
| High | 7 | Allocation tables wrong vs. live state; Hermes docs describe a superseded system; broken Terraform; broken proxmox inventory |
| Medium | 12 | Provider-pin drift, undocumented vault vars, stale roadmap/arch doc, version-label chaos, passed gate date |
| Low | 6 | Latent config bugs, dead code, housekeeping decisions |

Overall: VMID/IP facts for the *original* services agree everywhere, and all deployed services
are live and healthy. The drift concentrates in three areas: (1) anything that changed after
mid-May 2026 (inbox-receiver, Chiron pivot, Daily Digest swap) never made it back into the
docs; (2) `.claude/agents/homelab-iac-specialist.md` has never been re-synced and is now the
single most wrong file in the repo; (3) doc version labels (filename vs. internal header vs.
index) have diverged systemically.

### Live verification snapshot (all read-only, 2026-06-11)

- `pct list` / `qm list` on puppetmaster: 11 LXCs + 3 VMs running, including **VMID 103
  (inbox-receiver)** which the docs call available
- `pveversion`: **9.1.5** (docs claim 9.1.0 and 9.1.2)
- Health endpoints all 200: Hermes-Agent webhook :8644, ntfy :2586, n8n :5678, MinIO :9000,
  Umami :3000, Ollama :11434, Whisper :9000; Ariadne nginx 301 (normal). Old Hermes gunicorn
  :8765 is **dead** (connection refused) — Chiron/Hermes-Agent is what runs on LXC 110
- `ansible -m ping`: all inventories SUCCESS **except proxmox** (key mismatch, AUD-007)
- `terraform plan`: hermes, ariadne, inbox-receiver clean ("No changes"); ollama + whisper
  **fail validation** (AUD-006); pfsense cannot run (no local tfvars, see Unverifiable)
- Ollama `/api/tags`: `qwen3:1.7b`, `qwen3:4b`, `nomic-embed-text`, `mistral:7b` — no
  `qwen3:8b` (AUD-017)

---

## High severity

### AUD-001 — Add inbox-receiver to allocation tables; VMID 103 and 10.0.50.19 are taken

- **Category:** status / network · **Owner:** sprint-session
- **Evidence:**
  - `CLAUDE.md:44-45` — "Available VMIDs: 103, 109, …" and "Available IPs: VLAN 50 → 10.0.50.19+"
  - `.claude/agents/homelab-iac-specialist.md:113` — "103: available";
    `:120` — "VLAN 50: 10.0.50.19+ available"
  - Live: `pct list` shows `103 running inbox-receiver`;
    `infrastructure/mnemosyne/inbox-receiver/terraform/variables.tf` defaults vmid 103,
    `container_ip 10.0.50.19/24`; ansible ping to 10.0.50.19 → pong
  - PKM agrees with live: `Project - Mnemosyne` ("inbox-receiver LXC at 10.0.50.19")
- **Truth:** live + PKM. The repo's two allocation tables and the service roster were never
  updated when inbox-receiver deployed. This is the exact collision risk the agent file exists
  to prevent.
- **Fix:** add inbox-receiver (VMID 103, 10.0.50.19, VLAN 50) to the root CLAUDE.md roster and
  the agent allocation table; change available ranges to "109, 111–119, 123–199, 201+" and
  "VLAN 50 → 10.0.50.23+" (after reserving 10.0.50.20–22 for Argus, which the available-range
  line also currently contradicts).

### AUD-002 — Rewrite infrastructure/hermes/CLAUDE.md for the Chiron / Hermes-Agent reality

- **Category:** status · **Owner:** sprint-session
- **Evidence:**
  - `infrastructure/hermes/CLAUDE.md:23` — "IaC written — pending deployment"; `:17` — "CLI
    entrypoint (`bin/hermes`)"; `:63` — provider "pinned to `0.96.0`"
  - Reality: LXC 110 running since 2026-04-14; `infrastructure/hermes/ansible/provision.yml:113-155`
    imports the `hermes_agent` role (profile `haley`, `/opt/hermes-agent`, webhook :8644);
    `provider.tf:11` is `= 0.98.1`; live :8644/health → 200, :8765 → dead
  - PKM: `Project - Hermes` documents the 2026-05-27 pivot (Hermes-Agent upstream, local layer
    renamed Chiron) and a pending rename cascade
- **Truth:** live + ansible + PKM. The CLAUDE.md describes the superseded homegrown app.
- **Fix:** rewrite Definition of Done, Components, dependencies (Gemini/Vertex via LiteLLM —
  not Ollama-tier routing), and constraints. Update root `CLAUDE.md:31` roster wording while
  there ("Deployed — off hold 2026-05-20" understates the pivot).

### AUD-003 — Fix VLAN table in homelab-iac-specialist.md (30/40 names wrong, 66 wrong, 80 missing)

- **Category:** network · **Owner:** sprint-session
- **Evidence:**
  - `.claude/agents/homelab-iac-specialist.md:81-82` — VLAN 30 "IoT", VLAN 40 "Trusted
    Wireless"; `:85` — VLAN 66 "Quarantine"; VLAN 80 absent from the table
  - Truth sources agree with each other: `CLAUDE.md:92-105`,
    `docs/network-services-architecture-v1.6.md:108-118`, and the deployed IaC —
    `infrastructure/network/pfsense/ansible/group_vars/pfsense.yml:28,35,56,70` (WORK, IOT,
    SANDBOX, MEDIA) and `infrastructure/network/switch/ansible/group_vars/switch.yml:18-30`
- **Fix:** correct rows 30 (Work), 40 (IoT), 66 (Sandbox); add VLAN 80 Media 10.0.80.0/24.

### AUD-004 — Remove the "provider 0.96.0, no exceptions" rule from the agent file

- **Category:** terraform · **Owner:** sprint-session
- **Evidence:** `.claude/agents/homelab-iac-specialist.md:27` — "**Terraform provider is
  `bpg/proxmox` version `0.96.0`.** No exceptions." vs. `CLAUDE.md:64-66` (migration to
  0.98.1; new services use 0.98.1) and actual pins (hermes + inbox-receiver `= 0.98.1`).
- **Fix:** restate as the root CLAUDE.md policy (0.98.1 target). Same fix applies to
  `infrastructure/hermes/CLAUDE.md:63` (covered by AUD-002).

### AUD-005 — Hermes design doc v1.1 documents the superseded architecture

- **Category:** docs · **Owner:** sprint-session (technical-writer pass)
- **Evidence:** `docs/hermes-design-doc-v1.1.md` contains zero mentions of Hermes-Agent or
  Chiron; `:165-166` lists `bin/hermes` / `bin/hermes-api` (gunicorn :8765) as current;
  `:270` describes the :8765 service unit. The doc was last touched 2026-05-20 — seven days
  before the platform pivot.
- **Fix:** either bump to v2.0 reflecting Hermes-Agent + Chiron, or add a prominent
  supersession banner pointing at the PKM pivot pages until the rewrite happens. Update the
  root CLAUDE.md Key Docs row to match.

### AUD-006 — Ollama and Whisper Terraform no longer validates (cannot plan or apply)

- **Category:** terraform · **Owner:** sprint-session
- **Evidence:** `terraform plan` fails in both dirs: `Error: Unsupported argument —
  "dns_servers" is not expected here` (`infrastructure/platform/ollama/terraform/main.tf:27`;
  whisper equivalent). Both pin `~> 0.69` (`provider.tf:10-11`), and the installed provider
  rejects the config. State files exist, so the *deployed* containers are fine — but the IaC
  cannot currently reproduce them.
- **Fix:** fold into the 0.98.1 migration sweep (AUD-008): upgrade the pin, move `dns_servers`
  into the schema the new provider expects (`initialization.dns.servers`), run
  `terraform init -upgrade` + plan until clean.

### AUD-007 — proxmox Ansible inventory pins a key that puppetmaster rejects

- **Category:** conventions · **Owner:** sprint-session; re-verify via hermes-functional-test
- **Evidence:** `infrastructure/proxmox/ansible/inventory.ini:5` pins `~/.ssh/id_rsa`; live
  test: `id_rsa` → Permission denied, `homelab_ed25519` → Permission denied,
  **`id_ed25519` → success**. `ansible -m ping` → UNREACHABLE. The SSH-key convention in
  `CLAUDE.md:79` and the agent file `:49-52` lists only `id_rsa` / `homelab_ed25519`, so the
  documented convention cannot produce a working proxmox inventory.
- **Truth:** live. The proxmox playbook is unrunnable as committed.
- **Fix:** point the inventory at `~/.ssh/id_ed25519` (or authorize the conventional key —
  needs-james sub-decision), then update the convention docs to match whichever wins.

---

## Medium severity

### AUD-008 — Provider pin sweep: 8 of 10 services off the 0.98.1 target

- **Category:** terraform · **Owner:** sprint-session
- **Evidence (`provider.tf` line 7–11 per service):** hermes `= 0.98.1` ✓, inbox-receiver
  `= 0.98.1` ✓, ariadne `~> 0.96`, pfsense `~> 0.96`, postgres / redis / minio / n8n
  `= 0.96.0`, ollama / whisper `~> 0.69`. Policy: `CLAUDE.md:64-66`.
- **Fix:** one migration sprint: bump pins, `terraform init -upgrade`, plan-to-clean per
  service. Note postgres/redis/minio/n8n have no real resources (LXCs are Ansible-managed,
  `terraform/` holds `.gitkeep`-era scaffolding) — verify whether those four even need
  provider files, or delete the scaffolding instead. Includes AUD-006.

### AUD-009 — 13 vault variables in use are missing from both convention lists

- **Category:** vault · **Owner:** sprint-session
- **Evidence:** grep of `vault_*` across ansible finds 21 distinct vars; `CLAUDE.md:82-88` and
  `.claude/agents/homelab-iac-specialist.md:38-43` list 8. Undocumented:
  `vault_authelia_jwt_secret`, `vault_authelia_session_secret`,
  `vault_authelia_storage_encryption_key`, `vault_umami_app_secret`,
  `vault_umami_postgres_password`, `vault_wiki_deploy_key`, `vault_git_user_name`,
  `vault_git_user_email`, `vault_inbox_token`, `vault_chiron_gemini_api_key`,
  `vault_chiron_telegram_bot_token`, `vault_chiron_vertex_sa_json`,
  `vault_chiron_webhook_secret`.
- **Fix:** backfill both lists. Flag `vault_git_user_name`/`_email` (no service segment) as
  accepted convention exceptions or rename.

### AUD-010 — Roadmap v2.2 is stale on completed and renamed work

- **Category:** dates / status · **Owner:** sprint-session
- **Evidence:**
  - `docs/project-roadmap-v2.2.md:160` — "[ ] Daily Digest LLM swap (`claude -p` → Hermes
    `/task`)" — PKM journal `2026-05-21 — Daily Digest Gemini Swap Sprint Complete` records it
    shipped (commit `49d60e5`), and the implementation went to direct `google-genai` SDK, not
    Hermes `/task`
  - `:103` — "Mistral 7B" as the Ollama model (see AUD-017)
  - `:43` — registry lists "Mnemosyne Design Doc v1.2 ✅" (file on disk is
    `mnemosyne-design-doc-v1.1.md`; see AUD-015)
  - No Hermes-Agent/Chiron pivot reflected anywhere in Phase 2
  - Phase 2 revised target May 4, 2026 passed with phase still "in progress" (`:326`)
- **Fix:** roadmap re-sync session → v2.3: check off shipped items, rewrite the Hermes Phase 2
  block post-pivot, re-baseline targets.

### AUD-011 — The 2026-06-01 Decide gate passed with no recorded outcome

- **Category:** dates · **Owner:** needs-james
- **Evidence:** repo says queued — `CLAUDE.md:33` (roster), `infrastructure/mnemosyne/CLAUDE.md:5-7`,
  `infrastructure/mnemosyne/ToDo.md:9`, `docs/project-roadmap-v2.2.md:159,181`. PKM June
  journals show Chiron Week 3 + Vertex migration work proceeding, but no Decide-gate session
  entry exists, and `Project - Mnemosyne` `next_action` still points at the gate.
- **Fix (decision):** either hold the gate retroactively and record the selection, or declare
  the de facto outcome (Chiron migration continued as the active sprint; Phase 2T re-queued)
  and update repo + PKM in one pass.

### AUD-012 — Execute the NPM → nginx rename (PKM task already scoped)

- **Category:** docs / IaC naming · **Owner:** sprint-session
- **Evidence:** Ariadne runs native nginx + certbot, not NGINX Proxy Manager. Stale "NPM"
  references: `CLAUDE.md:28` (roster), `docs/network-services-architecture-v1.6.md:183,347,351`
  (+ §6 prose), roadmap `:254`, role dir `infrastructure/ariadne/ansible/roles/npm/`. The PKM
  ADMIN page `Rename NPM References to Nginx Across Homelab Command Repo` (2026-05-24) already
  scopes the sweep, including the role-rename risk note.
- **Fix:** run that task as written; re-run the Ariadne playbook to confirm idempotency.

### AUD-013 — mnemosyne CLAUDE.md denies the Postgres/pgvector usage that now exists

- **Category:** status · **Owner:** sprint-session
- **Evidence:** `infrastructure/mnemosyne/CLAUDE.md` — "There is no Postgres schema, no
  pgvector dependency" (Architecture section) and "The old pgvector/Postgres design is retired
  — do not reference or build against it" (Notes). Contradicted by the shipped embeddings
  sidecar (`scripts/lib/embeddings.py`, `wiki_embeddings` table, `semantic-search`,
  `embed-wiki`) and the `mneme_log` Postgres work (commits `e63f95b`…`0137466`).
- **Truth:** code. The *sidecar principle* (wiki canonical, Postgres derived) is the nuance the
  doc is missing — it currently reads as a ban.
- **Fix:** rewrite both passages: canonical store is the wiki; Postgres holds derived,
  regenerable caches (`wiki_embeddings`) and the authoritative event log (`mneme_log`).
  Update the component table while there.

### AUD-014 — Proxmox version: live 9.1.5, docs say 9.1.0 and 9.1.2

- **Category:** status · **Owner:** hermes-functional-test (recurring); sprint-session (edit)
- **Evidence:** live `pveversion` → `pve-manager/9.1.5`. `CLAUDE.md:113` — "PVE version 9.1.0";
  `docs/network-services-architecture-v1.6.md:28,295` — "Proxmox 9.1.2".
- **Fix:** update both; consider documenting "9.1.x (rolling)" to stop this class of drift, and
  add a Chiron functionality test that compares `pveversion` against the docs.

### AUD-015 — Doc version labels have diverged: filename vs. header vs. indexes

- **Category:** docs-index · **Owner:** sprint-session + needs-james (policy)
- **Evidence (filename → internal header):**
  - `network-services-architecture-v1.6.md` → **1.9** (README index and root CLAUDE.md say v1.6)
  - `iac-runbook-v1.2.md` → **1.5** (docs/README.md:16 says v1.3 — a third value)
  - `mnemosyne-design-doc-v1.1.md` → **1.2** (roadmap registry says v1.2; README + root
    CLAUDE.md say v1.1)
  - `orpheus-design-doc-v1.1.md` → **1.3**
  - Stale companion footers: network arch `:433` cites "Project Roadmap v1.3 · IaC Runbook
    v1.3"; roadmap `:370` cites "Mnemosyne Design Doc v1.2"
- **Fix (decision first):** pick a policy — either rename files on every version bump, or drop
  versions from filenames and keep them only in headers (lower-friction; links never break).
  Then one sweep to align filenames, headers, README index, roadmap registry, root CLAUDE.md,
  and companion footers.

### AUD-016 — Network architecture doc carries pre-deployment claims as current

- **Category:** docs / status · **Owner:** sprint-session
- **Evidence (`docs/network-services-architecture-v1.6.md`):**
  - `:171,312` — Hermes "LXC (planned)" (live since 2026-04-14)
  - `:303,331,376` — ntfy "pending playbook run" (ran 2026-03-10; proxied at ntfy.sirhexx.com)
  - `:377` open queue + `:422` open item #16 — "GitHub repo not created" (this repo)
  - `:400` — "repo: ~/projects/IaC-Projects/" (actual: `~/projects/homelab-command/`)
  - `:409` open item #2 — "VLAN 20 not yet renamed" vs. roadmap `:81` "[x] Rename VLAN 20"
  - `:384` — "Deploy NPM, WireGuard, Squid, Authelia (VLAN 60)" still queued MEDIUM though
    Ariadne + Authelia are deployed
  - Missing from all tables: inbox-receiver (AUD-001)
- **Fix:** one stale-sweep pass over §§1, 5, 8, 9 (pairs naturally with the AUD-015 re-version).

### AUD-017 — Three conflicting claims about the Ollama model lineup

- **Category:** status · **Owner:** needs-james
- **Evidence:** live `/api/tags`: `qwen3:1.7b`, `qwen3:4b`, `nomic-embed-text`, `mistral:7b`.
  `infrastructure/platform/ollama/CLAUDE.md:18` claims **`qwen3:8b`** is Tier 1 (not
  installed). `.claude/agents/homelab-iac-specialist.md:100` and roadmap `:103` say
  **Mistral 7B**. PKM (`Project - Hermes`, hold history) records qwen3:4b/1.7b as having
  failed for agent-loop use on CPU.
- **Fix (decision):** declare the intended Tier 1 model (or that local tier routing is
  retired post-pivot — Chiron routes to Gemini/Vertex, with Ollama serving embeddings only),
  then align the three docs and optionally prune unused models.

### AUD-018 — Semantic search embeds without nomic task prefixes; coverage 636/686

- **Category:** PKM-tooling · **Owner:** sprint-session
- **Evidence:** `infrastructure/mnemosyne/scripts/lib/embeddings.py:68-69` sends bare text;
  `nomic-embed-text` expects `search_query:` / `search_document:` prefixes for asymmetric
  retrieval. Observed: "What is the current status of Hermes?" missed `Project - Hermes.md`
  (which is embedded) entirely; keyword queries work. Coverage: 636 rows in `wiki_embeddings`
  vs. 686 wiki pages — verify the ~50 gap is intentional (inbox/templates/raw exclusions).
- **Fix:** add `search_document:` at index time and `search_query:` in `semantic-search`;
  re-run `embed-wiki` to rebuild the corpus (cache is regenerable by design); confirm
  exclusion list.

### AUD-019 — homelab-iac-specialist.md self-contradicts on IaC state and Hermes

- **Category:** status · **Owner:** sprint-session (fold into AUD-003/004 agent-file resync)
- **Evidence:** allocation table `:100-101` marks ollama/whisper "Ansible" while the same
  file's IaC State Reference `:130-131` says "Terraform ✅ + Ansible ✅"; `:107` — hermes
  "(planned VMID)" though live; `:139` — Mnemosyne "Planned" (inbox-receiver IaC is written
  and deployed).
- **Fix:** full resync of the agent file in one edit alongside AUD-001/003/004.

---

## Low severity

### AUD-020 — Latent roles_path bugs in proxmox and switch ansible.cfg

- **Owner:** sprint-session
- **Evidence:** `infrastructure/proxmox/ansible/ansible.cfg:3` uses `../../../ansible/roles`
  (2-level service — should be `../../`; resolves to a nonexistent path);
  `infrastructure/network/switch/ansible/ansible.cfg:3` is `roles` only (no shared path).
  Both currently work because each playbook uses only local roles — they break the moment a
  shared role (e.g. dotfiles) is added.
- **Fix:** correct both to the convention in `CLAUDE.md:71-75`.

### AUD-021 — Decide fate of untracked infrastructure/hermes/scripts/ and test-results/

- **Owner:** needs-james
- **Evidence:** untracked since 2026-03-18 (`ab-test-models.sh` + 3 benchmark `.md` files);
  `infrastructure/hermes/CLAUDE.md:74` still says "review before committing or gitignoring".
  Post-pivot, the benchmarks describe the superseded homegrown router.
- **Fix (decision):** commit as historical record, or gitignore/delete.

### AUD-022 — Old `hermes` Ansible role is dead code beside `hermes_agent`

- **Owner:** sprint-session
- **Evidence:** `infrastructure/hermes/ansible/roles/` holds both `hermes/` and
  `hermes_agent/`; `provision.yml` imports only `hermes_agent` (`:113-114`).
- **Fix:** delete the old role (git history preserves it) or move under an `_archive/` mirror
  of the `apps/hermes/lib/skills/_archive/` pattern. Pair with AUD-002.

### AUD-023 — Duplicate skill copies: flat .md files vs. skill directories

- **Owner:** needs-james
- **Evidence:** `~/.claude/skills/mneme-ask.md` (flat) and `~/.claude/skills/mneme-ask/SKILL.md`
  both exist; same for `mneme`. The Skill tool loads only the directory form — the 2026-06-11
  semantic-search update initially landed in the flat file and silently didn't take effect
  (fixed during this audit by copying into `SKILL.md`). Outside the repo, but it burned us once.
- **Fix (decision):** remove the flat duplicates (or repurpose them as docs with a pointer),
  so future edits can't land in the dead copy.

### AUD-024 — docs/README.md index nits

- **Owner:** sprint-session (fold into AUD-015 sweep)
- **Evidence:** `docs/README.md:16` — runbook version cell "v1.3" next to the v1.2 link;
  `nas-readmes/` directory and `network-topology.drawio` absent from the index.
- **Fix:** correct in the AUD-015 alignment pass; add the two missing entries.

### AUD-025 — semantic-search script is untracked

- **Owner:** sprint-session
- **Evidence:** `git status` shows `infrastructure/mnemosyne/scripts/semantic-search` as
  untracked. The `/mneme-ask` skill (fixed during this audit) now calls it by absolute path —
  the skill's primary retrieval path depends on an uncommitted file.
- **Fix:** commit the script (it follows the existing scripts/ conventions and uses
  `lib/embeddings.py`, which is already tracked).

---

## Unverifiable items

| Item | Why | Suggested resolution |
|------|-----|----------------------|
| pfSense Terraform drift | No `terraform.tfvars` on this machine (only `.example`); plan exits on missing `proxmox_endpoint` / API token vars | Recreate tfvars from example (credentials from vault/Proxmox), or document where the working copy lives |
| Switch config vs. IaC | Telnet transport; no read-only check attempted from this session | Cover in next switch playbook run |
| Orpheus *Arr reconfiguration state | TrueNAS apps not probed (out of audit scope); PKM has open ADMIN tasks (e.g. `Configure Bazarr`) | Treat PKM ADMIN tasks as authoritative backlog |
| Porkbun domain migration | Roadmap items unchecked; no PKM completion record — consistent, just stalled since ~April 2 | Confirm intent at next roadmap re-sync (AUD-010) |
| Postgres/Redis internal health | No deep checks (`pg_isready`/`redis-cli` via SSH skipped — endpoints' hosts answered ansible ping) | Optional Chiron functionality test |

---

## Suggested sprint grouping

1. **Agent-file + allocation resync** (1 session): AUD-001, 003, 004, 019 + roster touch-ups
   from AUD-002. One file-set, mostly mechanical, kills the collision risk.
2. **Hermes/Chiron doc truth pass** (1 session): AUD-002, 005, 022, 021 decision. Pairs well
   with the PKM rename-cascade work already queued there.
3. **Provider 0.98.1 migration sweep** (1–2 sessions, service-by-service): AUD-006, 008;
   includes the platform-services scaffolding decision.
4. **Docs re-version + stale sweep** (1 session): AUD-015 policy decision, then AUD-010, 012,
   014, 016, 024 in one pass — roadmap v2.3, network arch refresh, NPM rename.
5. **Small fixes batch** (under an hour): AUD-007 inventory key, AUD-020 roles_path, AUD-009
   vault list backfill.
6. **Mnemosyne tooling** (1 session): AUD-013 CLAUDE.md rewrite, AUD-018 prefix fix + re-embed.
7. **Decisions for James** (no code): AUD-011 gate outcome, AUD-017 Ollama model intent,
   AUD-021 benchmark files, AUD-023 flat skill duplicates, AUD-015 version-label policy.

### Hermes functionality-test candidates

Recurring read-only checks worth porting to Chiron skills: health-endpoint sweep (the 9 URLs
above), `pct list` vs. roster reconciliation, `pveversion` vs. docs, `terraform plan`-clean
checks, ansible ping sweep, `wiki_embeddings` count vs. wiki page count.

---

## Methodology

- **Repo pass:** read in full — root CLAUDE.md, `.claude/agents/homelab-iac-specialist.md`,
  `docs/network-services-architecture-v1.6.md`, `docs/project-roadmap-v2.2.md`, docs/README.md,
  service CLAUDE.md files; grepped all `provider.tf`, `ansible.cfg`, `inventory.ini`, and
  `vault_*` usage; targeted factual pass over design docs.
- **Live pass (read-only):** SSH `pct list` / `qm list` / `pveversion`; `ansible -m ping` per
  inventory; `terraform plan` (never apply) in the six dirs with real state; HTTP health
  probes; Ollama tag listing. Working tree left clean apart from this report.
- **PKM pass:** semantic search (post-fix) + targeted greps over `~/mneme/wiki/`; pages read:
  `Project - Hermes`, `Project - Mnemosyne`, `Rename NPM References…`, June 2026 journals,
  `2026-05-21 — Daily Digest Gemini Swap Sprint Complete`.
- Three-way disagreements were classified by which source the live check (or the most recent
  dated record) supported.
