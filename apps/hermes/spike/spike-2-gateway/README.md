# Spike 2 — Headless gateway / programmatic task injection

**Goal:** verify Hermes-Agent can run as a systemd-managed daemon with no TTY, accept tasks from an automated caller (n8n), and stay up for 24h without intervention.

**Effort target:** 1h active + 24h passive (overnight).

This spike is most likely to surface unknowns. The Hermes-Agent README leans on chat-style use; the gateway's programmatic interface(s) need empirical discovery.

## What we're actually testing

Three possible interfaces — find which (if any) work, pick the cleanest for n8n integration:

| Interface | What it looks like | Best for |
|-----------|--------------------|----------|
| **A. Native HTTP/RPC** | `POST /task` or `/v1/messages` → JSON response | Cleanest n8n integration |
| **B. Channel-as-API** | n8n drives a "channel" Hermes-Agent owns (Telegram-style hook); n8n forwards to/from the real channel | Workable if A doesn't exist |
| **C. CLI non-interactive** | `hermes --message "task" --json` returns structured output; n8n calls via local exec / SSH | Last resort |

Preference: A > B > C. Document which work.

## Setup

```bash
mkdir -p ~/.config/systemd/user
cp ../install/hermes-agent-spike.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hermes-agent-spike.service
systemctl --user status hermes-agent-spike.service
```

If `hermes gateway start` requires interactive setup the first time, run it once manually to complete auth, then start the unit.

## Test sequence

### 2.1 — Headless start

`systemctl --user start hermes-agent-spike.service`. Watch `journalctl --user -u hermes-agent-spike.service -f`.

**Pass:** service stays up; no TTY-required errors; no interactive prompts blocking startup.
**Fail:** service exits because it needs a terminal, or requires manual input to start.

### 2.2 — Interface discovery

For each candidate interface (A, B, C):

- **A (HTTP/RPC):** check `hermes gateway --help`, project docs, source code. Look for a port being listened on. `ss -tlnp | grep hermes` or `netstat -tlnp`. If a port is bound, try `POST /task` and `POST /v1/messages` with curl.
- **B (Channel-as-API):** check `hermes gateway --help` for "webhook" or "http channel" — some agents expose a generic HTTP channel that mimics a messaging platform.
- **C (CLI):** run `hermes --help` and look for `--message`, `--input`, `--json`, `--non-interactive` flags.

Document which exist.

### 2.3 — Task injection round-trip

For whichever interface works (preferring A), inject a simple classification task:

```
Task: classify the following note into one of: idea, task, journal.
Note: "I should look into the Chiron migration spike findings tomorrow morning."
```

**Pass:** response is structured (JSON or parseable text); contains a classification; latency under 10s.
**Fail:** no response; response is unparseable; latency over 30s.

Run `test-inject` once it knows which interface to hit.

### 2.4 — 24h uptime + memory growth

Start `measure-memory` in the background (or via cron):

```bash
./measure-memory &
```

Snapshots RSS every hour into `memory.log`. Run injections every 15 minutes via cron during the test window:

```bash
# crontab -e --user
*/15 * * * * /home/james/projects/homelab-command/apps/hermes/spike/spike-2-gateway/test-inject >/dev/null 2>&1
```

After 24h:

- **Uptime pass:** `systemctl --user status` shows active; no restarts logged.
- **Memory pass:** RSS growth under 50% of baseline. (e.g., starts 200MB, ends under 300MB.)
- **Fail:** crashed and didn't restart; memory grew > 100%; injection latency degraded over time.

### 2.5 — Restart resilience

`systemctl --user restart hermes-agent-spike.service`. Inject a task within 30s.

**Pass:** service comes up clean; injection succeeds.
**Fail:** restart requires manual setup; injection fails post-restart.

## What to record in `spike-report.md`

- Result per sub-test (2.1 - 2.5)
- Which interface(s) work; chosen interface for downstream migration
- 24h memory log (paste min/max/final)
- Any restart events from the journal
- Configuration steps that turned out to be required (especially anything interactive)
