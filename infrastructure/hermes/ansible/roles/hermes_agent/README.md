# roles/hermes_agent

Installs and configures the [Hermes-Agent](https://github.com/NousResearch/hermes-agent)
platform (NousResearch, MIT, Python 3.11+) on a Hermes LXC, plus the local
**Chiron** persona/skill layer that customizes it for this homelab.

Replaces the homegrown `hermes` role (kept on disk until the Week 8 cascade
rename). See `docs/hermes-design-doc-v1.1.md` and the Mnemosyne sprint page
`Migrate to Hermes-Agent Platform and Rename Hermes to Chiron` for context.

## What it does

1. Installs apt build deps (`base.yml`).
2. Bootstraps `uv` (Astral's Python manager) for the install user (`uv.yml`).
3. Clones Hermes-Agent at the pinned commit, creates a Python 3.11 venv via
   uv, `pip install -e ".[all]"` plus `python-telegram-bot` (`install.yml`).
4. Templates `/etc/hermes-agent/env` (systemd EnvironmentFile, secrets via
   Vault) and patches `~/.hermes/config.yaml` to set the default model and
   enable the webhook + Telegram platforms. Registers configured MCP
   servers (`config.yml`).
5. Creates each configured Hermes-Agent profile (persona), templates its
   `SOUL.md` (persona system prompt) and `USER.md` (user model), and sets
   the sticky default profile (`profile.yml`).
6. Installs and starts `/etc/systemd/system/hermes-agent.service` running
   `hermes gateway run` (`service.yml`).

Each task is idempotent — re-runs converge to no-change when the LXC is
already in the desired state. `pip install` only runs when the pinned git
commit changes.

## Persona content (SOUL.md / USER.md) lives in this repo

Hermes-Agent stores three persistent files per profile, each carrying a
distinct concern:

| File         | What it carries                            | Lifetime                             | Source of truth                       |
| ------------ | ------------------------------------------ | ------------------------------------ | ------------------------------------- |
| `SOUL.md`    | Persona — voice, posture, off-limits       | Stable; revised when persona shifts  | `templates/<persona>-SOUL.md.j2` here |
| `USER.md`    | User model — who James is, what he values  | Stable; revised when identity model deepens | `templates/<persona>-USER.md.j2` here |
| `MEMORY.md` | Episodic notes — what happened, what's remembered | Evolving; agent writes this over time | Not in IaC — runtime state on LXC     |

**Conflating these is the most common authoring mistake.** Facts about
James → `USER.md`. Facts about the persona's voice or role → `SOUL.md`.
Facts about specific past interactions → `MEMORY.md`.

USER.md is **near-identical across personas** because James is one person.
SOUL.md is **where personas diverge**.

### Currently provisioned personas

- **`templates/haley-SOUL.md.j2`** — Haley, the senior personal assistant.
  Coaching warmth + sardonic accountability. Greetings, closers, recaps,
  stale-content nudges, the relationship layer of the AI stack.
- **`templates/haley-USER.md.j2`** — User model loaded under Haley. Sourced
  from the Mnemosyne wiki pages `The Man I Want To Be` and
  `North Star — The Man I Want To Be`.

Margot, Quinn, and Reese will be added as additional templates + profile
entries in `defaults/main.yml` as their build sequence weeks come up.

### Design rationale for persona content

The persona templates are *deliberately* designed against two upstream
documents:

1. **Hexxus Voice Identity Guide** (`~/projects/hexxus-brand-guidelines/Hexxus_Voice_Identity_Guide.pdf`)
   — defines the voice anti-patterns every Chiron persona inherits
   (anti-sycophancy, anti-performance, earned confidence, lead with the
   point).
2. **The Man I Want To Be** (Mnemosyne wiki, `~/mneme/wiki/ideas/`) — the
   identity model the personas operate downstream of. Personas do *not*
   recite his philosophy; they enact it.

The design framework lives in the wiki at
`[[Chiron Persona Design Principles]]`, with the Haley-specific worked
application at `[[Haley as Enactment of Fidelity and The Witnessed Life]]`.
**Read those before editing any persona template here.** They are the
source of truth for what gets included, what gets excluded, and why.

### How to add a new persona

1. Write `templates/<name>-SOUL.md.j2` — start from the persona spec at
   `[[Mnemosyne TTS Voice Personas]]`, validate against the Voice Identity
   Guide and TMIWTB per `[[Chiron Persona Design Principles]]`.
2. Write `templates/<name>-USER.md.j2` — most lift can come from copying
   `haley-USER.md.j2` and adjusting the section emphasis appropriate to
   the persona's coverage area. (Quinn might lean on Rule 9; Margot on
   Rule 7; Reese on the family-as-anchor framing for outreach drafts.)
3. Append a profile entry to `hermes_agent_profiles` in
   `group_vars/hermes_containers.yml` (or `defaults/main.yml` if the
   default list is being extended):
   ```yaml
   - name:        <name>
     description: "…one or two sentences…"
     soul_template: <name>-SOUL.md.j2
     user_template: <name>-USER.md.j2
   ```
4. Run the playbook; the new profile + its content will be provisioned
   without disturbing existing personas.

## Variables

See `defaults/main.yml` for the complete list. The ones most likely to be
overridden in `group_vars/hermes_containers.yml`:

| Variable                              | Purpose                                          |
| ------------------------------------- | ------------------------------------------------ |
| `hermes_agent_version`                | Pinned Hermes-Agent git commit                   |
| `hermes_agent_telegram_allowed_users` | Comma-separated Telegram user IDs (DM allowlist) |
| `hermes_agent_mcp_servers`            | List of `{name, url}` MCP servers to register    |
| `hermes_agent_profiles`               | List of persona profile definitions              |
| `hermes_agent_active_profile`         | Sticky default profile                           |

### Secrets (Ansible Vault)

| Vault variable                       | Purpose                                  |
| ------------------------------------ | ---------------------------------------- |
| `vault_chiron_gemini_api_key`        | Google AI Studio API key for Gemini      |
| `vault_chiron_telegram_bot_token`    | @HaleyChironBot bot token                |
| `vault_chiron_webhook_secret`        | HMAC-SHA256 secret for inbound webhooks  |

See `group_vars/vault.yml.example` for placeholder format.

## Verifying

After a successful run:

```bash
ssh root@10.0.50.17
systemctl status hermes-agent.service          # active (running)
journalctl -u hermes-agent.service -n 30       # gateway log
hermes profile list                             # ◆haley should be active
hermes mcp test n8n-echo                        # MCP connectivity
```

End-to-end smoke: DM `@HaleyChironBot` on Telegram — should respond in
Haley's voice ("Hello, Mr. Stacy"-shaped opener, sardonic warmth, no
sycophantic filler).

## Related

- Wiki pages (canonical design rationale):
  - `[[Chiron Persona Design Principles]]`
  - `[[Haley as Enactment of Fidelity and The Witnessed Life]]`
  - `[[Mnemosyne TTS Voice Personas]]`
  - `[[The Man I Want To Be]]`
  - `[[Two Kinds of Agent Memory]]`
- Migration sprint page: `[[Migrate to Hermes-Agent Platform and Rename Hermes to Chiron]]`
- Spike report: `apps/hermes/spike/spike-report.md`
- The Hexxus Voice Identity Guide lives in `~/projects/hexxus-brand-guidelines/`
  (separate repo); the wiki page `[[Hexxus Brand Guidelines]]` indexes it.
