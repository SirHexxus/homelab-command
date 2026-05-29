---
name: mneme_wiki
description: Read pages from the Mnemosyne wiki — the user's canonical knowledge memory at $MNEME_WIKI_PATH. Spike 4 port of read_wiki_page from Homegrown-Hermes wiki.py. Read-only; write/append/git operations are separate skills queued for migration.
version: 0.1.0
author: James Stacy (port via Path C scaffolding by Claude)
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Mnemosyne, Wiki, Markdown, Knowledge-Memory, Chiron, Spike-4]
    related_skills: [obsidian]
---

# Mneme Wiki — Read

Use this skill to read a page from the Mnemosyne wiki. The wiki is a git-backed Markdown knowledge base; **the user's canonical knowledge memory.** Pages are organized by bucket (e.g. `projects/`, `ideas/`, `journal/`, `admin/`, `reference/`, `people/`, `pursuits/`).

## Wiki location

The wiki path is `$MNEME_WIKI_PATH` from `~/.hermes/.env`. If unset, the fallback is `~/mneme/wiki`. The script resolves this and refuses to read anything outside the wiki root (path-traversal guard).

## When to use

- The user asks you to read, summarize, or reference a wiki page
- You need to ground a response in canonical project state (e.g. `[[Project - Hermes]]`)
- You need to look up a known reference (e.g. `[[Mnemosyne TTS Voice Personas]]`)

## When NOT to use

- Writing or modifying pages — there is no write surface in this skill yet. The user's homegrown `wiki.py` had 6 more skills (write, append-log, list-bucket, scan-inbox, read-index, git-commit-push) that are queued for migration but not present here.
- General filesystem reads outside the wiki — use the `file` toolset instead.

## Workflow

1. Resolve the page path. The user may refer to a page by:
   - Relative path with extension (`projects/Project - Hermes.md`)
   - Wikilink syntax (`[[Project - Hermes]]`) — strip brackets, search for the file in the wiki
   - Just a title — search the wiki for a matching filename
2. Run [scripts/read_wiki_page.py](./scripts/read_wiki_page.py) with the relative path.
3. Present the content to the user. For long pages, summarize and offer to fetch more detail.

## Errors the script surfaces

| Exit code | Meaning |
|-----------|---------|
| `0` | success; page content on stdout |
| `2` | path not found — page does not exist |
| `3` | path is a directory, not a page |
| `4` | path escapes the wiki root (traversal attempt or absolute path) |
| `5` | `$MNEME_WIKI_PATH` is unset and fallback `~/mneme/wiki` does not exist |
| other non-zero | unexpected error; check stderr |

## Notes for future expansion

This is Spike 4's port of one skill (`read_wiki_page`). During migration Week 2 the remaining 6 skills join this folder. They share:

- The same `$MNEME_WIKI_PATH` resolution
- The same path-traversal guard
- `git_commit_push` will additionally hold `~/mneme/wiki/.git/mnemosyne.lock` (filelock) to serialize concurrent commits
