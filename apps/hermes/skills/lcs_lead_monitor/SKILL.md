---
# ┌──────────────────────────────────────────────────────────────────────────┐
# │ INTENTIONALLY UNTRACKED — do not `git add` this directory.               │
# └──────────────────────────────────────────────────────────────────────────┘
#
# `homelab-command` is a PUBLIC repository. This skill contains client-
# confidential material that must not be published:
#
#   * Left Coast Scales named as a client, with their sales territory
#     (SoCal + Arizona, bleeding into Central CA and southern Nevada)
#   * "NV legal-for-trade registration is unconfirmed" — an internal
#     regulatory gap, in writing
#   * Commodity codes and portal keyword targeting — LCS's lead-gen strategy
#   * Internal revenue taxonomy (Stream 8 Mode 1) and staffing plan
#     (Haley now, Reese later)
#
# No credentials are hardcoded here (secrets come from env vars), so the risk
# is disclosure of client business information, not key leakage.
#
# A push is effectively permanent: history, forks, and caches survive deletion.
#
# Intended resolution (decided 2026-07-30): SPLIT this skill — publish the
# generic procurement-portal monitoring machinery, and keep territory.yml,
# commodity-codes.md, and the LCS-specific framing in a private repo
# (e.g. alongside lcs-current-customer-fe/be). Until that split is done,
# this directory stays untracked.
#
# Note: .gitignore does NOT exclude this directory — only the __pycache__
# inside it. Nothing but this notice prevents an accidental `git add`.
#
name: lcs_lead_monitor
description: >
  Monitor state/local procurement portals for capital-level scale-equipment
  opportunities in Left Coast Scales' territory, classify and score each one,
  and deliver a review-ready handoff memo to James via Telegram. James reviews
  every memo before anything goes to LCS. Implements Stream 8 Mode 1 (lead
  referral). Today Haley runs this; it is structured to hand off to Reese (the
  sales lane) when she comes into production.
version: 0.1.0
author: James Stacy (Stream 8 Mode 1 — LCS capital-equipment lead referral)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Stream-8, LCS, lead-referral, Hexxus-Weighment, procurement, Haley, Reese]
    related_skills: [mneme_wiki]
---

# LCS Lead Monitor

Watches procurement portals for capital-level scale-equipment RFPs in
[[Left Coast Scales]] territory, then surfaces the good ones to James as a
handoff memo he can review in ~5 minutes and forward to Jason.

This is **discovery + qualification + drafting**, never auto-forwarding.
Per the Stream 8 rule: **human approval on every LCS handoff.** The skill's job
is to make James's review fast and the memo trustworthy — not to make the
referral decision for him.

## Lane and persona

- **Today:** Haley runs this skill on a daily cron and delivers to James.
- **Later:** this is naturally a **Reese** skill (sales lane — "lead-gen
  activity, outreach drafts pending review"). When Reese is in production she
  takes ownership and writes her sub-report into the daily-digest fragment
  directory instead of (or in addition to) a standalone Telegram send. Build
  and read this skill with that handoff seam in mind; do not hard-code "Haley"
  into the memo voice in a way Reese would have to unpick.

## Division of labor (the load-bearing rule)

Mirror the `daily_digest` contract: **scripts fetch and move data; the agent
does judgment.**

| Step | Owner | How |
|------|-------|-----|
| Pull new alert emails | script | `scripts/fetch_alerts.py` (IMAP on `bids@hexxusweb.com`) |
| Extract fields, classify equipment, score bid-worthiness, decide territory tier, apply the NV LFT guard, draft the memo | **agent (Gemini)** | this SKILL.md is your instruction set |
| Dedupe + date sanity | script | `scripts/dedupe_store.py` |
| Deliver memo to Telegram | script | `scripts/deliver_memo.py` |
| Log to the pipeline tracking page | `mneme_wiki` scripts | `write_wiki_page.py` / `append_wiki_log.py` / `git_commit_push.py` |

If a fact can be computed deterministically (dedupe key, date math), it belongs
in a script, not in the model. The model never invents a fact that isn't in the
source alert — see "No fabrication."

## Daily run sequence

1. `python scripts/fetch_alerts.py` → JSON list of unseen alert emails
   `[{portal, subject, body, received, message_id, links[]}]`.
   If empty, exit quietly (no-filler rule — do not send "nothing today").
2. For each alert, **extract** the structured opportunity:
   `{agency, solicitation_number, title, equipment_guess, jurisdiction,
   close_date, est_value (if stated), source_url}`.
   Pull only what is present in the email/links. Missing field → `null`, never a guess.
3. Apply the **classification rubric** and the **territory matrix** below.
   Drop hard non-matches (see negative keywords in `reference/commodity-codes.md`).
4. `python scripts/dedupe_store.py --input <opps.json> --commit` → keeps only new,
   in-runway opportunities (drops already-seen and expired/too-soon).
5. For each surviving opportunity, assign a **bid-worthiness** tier and **draft
   the memo** in the format below.
6. `python scripts/deliver_memo.py --file <memo.md>` → Telegram to James
   (one message per opportunity; keep them individually forwardable).
7. Append each surfaced opportunity to the pipeline tracking page
   `reports/lcs-lead-pipeline.md` via the `mneme_wiki` skill, then commit:
   - `write_wiki_page.py "reports/lcs-lead-pipeline.md" <updated>`
   - `append_wiki_log.py report reports "LCS Lead Pipeline YYYY-MM-DD" claude_code`
   - `git_commit_push.py "mneme: report reports — LCS Lead Pipeline YYYY-MM-DD"`
   Wiki-commit failure is a soft fail (James already got the memo); log and continue.

## Territory matrix

Source of truth is `reference/territory.yml`. Summary:

- **Tier A — auto-surface.** SoCal counties (Imperial, Riverside, San Bernardino,
  San Diego, Orange, Los Angeles, Ventura, Santa Barbara, Kern) **+ all of Arizona.**
- **Tier B — surface, tag `stretch territory`.** Central California (Fresno,
  Tulare, Kings, Madera, Merced, and north toward Sacramento) **+ southern Nevada**
  (Clark County / Las Vegas / Henderson area).
- **Outside A and B:** do not surface. Log as `out-of-territory` only if it was a
  strong equipment match (useful for spotting where demand exceeds LCS's reach).

### NV legal-for-trade guard

LCS's Nevada legal-for-trade registration is **unconfirmed**. So:

- Any **Nevada** opportunity that is **commercial / legal-for-trade** — truck
  scales at points of sale, landfill/aggregate scales that bill by weight, DOT
  weigh stations, anything used to determine a price or enforce a regulation —
  gets the banner **`⚠️ VERIFY LCS NV LFT REGISTRATION`** at the top of the memo
  and a bid-worthiness ceiling of **Medium** until James confirms.
- Nevada **non-LFT / industrial / internal-process** weighing (process tanks,
  hoppers, internal QC) is **not** flagged — surface it normally.
- California and Arizona opportunities are never NV-flagged.

## Equipment scope

Capital-level, install-required equipment only (Mode 1):

- Truck / vehicle scales, weighbridges, axle / weigh-in-motion (WIM) scales
- Rail / track scales
- Tank scales, hopper scales, batching scales
- Large-capacity floor / platform scales (>2,000 lb, foundation-mounted)
- Any scale system requiring foundation work, structural/electrical integration,
  or legal-for-trade certification

Sub-capital bench/portable/lab scales: **for now, still surface to LCS** (per the
"hand all leads to LCS, prove volume first" decision) but tag `sub-capital` and
score no higher than Low. The classifier distinguishes them so Mode 2 can be
switched on later without rework.

## Classification rubric

For each opportunity decide:

1. **Equipment match** — does it map to a scope item above? Use the keyword and
   negative-keyword lists in `reference/commodity-codes.md`. The word "scale"
   alone is **not** a match (kill "large-scale", "scalable", "pay scale",
   "scale model", fish/dental scaling, "scale of the project").
2. **Territory tier** — A, B, or out (territory matrix).
3. **Capital vs sub-capital.**
4. **NV LFT flag** — apply the guard.
5. **Runway** — days until close. `dedupe_store.py` drops anything under the
   minimum runway; note tight runways (<14 days) in the memo.

## Bid-worthiness scoring

Assign **High / Medium / Low**:

- **High** — clear capital-level equipment match, Tier A, ≥14 days runway,
  install/LFT work that is squarely LCS's wheelhouse, est. value (if stated) ≥ $25k.
- **Medium** — capital match but Tier B, or NV-LFT-flagged, or runway 7–14 days,
  or value unstated/unclear.
- **Low** — sub-capital, marginal equipment match, or otherwise weak fit.

State the reason for the tier in one line. James overrides freely — the score
orders his review, it doesn't make his decision.

## Memo format

One Telegram message per opportunity. Plain text, individually forwardable.

```
[<BID-WORTHINESS>] <Equipment type> — <Agency>
<⚠️ VERIFY LCS NV LFT REGISTRATION  (only if NV LFT guard fired)>

Territory: <Tier A | Tier B (stretch) | out>   Jurisdiction: <county, state>
Solicitation: <number>          Closes: <YYYY-MM-DD> (<N> days)
Est. value: <$ or "not specified">
What it is: <1–2 sentence plain-language summary from the solicitation>
Why this tier: <one line>
Source: <canonical portal URL>
```

**Every memo must carry a working `Source:` link and the solicitation number.**
A memo without a verifiable source link is a defect — do not send it; log the
parse failure instead.

## No fabrication

The memo may contain only facts present in the alert email or the linked
solicitation. If capacity, value, or location is not stated, write
"not specified" — never infer. Summaries paraphrase the source; they do not
add specs, deadlines, or dollar figures the source didn't give. This is what
makes the `Source:` link meaningful and keeps James's trust in the pipeline.

## Outcome tracking

`reports/lcs-lead-pipeline.md` is the living record. Each row:
`date surfaced | equipment | agency | tier | status`. Status starts `surfaced`
and James (or a later skill) advances it: `forwarded → quoting → won/lost`.
This is both the success metric and the long-term accuracy feedback loop
(did the High-scored leads actually convert?).

## Environment

| Var | Purpose |
|-----|---------|
| `BIDS_IMAP_HOST` / `BIDS_IMAP_PORT` | IMAP server for `bids@hexxusweb.com` |
| `BIDS_IMAP_USER` / `BIDS_IMAP_PASS` | Credentials for the bids intake mailbox |
| `BIDS_IMAP_MAILBOX` | Mailbox/folder to read (default `INBOX`) |
| `GOOGLE_API_KEY` | Gemini (classification + memo drafting) |
| `HERMES_BIN` | Path to the `hermes` CLI (default `hermes`) |
| `HERMES_SEND_TARGET` | Telegram target (default `telegram:James`) |
| `LCS_LEAD_STORE` | Dedupe store path (default `~/.cache/hermes/lcs_lead_store.json`) |
| `MNEME_WIKI_PATH` | Wiki working copy for the tracking page |

All provisioned by Ansible on the LXC at deploy time (Week 1), the same way
`daily_digest` env is provisioned. The bids mailbox is a **dedicated data
intake** — distinct from Haley's own identity mailbox (`haley.chiron@…`); the
skill reads `bids@` directly and does not need Haley's mailbox.

## Failure modes

| Symptom | Likely cause |
|---------|--------------|
| No alerts ever arrive | Portal vendor alerts not yet configured, or IMAP creds wrong / mailbox empty. Verify a test alert lands in `bids@` first. |
| Flood of false positives | Negative-keyword list too weak — this is expected in calibration weeks; feed James's 👎 labels back into `reference/commodity-codes.md`. |
| Same RFP sent twice | Dedupe key drift (agency/solicitation formatting). Normalize before keying. |
| Memo missing Source link | Parse failure — suppress the memo, log it, do not send a linkless memo. |

## When to use

- Cron-triggered daily — the canonical use.
- On demand: "Haley, run the LCS bid sweep" — same sequence, immediate.

## When NOT to use

- To forward anything to LCS automatically — never. James reviews every memo.
- General procurement questions unrelated to scale equipment — out of scope.
- Federal SAM.gov bidding — explicitly cut (Stream 8). SAM.gov may later be added
  as a discovery-only source (James never bids; hand-offs go to LCS), but that is
  not in this scaffold.
