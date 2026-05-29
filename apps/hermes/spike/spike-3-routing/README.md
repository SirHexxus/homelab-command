# Spike 3 — Per-task model routing

**Goal:** verify Hermes-Agent supports per-skill or per-task model selection (Gemini 3.5 Flash default; Gemini 3.1 Pro on opt-in only) without forking the upstream.

**Effort target:** 1-2h.

## What you're testing

The Chiron routing table (see migration sprint page) needs:

- **Default for everything:** `gemini-3.5-flash`
- **Opt-in for one specific skill:** `gemini-3.1-pro` (Idea Synthesis only, never in cron)

The mechanism doesn't matter — what matters is that it's config-driven (not a fork) and verifiable (logs confirm the actual model used, not just the configured one).

## Setup

You need two test skills. Skill format is agentskills.io standard; the exact folder layout becomes obvious from `~/.hermes-agent/skills/` examples after install. Likely shape:

```
test-skills/
  simple_classify/
    SKILL.md          ← manifest (name, description, model preference?)
    instructions.md   ← system prompt
    (optional code/tools)
  idea_synthesis_test/
    SKILL.md
    instructions.md
```

Discover the actual format during install. Then create both skills following these specs:

### `simple_classify`

- Description: "Classify a one-line note into: idea | task | journal | reference. Return JSON."
- Model preference: default (i.e., Gemini 3.5 Flash)
- Input: one string (the note)
- Output: JSON `{"bucket": "..."}`
- System prompt: short, single-shot

### `idea_synthesis_test`

- Description: "Take two short notes and produce a one-paragraph synthesis connecting them. Return prose."
- Model preference: **override to `gemini-3.1-pro`** (this is what the spike tests)
- Input: two strings
- Output: one paragraph of prose
- System prompt: synthesis-flavored

## Test sequence

### 3.1 — Default model works

Invoke `simple_classify` with a sample note. Verify:

- Trajectory log shows Gemini 3.5 Flash was called
- Gemini API request log (in your Google Cloud console) shows a Flash call at that timestamp
- Output is valid JSON

**Pass:** model used = Flash, verified independently.
**Fail:** different model used, or Hermes-Agent doesn't log which model was used.

### 3.2 — Per-skill override works

Invoke `idea_synthesis_test` with two sample notes. Verify:

- Trajectory log shows Gemini 3.1 Pro was called
- Gemini API request log shows a Pro call at that timestamp
- Output is one paragraph of prose

**Pass:** override took effect; verified independently.
**Fail:** Flash used despite override config; or override required a fork.

### 3.3 — Configuration approach review

Subjective: was the override config-driven (YAML field, skill manifest entry) or did it require code changes to Hermes-Agent?

**Pass:** override is a config field on the skill (or in a router config) that anyone could edit.
**Soft fail:** override works but requires a Python middleware shim you'd have to maintain.
**Fail:** override requires forking Hermes-Agent or monkeypatching.

### 3.4 — Cron-protection mechanism

Can you express "this invocation should never escalate to Pro, even if the skill says so"? Possible mechanisms:

- A "no-escalation" flag passed at invocation time
- A profile/persona configuration that pins the model
- A wrapper script that strips Pro from the routing table before invoking

The cleanest answer: some way to override per-invocation. Doesn't need to be elegant.

**Pass:** some viable mechanism exists.
**Soft fail:** workaround possible but ugly (e.g., separate cron-only skill folder with Flash hardcoded).
**Fail:** no way to prevent escalation in cron contexts.

## How to verify model used

Two independent sources:

1. **Hermes-Agent's trajectory log** — should record the model per invocation. Find its path during install (`hermes --help` or check `~/.hermes-agent/`).
2. **Gemini API console** (https://console.cloud.google.com/) — Logging shows requests by model. Cross-reference timestamps.

If Hermes-Agent doesn't log the model, the Gemini console is sufficient on its own.

## What to record in `spike-report.md`

- Result per sub-test (3.1 - 3.4)
- The override mechanism (config field, manifest entry, middleware, etc.)
- Trajectory log excerpt showing model per call
- Cost delta visible in Gemini console
- Subjective DX rating (1-5)
