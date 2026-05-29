# Spike 4 — `read_wiki_page` Porting Log

Path C (hybrid): Claude scaffolded SKILL.md + Python script; user reviewed, installed, and tested. Headline finding turned out to be a **design lesson**, not a wall-clock measurement.

## Scaffolding (Claude, 2026-05-28)

Scaffolding time: ~15 min wall-clock (not load-bearing — Path C measures user time).

Files produced under `mneme_wiki/`:

- `SKILL.md` — frontmatter + workflow prose, modeled on Whisper's richer manifest pattern
- `scripts/read_wiki_page.py` — standalone executable Python, mirrors the homegrown contract

Smoke-tested locally from the laptop before installation:

| Case | Expected | Actual |
|------|----------|--------|
| `projects/Project - Hermes.md` | exit 0, content streamed | ✓ |
| `nonsense/does-not-exist.md` | exit 2, FileNotFound | ✓ |
| `../../../etc/passwd` | exit 4, PermissionError (traversal blocked) | ✓ |

Wiki root resolved from `$MNEME_WIKI_PATH` env var with fallback `~/mneme/wiki`. Path-traversal guard implemented as a code-enforced check.

## User installation + test (2026-05-28)

Skill installed to `~/.hermes/skills/mneme_wiki/`. Tested via `hermes-spike chat` with prompt:

> Read the wiki page projects/Project - Hermes.md

End-user goal achieved: agent loaded the skill, located the file, returned an accurate summary of the page in 14s wall-clock.

## Headline finding — the Python script never ran

Trace from the test:

```
🔎 find      *Project - Hermes*     ← agent searched for the file
🔎 find      *.md
🔎 find      *Project - Hermes*
📚 skill     mneme_wiki              ← skill loaded (SKILL.md instructions internalized)
📖 read      /home/james/mneme/wiki/projects/Project - Hermes.md   ← built-in file.read, NOT read_wiki_page.py
```

The agent loaded the SKILL.md prose, internalized the wiki location and naming patterns, then used Hermes-Agent's **built-in `file.read` tool** to fetch content. `read_wiki_page.py` was never invoked.

This matches the pattern observed in the bundled `note-taking/obsidian/SKILL.md` skill, which has zero scripts — pure prose telling the agent to use built-in `read_file`, `search_files`, `write_file`, `patch` against the vault path.

## Revised port strategy

Read-only operations don't need scripts. Pure SKILL.md prose with the wiki root resolution instructions is sufficient. Write and git operations benefit from scripts for **code-enforced policy** — traversal guards, schema validation, filelocks — that prose alone cannot enforce.

| Skill | Strategy | Multiplier | Rationale |
|-------|----------|-----------:|-----------|
| `read_wiki_page` | prose-only | 0.5× | built-in `file.read` |
| `read_wiki_index` | prose-only | 0.3× | subset of read |
| `list_wiki_pages` | prose-only | 0.5× | built-in `search_files` |
| `scan_wiki_inbox` | prose-only | 0.5× | built-in `search_files` |
| `write_wiki_page` | script | 1.5× | needs traversal guard + schema check enforced in code |
| `append_wiki_log` | script | 1.5× | needs atomic append + timestamp |
| `git_commit_push` | script | 3.0× | needs filelock + git subprocess + push semantics |
| **Total** | hybrid | **~7.8×** | down from earlier 9.5× estimate |

## Soft vs. hard policy boundary

The traversal guard in `read_wiki_page.py` would never fire under this design — the agent uses `file.read`. We're relying on SKILL.md prose ("only read paths within the wiki") as a **soft constraint** the agent honors, not a code-enforced hard constraint.

For reads, soft is acceptable — low blast radius. For writes and git ops, code-enforced guards in scripts are non-negotiable. This connects directly to the [autonomous action boundaries](../../../../../.claude/projects/-home-james-projects-homelab-command/memory/feedback_autonomous_action_boundaries.md) memory: trust-via-prose and trust-via-code are different threat models, and the migration plan should distinguish them.

## Subjective DX

Rating: **5 / 5**

Why: asked for a port, got a working skill the same day. The "wasted" Python script turned out to teach the actual lesson about skill format. Net win.

## Confidence in revised multipliers

Medium-high. One direct data point (read prose-only works), one well-precedented pattern (Obsidian skill), one unknown (writes/git not yet ported). The write/git multipliers should be re-validated when the first script-bearing skill is ported during migration Week 2.

## Estimated full port

Using a notional 30-min baseline for `read_wiki_page` (under prose-only strategy this is faster than the original 1.0× scripted assumption):

- Full port ≈ 30 min × 7.8 ≈ **~4 hours** of focused work
- Comfortably under the 4h-per-skill spike threshold; well within a Week-2 sprint

## Open design question for migration Week 2

Should the **write-bearing skills accept SCHEMA.md as a runtime dependency** (script reads `~/mneme/wiki/SCHEMA.md` and enforces frontmatter rules), or should schema enforcement live in a separate `mneme_wiki_lint` skill the agent invokes before commit? Defer the decision to when those skills are actually being ported.
