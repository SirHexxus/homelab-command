# Mnemosyne: Design Thinking & Open Questions

This file captures architectural thinking, design decisions, and open questions specific to
the Mnemosyne project — things that should inform implementation but aren't task items. It
is a living document, not a spec.

---

## Telegram Is Both the User Interface and the Ingestion Channel

Telegram serves two distinct roles for Mnemosyne, and the bot interface must handle both:

1. **Ingestion endpoint** — the user sends notes, voice memos, and files; the system
   processes them into the wiki
2. **Retrieval and delivery channel** — the system sends reports, answers queries, and
   confirms successful saves

This creates an important routing decision at the bot level: every incoming message must
be classified as either a **capture** (process and store) or a **command** (retrieve or
act). The logic:

- Slash commands (`/ask`, `/search`, `/find`, `/project`, `/pursuit`, `/remind`, `/lint`)
  → retrieval or maintenance path
- Everything else → ingestion path (with clarification if bucket ambiguity is high)

### Stateful multi-turn conversations are required

The bot must support multi-turn interactions for:
- Disambiguation: "This looks like it could be IDEA or REFERENCE — which is it?" →
  user replies → merge context + re-classify
- Entity confirmation: "This looks like it's about Marcus Chen. Add to existing entry?" →
  user replies Yes/No/New
- Bulk clarification for notes with multiple items

Multi-turn requires session state persisted in Redis (key: `session:{chat_id}`, TTL ~10 min).
**Design the bot for stateful multi-turn from the start**, even if the first implementation
only uses single turns. Retrofitting session state into a stateless bot is messier than
designing for it up front.

### Clarification timeout behavior

When the bot asks a clarification question and the user doesn't reply:
- Wait 10 minutes
- Default to IDEA bucket (the safest fallback — IDEAs are the most forggiving
  misclassification from a retrieval standpoint)
- Notify user: "No reply received — saved as IDEA. Use /find to correct if needed."

The 10-minute timeout is implemented as a Redis TTL on the pending session key. When n8n
(or Hermes) checks for a pending session and finds it expired, it applies the default.

### Report delivery design

Scheduled reports (Daily Digest, Serendipity Engine, Weekly Summary, etc.) are delivered
via Telegram as formatted messages. A few constraints to design around:

- **Telegram message length limit: 4096 characters.** Long reports must be split across
  multiple messages or truncated with a "full report in Obsidian" pointer.
- **Formatting:** Telegram supports MarkdownV2 for bold, italics, and code. Reports should
  use this for readability, but Hermes must escape special characters correctly.
- **Delivery timing:** Reports are n8n cron triggers → Hermes generates → n8n sends.
  If report generation takes >30 seconds (large wiki, complex synthesis), consider async:
  n8n triggers, Hermes generates in background, notifies when complete.

---

## The IDEA / REFERENCE Boundary Is the Highest-Risk Classification Edge

This was identified in the original design doc and remains true in the wiki model. The
distinction:
- **IDEA** — subjective, yours, your interpretation or question about a thing
- **REFERENCE** — objective, external, verifiable fact or source

Edge cases that are genuinely ambiguous:
- A half-formed thought about a verifiable fact ("I think TypeScript adoption is slowing")
- A question about a concrete thing ("what is the current Proxmox version?")
- An insight drawn from reading a source ("nomic-embed-text seems better than ada for
  this use case" — is this an IDEA or a REFERENCE note?)

**Classification rule:** When confidence at this specific boundary is below threshold,
**always ask** rather than guess. A misclassification here doesn't lose data (it's always
in the wiki), but it degrades retrieval quality and breaks the mental model.

**Default rule:** If something cannot be cleanly resolved between IDEA and REFERENCE even
after asking — or if the user declines to clarify — default to IDEA. IDEA is the safer
misclassification: a subjective framing of an objective fact is less disorienting to
retrieve than an objective fact filed as a personal insight. When in doubt, it's yours.

The SCHEMA.md must include worked examples of IDEA vs. REFERENCE edge cases for the LLM
classifier, including the explicit default-to-IDEA rule. This is the most important section
of the schema.

---

## The Index File Is Load-Bearing Infrastructure

`index.md` is how Hermes navigates the wiki on every operation. It is the substitute for
embedding-based retrieval at this scale. Some design decisions to get right early:

**Entry format must be compact and consistent.** Suggested format:
```
- [[Page Title]] | BUCKET | one-line summary (max 120 chars)
```
If entries are verbose, `index.md` grows large fast and starts consuming significant tokens
on every LLM call. The 120-character summary limit is a SCHEMA.md requirement, not a
guideline.

**The index must be organized by bucket, not chronologically.** Flat chronological indexes
become impossible to navigate quickly. Suggested structure:
```markdown
## People
- [[Marcus Chen]] | PERSON | Software engineer, homelab friend, last contact 2026-03
...

## Projects
- [[Project: Homelab Phase 2]] | PROJECT | Active — deploying media stack
...

## Ideas
- [[On ADHD and systems]] | IDEA | Reflection on friction and executive function
...
```

**The index is not a substitute for the log.** `index.md` is a catalog of what exists.
`log.md` is a record of what happened and when. They answer different questions. The
LLM must update both correctly on every ingest.

**Index size monitoring.** At ~100 pages, `index.md` is ~15KB — trivially small. At ~500
pages with compact entries, it's ~75KB. At ~1,000 pages it starts to matter in context
windows. Plan to implement a tiered or categorized index structure before hitting 500 pages,
not after. This is a SCHEMA.md evolution concern, not an immediate implementation concern.

---

## YAML Frontmatter Is the Structured Data Layer

In the wiki model, YAML frontmatter replaces the Postgres `metadata JSONB` field. Every
wiki page should have frontmatter. The LLM must write it consistently.

Minimum required frontmatter for each bucket:

```yaml
# All pages
---
bucket: IDEA
created: 2026-04-10
updated: 2026-04-10
source: telegram
---

# ADMIN additions
due: 2026-04-15
status: Pending   # Pending | Done
recurrence: null  # weekly | monthly | null

# PERSON additions
relationship: friend | colleague | professional | family
last_contact: 2026-03-15
follow_up_needed: true
follow_up_date: 2026-04-20

# PROJECT additions
status: Active    # Not Started | Active | Blocked | Done
next_action: "Write the SCHEMA.md"
deadline: null

# PURSUIT additions
current_milestone: "Phase 1 complete"
next_milestone: "Deploy Hermes"
```

Obsidian's Dataview plugin can query this frontmatter to produce dynamic tables — e.g., all
ADMIN items due this week, all PERSON entries with `follow_up_needed: true`. This is the
replacement for the structured Postgres queries in the original design.

The LLM must be instructed in SCHEMA.md to always write frontmatter and to use exact field
names. Inconsistent field names (`due_date` vs `due`, `followup_needed` vs `follow_up_needed`)
will break Dataview queries silently.

---

## The Wiki Model vs. The Original Design: What Changed and Why

For future reference, a summary of the architectural pivot:

| Dimension | Original Design | Wiki Model |
|-----------|----------------|------------|
| Primary store | Postgres (pgvector) | Git repo of markdown files |
| Retrieval | Vector similarity search | index.md + LLM reads pages |
| Entity resolution | Confidence-scored n8n workflow | LLM reads entity page, updates it |
| UI | Notion (sync'd from Postgres) | Obsidian (reads git repo directly) |
| Ingest pipeline | ~15-node n8n workflow | Classify → Hermes integrates |
| Embedding | nomic-embed-text (all content) | Not required (index.md navigation) |
| Knowledge growth | Retrieval-time RAG | Ingest-time synthesis (compounding) |
| Human-readable | Only via Notion UI | Always — it's just markdown |

**Why the pivot is correct:**  
The original design optimized for retrieval (pgvector similarity search) at the cost of
significant infrastructure complexity and a Notion dependency. The wiki model optimizes for
*compounding knowledge* — each new note makes the wiki richer, not just bigger. For an ADHD
capture system where the goal is to reduce friction and increase discoverability, ingest-time
synthesis ("the connections are already there when you look") is a fundamentally better fit
than retrieval-time reconstruction ("find the right fragments and assemble them on demand").

The retrieval quality of a well-maintained wiki plus a capable LLM equals or exceeds the
retrieval quality of a pgvector index for the scale and use case this system will operate at.

---

## Obsidian Graph View Requires Consistent Wikilink Syntax

The graph view — one of the primary reasons Obsidian was chosen over Notion — only shows
connections that exist as `[[wikilinks]]` in the markdown files. A sentence like "this
relates to Marcus Chen's work" does not appear in the graph. `[[Marcus Chen]]` does.

**This is a SCHEMA.md requirement:** The LLM must be explicitly instructed to use
`[[wikilink]]` syntax when referencing any entity or concept that has (or should have) its
own page. Prose references without brackets are invisible to the graph.

Consequence: the graph view is only as good as the LLM's adherence to the wikilink
convention. The lint flow (checking for prose references that should be links) is an
important long-term maintenance step.

---

*See `ToDo.md` for the actionable task list. This document is context and thinking, not tasks.*
