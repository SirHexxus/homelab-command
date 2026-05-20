# Hermes — Agent Task List

Maintained by Claude Code (Project Manager role). Updated each session.
Source of truth: `Mnemosyne-Hand-Off.md` (historical requirements spec), `THOUGHTS.md`
(design rationale).

---

## Status: Active (off hold 2026-05-20)

Hermes is off hold. Active Orient session: **Hermes Orient - Reframe After Hold Lift**
(wiki page: `~/mneme/wiki/admin/`). Build-sprint selection happens at the
**Decide First Mnemosyne and Hermes Build Sprint** gate on 2026-06-01.

Do not start work on Post-Hold-Lift Candidates (below) before the Decide gate. The Orient
sessions exist to inform that decision.

---

## Phase 2 — Complete

All Phase 2 deliverables shipped. LXC live at VMID 110, 10.0.50.17.

| # | Item | Date | Outcome |
|---|---|---|---|
| 1 | Archive `lib/skills/mneme.py` | 2026-04-10 | Moved to `lib/skills/_archive/mneme_postgres.py`; deregistered |
| 2 | Resolve Terraform provider version conflict | 2026-04-10 | Pinned `bpg/proxmox = 0.96.0`; lock file regenerated |
| 3 | Wire Gemini + Claude into `LLMRouter` | 2026-04-10 | Three-tier waterfall (Ollama → Gemini → Claude); task_type routing |
| 4 | Implement `lib/skills/wiki.py` | 2026-04-10 | 7 skills registered; filelock on `git_commit_push` |
| 5 | Minimal HTTP endpoint (`/task` + `/health`) | 2026-04-11 | Flask/gunicorn on port 8765; Bearer token auth |
| 6 | Deploy LXC (VMID 110, 10.0.50.17) | 2026-04-14 | `terraform apply` + `ansible-playbook provision.yml` clean; `/health` returns 200 |
| 7 | `IngestItem` dataclass | 2026-04-11 | `lib/core/ingest.py`; consumed by ingest pipeline |
| 9 | Update this directory's `CLAUDE.md` | 2026-04-11 | Runtime deps, interface phases, app structure tree refreshed |

---

## Pending — Pre-Hold-Lift Carryover

### Item 8 — Telegram Bot (Personal Context) — SUPERSEDED

Superseded by n8n-as-bot-frontend architecture. n8n's Telegram Trigger node owns the bot
surface; n8n HTTP-POSTs ingest items into Hermes at `10.0.50.17:8765/task`. Workflow at
`infrastructure/mnemosyne/n8n/mnemosyne-ingest-v1.json` (export). There is no
`lib/interfaces/telegram_bot.py` to build inside Hermes; the bot is an n8n responsibility.

Preserved here as design history. Do not implement.

### Item 10 — Update `config/config.example.yml`

Status: Pending.

- Remove Postgres mnemosyne block (commented out but misleading)
- Add `mnemosyne: wiki_path:` and `wiki_remote:` config keys
- Add `model_routing:` block (see THOUGHTS.md for shape)
- Add `gemini_api_key:` and `claude_api_key:` (uncommented placeholders) — note: see also
  the `gemini-creds.json` pattern candidate below; this item may be subsumed
- Remove complexity-score routing section (replaced by task_type routing)

---

## Pending — Post-Hold-Lift Candidates

Candidates feeding the **Decide First Mnemosyne and Hermes Build Sprint** gate (2026-06-01).
No priority order committed here. Acceptance criteria for the chosen sprint will be written
into a dedicated ADMIN page after selection.

- GeminiClient refactor against the `gemini-creds.json` pattern (siblings: weather-creds,
  telegram-creds migrations)
- LLM-default switch to `gemini-3.5-flash` (pinned, not `-latest`) across `LLMRouter` and
  `config/config.example.yml`
- Daily Digest `claude -p` → `gemini-3.5-flash` direct API swap (eliminates ~29k tokens
  of Claude Code framework overhead per run; cost $0.014 → $0.0072)
- Mnemosyne Phase 2 ingest pipeline kickoff (current interim path bypasses Hermes via
  inbox-receiver LXC; target path routes through Hermes)
- ReAct-loop scope reduction: extract single-shot classification for simple ingest tasks;
  reserve ReAct for genuine multi-step judgment (see `THOUGHTS.md` Phase 3 single-shot
  architecture, and `[[AI Agents Are the Wrong Abstraction Layer]]`)

---

## Delivery Order

```
NOW:    Hermes Orient session (this list audit + GeminiClient code audit)
NEXT:   Mnemosyne Orient + Top-level Orient sessions
THEN:   Decide gate (2026-06-01) — pick one candidate from above
THEN:   Spin up dedicated ADMIN page for the chosen sprint, execute
```

One sprint at a time. Do not pre-commit beyond the chosen #1.
