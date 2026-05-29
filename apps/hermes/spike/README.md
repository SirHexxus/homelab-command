# Hermes-Agent Verification Spike

Validate 4 unverified claims about Hermes-Agent before committing to the migration. Throwaway — delete `spike/` when done.

Spec for the downstream migration if GO: `~/mneme/wiki/admin/Migrate to Hermes-Agent Platform and Rename Hermes to Chiron.md`

## Run order

| Phase | Spikes | Wall-clock |
|-------|--------|------------|
| Day 1 morning | `install/` → Spikes 1 + 3 in parallel | 4-5h |
| Day 1 afternoon | Spike 4 | 2-3h |
| Day 1 evening | Spike 2 setup; leave systemd unit running overnight | 1h + overnight |
| Day 3 | Review Spike 2; fill `spike-report.md`; decide | 1-2h |

## Prerequisites

- [ ] n8n echo workflow created and self-tested (see `n8n-echo-workflow-SPEC.md`)
- [ ] Gemini API key available (use the `gemini-creds.json` pattern from the homelab)
- [ ] Python 3.11+ on the spike machine
- [ ] ~2GB disk for the venv

## Layout

```
spike/
  README.md                    ← this file
  n8n-echo-workflow-SPEC.md    ← spec for the user to implement in n8n
  install/                     ← installer + systemd unit
  spike-1-mcp/                 ← MCP-client verification
  spike-2-gateway/             ← Headless gateway verification
  spike-3-routing/             ← Per-task model routing verification
  spike-4-wiki-port/           ← wiki.py → agentskill port effort
  spike-report.md              ← aggregate report (fill at end)
```

## Decision rule

- **All 4 pass** → GO. Begin migration Week 1.
- **3 of 4 pass, 4th is workable PARTIAL** → GO with plan modification. Note in `spike-report.md`.
- **2 or more fail** → NO-GO. Platform choice returns to evaluation.

## What I'm explicitly not pre-writing

- Exact Hermes-Agent config field names — discovered during install via `hermes --help`, `hermes doctor`, `hermes config --help`
- The agentskills.io skill format — discovered from the installed `~/.hermes-agent/skills/` examples or the project docs
- The MCP transport type n8n uses (SSE vs HTTP vs stdio) — discovered from the n8n MCP Server Trigger node config

These all come into focus within the first hour of Day 1. Leaving them as discovery prevents guessing wrong and writing scaffolding that doesn't match reality.
