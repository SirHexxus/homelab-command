# Spike 4 — `wiki.py` → agentskill port

**Goal:** port one skill from the current `lib/skills/wiki.py` into the agentskills.io format Hermes-Agent uses; measure effort; extrapolate to full-port estimate.

**Effort target:** 2-3 hours for `read_wiki_page` (the simplest skill).

## Which skill to port

**Port `read_wiki_page` only.** Why:

- Read-only — no git side effects
- No filelock concern
- Simple contract: `path` → markdown content
- Easy to verify correctness — eyeball the output against the actual file

Do NOT port `git_commit_push` for the spike — its complexity (filelock + git ops + push semantics) would dominate the timing and skew the estimate badly.

## Setup

1. Read the current `read_wiki_page` implementation: `apps/hermes/lib/skills/wiki.py`. Understand its full contract (args, return shape, error handling).
2. Locate the agentskills.io skill format — likely in `~/.hermes-agent/skills/` examples or the project docs. Capture the format in `format-notes.md` if it's not obvious from the install.
3. Create a skill folder: `mneme_wiki/` (or whatever Hermes-Agent expects), with the structure agentskills.io requires.

## Test sequence

### 4.1 — Start timing

```bash
date +%s > start.txt
```

Don't stop the clock until you have a working skill that returns the right content. Pausing for lunch is fine but note it.

### 4.2 — Port the skill

Implement `read_wiki_page` in the agentskills.io format. Aim for behavioral equivalence — same args, same return shape, same error cases.

Likely shape of the work:

- Skill manifest (name, description, input schema)
- Implementation (Python is most likely supported; the format spec confirms)
- Path-handling for the wiki repo location (config-driven, not hardcoded)
- Reading SCHEMA.md if Hermes-Agent supports skill-level system prompt injection

### 4.3 — Install / register

Whatever Hermes-Agent does to discover skills — copy to the right path, register via CLI, restart, etc.

### 4.4 — Functional verification

Prompt the agent:

```
Read the wiki page at projects/Project - Hermes.md
```

Compare the returned content against the actual file. They should match exactly (modulo any whitespace normalization the skill does intentionally).

### 4.5 — Stop timing, log

```bash
date +%s > end.txt
```

Fill out `porting-log.md` with the wall-clock time + notes.

## Estimating the full port

Apply the complexity multipliers (from spike spec, repeated here):

| Skill | Multiplier |
|-------|------------|
| `read_wiki_page` | 1.0 (baseline) |
| `read_wiki_index` | 0.5 |
| `list_wiki_pages` | 1.0 |
| `scan_wiki_inbox` | 1.0 |
| `write_wiki_page` | 1.5 |
| `append_wiki_log` | 1.5 |
| `git_commit_push` | 3.0 |
| **Total** | **~9.5×** |

If `read_wiki_page` took 2h: total port ≈ **19 hours**. Pass-equivalent threshold: full port ≤ ~28 hours (4h × 7 in baseline assumption). Anything over that pushes Spike 4 to Fail.

## Pass / Fail

- **Pass:** port completes in under 2 focused hours; skill works correctly; format feels natural.
- **Soft Pass:** 2-4 hours; works correctly; format had quirks worth documenting but no fight.
- **Fail:** over 4 hours, OR format requires fundamental restructure of the wiki interface, OR Hermes-Agent's skill model can't express the file-path-aware contract `wiki.py` has.

## What to record in `spike-report.md`

- Final wall-clock time (from `porting-log.md`)
- Full-port extrapolation (wall-clock × 9.5)
- Subjective DX rating (1-5)
- Format quirks / surprises to remember during full port
- Anything that suggests the multipliers above are wrong
