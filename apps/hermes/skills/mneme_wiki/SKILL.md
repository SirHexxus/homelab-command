---
name: mneme_wiki
description: Read and write pages in the Mnemosyne wiki — the user's canonical knowledge memory at $MNEME_WIKI_PATH. Covers all 7 operations (read page, read index, list bucket, scan inbox, write page, append log, commit + push). Reads use Hermes-Agent built-in tools; writes and git ops invoke code-enforced scripts.
version: 0.2.0
author: James Stacy (Migration Week 2 of the Hermes-Agent platform pivot)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Mnemosyne, Wiki, Markdown, Knowledge-Memory, Chiron, Migration-Week-2]
    related_skills: [obsidian]
---

# Mneme Wiki

This skill is how you read and write the **Mnemosyne wiki** — the user's canonical knowledge memory. The wiki is a git-backed Markdown vault organized into buckets (`ideas/`, `admin/`, `reference/`, `journal/`, `people/`, `projects/`, `pursuits/`, plus auxiliary `synthesis/`, `reports/`, `raw-sources/`, `inbox/`).

Two top-level files govern the vault: `SCHEMA.md` (the rules — read it before any write) and `index.md` (the catalog — every page has an entry).

## Wiki location

The wiki path is `$MNEME_WIKI_PATH`. Fallback if unset: `~/mneme/wiki`. On the production LXC the path is `/root/mneme/wiki`. Both scripts and prose-only operations resolve against this same root.

## The 7 operations

| Op | How to do it | Notes |
|----|--------------|-------|
| 1. Read a page | **Built-in `file.read`** against `$MNEME_WIKI_PATH/<relative_path>` | Or use `scripts/read_wiki_page.py <path>` as a fallback (preserved from Spike 4 for symmetry) |
| 2. Read the index | **Built-in `file.read`** against `$MNEME_WIKI_PATH/index.md` | Read it in full before deciding which pages to consult — it's the source of relevance |
| 3. List pages in a bucket | **Built-in `search_files`** / glob `*.md` under `$MNEME_WIKI_PATH/<bucket>/` | Bucket names match the directory names (`ideas`, `admin`, …) |
| 4. Scan the wiki inbox | **Built-in directory listing** of `$MNEME_WIKI_PATH/inbox/` | See "Two inboxes" below — this is the Obsidian Web Clipper drop zone, not the Telegram/n8n ingest path |
| 5. Write a page | `scripts/write_wiki_page.py <path> <content_file_or_->` | Script enforces path-traversal guard, parent-dir creation, UTF-8. `--dry-run` shows the write without performing it |
| 6. Append to log.md | `scripts/append_wiki_log.py <operation> <bucket> <title> <source>` | Script prepends ISO-8601 UTC timestamp and emits the canonical pipe-delimited line. See "log.md format" below |
| 7. Commit + push | `scripts/git_commit_push.py <message>` | Script handles `add → commit → pull --rebase → push` with filelock + retry. See "Concurrency" below |

## Schema awareness (operational subset of SCHEMA.md)

When writing, you are the **Custodian** of the wiki. Always read `SCHEMA.md` for the full rules. The minimum you must respect:

**Bucket → directory:**

| Bucket | Directory | What goes there |
|--------|-----------|-----------------|
| IDEA | `ideas/` | Subjective interpretations, questions, half-formed thoughts |
| ADMIN | `admin/` | Tasks, to-dos, reminders, anything with a due date or action required |
| REFERENCE | `reference/` | Objective, verifiable facts, sources, documentation |
| JOURNAL | `journal/` | Dated personal entries |
| PERSON | `people/` | People — contact info, relationship context |
| PROJECT | `projects/` | Bounded initiatives with a defined end state |
| PURSUIT | `pursuits/` | Long-running interests, no defined end |

**Default rule:** if IDEA vs REFERENCE is ambiguous, default to **IDEA**.

**Naming conventions:**

- IDEA / REFERENCE / PERSON: title case, descriptive
- ADMIN: action verb + object, title case (`Renew Ariadne SSL Cert.md`)
- JOURNAL: `YYYY-MM-DD.md` or `YYYY-MM-DD — Title.md`
- PROJECT: `Project - Title.md` (spaced hyphen, NOT a colon — colons are forbidden in Obsidian filenames even on Linux)
- PURSUIT: `Pursuit - Title.md`

**Forbidden characters in filenames:** `[ ] # ^ | * " \ / : < > ?` and leading `.`. Replace `:` with ` - ` (spaced hyphen); replace others with `-`; collapse consecutive hyphens. If sanitization changes the natural title, store the original in `title:` frontmatter.

**Required frontmatter (all pages):**

```yaml
---
bucket: IDEA          # IDEA | ADMIN | REFERENCE | JOURNAL | PERSON | PROJECT | PURSUIT
created: 2026-05-29   # ISO date
updated: 2026-05-29   # ISO date — update on every edit
source: claude_code   # telegram | email | web_clipper | n8n_chat | claude_code | manual
tags: []
---
```

Bucket-specific additions: see `SCHEMA.md` (ADMIN needs `due`/`status`/`recurrence`/`task_type`; ADMIN entries in `index.md` must include `[User]` or `[Maintenance]` at the start of the summary; PROJECT needs `status`/`next_action`/`deadline`; PURSUIT needs `current_milestone`/`next_milestone`/`last_active`; PERSON needs `relationship`/`last_contact`/`follow_up_*`; JOURNAL gets optional `mood`/`weather`; REFERENCE may carry `source_url`/`file_ref`).

**Wikilinks are mandatory.** Any reference to a named entity, concept, or page that has (or should have) its own wiki page MUST use `[[Page Title]]` syntax. Prose references are invisible to the Obsidian graph view. If a target page doesn't exist yet, create a stub — orphan wikilinks are worse than no link.

**index.md entry format:**

```
- [[Page Title]] | BUCKET | one-line summary (max 120 chars)
```

Entries are organized by bucket section; within a section, most-recent-first. ADMIN entries must lead with `[User]` or `[Maintenance]` so the agent can filter without opening pages.

**log.md format (pipe-delimited, single line per entry):**

```
{ISO-datetime} | {operation} | {bucket} | {page title} | {source}
```

`operation` is one of: `ingest | update | report | lint | merge`. Append-only — new entries go at the **end** of the file, never the top.

**Git commit convention** for every operation that modifies the wiki:

```
mneme: {operation} {bucket} — {page title}
```

Atomic — one logical operation per commit. Never batch unrelated ingests.

## Two inboxes — do not conflate

The system has two distinct "inboxes":

1. **`wiki/inbox/`** — a directory inside the wiki repo, used as a staging area for **Obsidian Web Clipper** captures. Items dropped here are processed by hand or by an audit script. Usually quiet (just `.gitkeep`). This is what `scan_wiki_inbox` (Op 4) lists.

2. **`inbox-receiver` LXC** — a separate FastAPI service at a separate IP that receives **Telegram + n8n** ingest payloads, runs `triage-inbox` / `enrich-stubs` cron scripts (at `infrastructure/mnemosyne/scripts/`), and writes pages directly into bucket directories. This is the active ingest path **during migration**. It will be retired in Week 4 when the full ingest pipeline moves to Hermes-Agent.

When the user says "the inbox," ask which one they mean if ambiguous. If they're asking you to look for unprocessed captures, default to the wiki inbox; if they're asking about a recent Telegram capture not yet visible, the answer is "still in flight through the receiver pipeline."

## Concurrency

The LXC wiki working copy at `/root/mneme/wiki` is **separate** from the laptop's Obsidian working copy. Two things follow:

1. **There is no auto-commit on the LXC.** Obsidian's Git plugin only runs on the laptop. After any writing session on the LXC, you MUST call `git_commit_push` (Op 7) or the work never reaches the remote.

2. **The race is at the remote.** Obsidian Git plugin pushes `mneme: vault sync <ts>` commits to the remote on a ~5 min cadence. A naive `git push` from the LXC right after a laptop push gets rejected as non-fast-forward. `git_commit_push.py` handles this with `git pull --rebase origin <branch>` before push, plus a single retry after 2s if the push is still rejected.

To minimize friction: **batch related writes into one commit**. Don't write the page, commit, append the log, commit again, then check something, commit again — write everything, append once, commit once.

The `filelock` inside the script (`.git/mnemosyne.lock`, 30s timeout) serializes concurrent **LXC** writers. It does nothing about the laptop. Today there's only one LXC writer (Haley); when Margot/Quinn come online and write in parallel, the lock starts earning its keep.

## When to use this skill

- The user asks you to read, summarize, write to, or update the wiki
- You need to ground a response in canonical project state (e.g., `[[Project - Hermes]]`, `[[Project - Mnemosyne]]`)
- You're filing an IDEA / REFERENCE / journal entry the user mentioned
- You're capturing an ADMIN task or updating its status
- The user references a wikilink (`[[Foo Bar]]`) — resolve it via the wiki

## When NOT to use this skill

- General filesystem reads / writes outside the wiki root — use the `file` toolset instead
- Anything inside the `inbox-receiver` LXC — that's a separate service with its own pipeline
- The MinIO bucket (`mnemosyne` at `10.0.50.16`) where binary source files live — that's its own surface

## Error codes

| Exit code | Meaning |
|-----------|---------|
| `0` | Success |
| `1` | Usage error (missing/invalid args) |
| `2` | Path not found (read/write target) |
| `3` | Path is a directory, not a page |
| `4` | Path escapes the wiki root (traversal blocked) |
| `5` | `$MNEME_WIKI_PATH` is unset and fallback `~/mneme/wiki` does not exist |
| `6` | Lock timeout (git ops only — another LXC writer is in progress) |
| `7` | Git command failed (commit/pull/push — stderr shows why) |
| other | Unexpected error; check stderr |

## Notes for future expansion

- A separate `mneme_wiki_lint` skill (read-only) is queued: walks the wiki, parses frontmatter against SCHEMA.md, reports violations. Use it before bulk-writing if you suspect drift.
- Margot, Quinn, Reese personas will join Haley. All four read/write the same wiki via this skill — there's no persona-scoped wiki view.
- The Layer 3 ingest work (Phase 1 candidate evaluation: Moondream, PaddleOCR, Trafilatura, Marker, etc.) will add `perception_*:` frontmatter fields once contract is stable. Update SKILL.md when that lands.
