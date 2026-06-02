---
name: daily_digest
description: Compile and deliver the morning daily digest. Haley owns the personal lane (schedule, weight check, important dates, weather, recent capture activity); Margot/Quinn/Reese will hand off voiced sub-reports here once they are in production. Output is a wiki-committed report page plus a Telegram text message and a Gemini-TTS voice note (Leda).
version: 0.1.0
author: James Stacy (Migration Week 3 of the Hermes-Agent platform pivot)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Mnemosyne, Daily-Digest, Chiron, Migration-Week-3, Haley]
    related_skills: [mneme_wiki]
---

# Daily Digest

Run by Hermes-Agent cron at 7am every day. The user (James) wakes up to one Telegram message + voice note from `@HaleyChironBot`. The digest is **Haley's morning report**: schedule, weight check, important dates, weather, plus a short "yesterday in capture" reflection drawn from the wiki log.

Other personas will produce their own sub-reports as they come online — see "Persona handoff seam" below. Today, only Haley is in production.

## Lane scope (Week 3)

Cover, in this order:

1. **Greeting + temporal anchor** — date, weekday, weather one-liner.
2. **Today on the calendar** — events from `fetch_calendar.py`, in chronological order.
3. **Weight check** — most recent entry from `lookup_weight_log.py`. If yesterday was missed, gently nudge (don't lecture).
4. **Important dates inside the lookahead window** — birthdays, anniversaries, ADMIN-due-soon from `lookup_important_dates.py`.
5. **Yesterday in capture (one sentence)** — quick reflection on `log.md` activity from yesterday, if anything was captured. Skip if quiet.
6. **Closer** — Haley's own.

**No-filler rule (inherited from the laptop digest):** if a section has no content, omit it silently. Don't say "no events today" or "no birthdays this week" — empty sections are invisible.

## Persona handoff seam (Weeks 5+, when other personas come online)

The digest is structured so Haley compiles and narrates contributions from her teammates:

- **Margot** (professional lane) — ops/research summary; deeper work-project status.
- **Quinn** (security lane) — overnight alerts, anomalies, escalations.
- **Reese** (sales lane, reports to Margot) — lead-gen activity, outreach drafts pending review.

When a teammate persona is in production, it writes its own short voiced sub-report to `~/mneme/wiki/reports/daily-digest-fragments/<date>-<persona>.md` on its own schedule (any time before 7am). At digest time, Haley reads this directory, pulls the fragments that exist for today, and threads them into her own narrative — quoting the teammate's voice in the text, then attaching their voice note as a follow-up Telegram message after her own.

**Today:** the fragments directory does not yet exist and `lookup_important_dates.py`/`lookup_weight_log.py` cover Haley's lane only. Do not invent fragments or fake the other personas' voices.

## How to assemble the digest

The agent is responsible for **compilation + narration**, not data fetching. Use the scripts in `scripts/` to pull data; assemble the narrative; render to voice; deliver.

Standard sequence:

1. `python scripts/fetch_calendar.py` → JSON list of today's events.
2. `python scripts/fetch_weather.py` → JSON weather block.
3. `python scripts/lookup_weight_log.py` → JSON `{last_entry: {date, weight, notes}, nudge: bool, gap_days: int}`.
4. `python scripts/lookup_important_dates.py --lookahead 30` → JSON list of birthdays / anniversaries / ADMIN due in the window.
5. **Compose the digest text** in Haley's voice, lane scope above, no-filler rule, ≤ 220 words for the spoken portion (TTS gets long otherwise).
6. Write the compiled text to a temp file (e.g. `/tmp/digest-YYYY-MM-DD.md`) — frontmatter included; format below.
7. Render voice: `python scripts/render_voice.py --input /tmp/digest-YYYY-MM-DD.md --output /tmp/digest-YYYY-MM-DD.ogg`.
8. Deliver: `python scripts/deliver_digest.py --text /tmp/digest-YYYY-MM-DD.md --voice /tmp/digest-YYYY-MM-DD.ogg`.
9. Commit to the wiki using the `mneme_wiki` skill:
   - `write_wiki_page.py "reports/daily-digest-YYYY-MM-DD.md" /tmp/digest-YYYY-MM-DD.md`
   - `append_wiki_log.py report reports "Daily Digest YYYY-MM-DD" claude_code`
   - `git_commit_push.py "mneme: report reports — Daily Digest YYYY-MM-DD"`

One atomic commit per digest. If `deliver_digest.py` succeeds but `git_commit_push.py` fails, that is a known soft-fail — the user got the digest, the wiki missed an entry. Log the failure, continue. The reverse (commit succeeded, delivery failed) is a hard fail — exit non-zero so the cron entry surfaces it.

## Digest page format

The compiled file (input to step 6 above) is a normal wiki REPORT page. Frontmatter:

```yaml
---
bucket: REPORT
created: 2026-05-29
updated: 2026-05-29
source: claude_code
tags: [daily-digest, haley]
report_date: 2026-05-29
report_type: daily_digest
persona: haley
---
```

Body is Haley's narrative in plain prose (no headings, no bullets — this is what the TTS will read). Wikilinks are allowed and encouraged where they reference real pages (`[[Emily Aeryn Olsen]]`, `[[Weight Log]]`, `[[Project - Mnemosyne]]`); the TTS strips the brackets cleanly.

## Voice rendering

Voice is **Leda** (Gemini TTS, `gemini-2.5-flash-preview-tts`). `render_voice.py` calls the Gemini API directly, decodes the returned PCM, encodes via `ffmpeg` to OGG/Opus at 32kbps mono, returns the output path on stdout.

Keep the spoken portion under ~220 words so the voice note is digestible on the morning commute. Long-form wiki output goes in the page; the voice gets the headline.

## Delivery

`deliver_digest.py` does two Telegram sends:

1. Text message via `hermes send --to telegram:James --file <text>`.
2. Voice note via direct Telegram Bot API `sendVoice` call (Hermes-Agent gateway has no voice attachment surface). Token + chat_id read from env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_HOME_CHANNEL`.

Both must succeed for non-zero exit to be avoided. Order: text first, voice second — if the voice fails, the user still has the text.

## Environment

The cron entry (configured via `hermes cron create`, codified in Ansible) must export:

| Var | Purpose |
|-----|---------|
| `GOOGLE_API_KEY` | Gemini chat + TTS. Same key, dual use. |
| `TELEGRAM_BOT_TOKEN` | Voice delivery via Bot API. |
| `TELEGRAM_HOME_CHANNEL` | Chat ID for the home target (James). |
| `OPENWEATHER_API_KEY` | Weather block. |
| `WEATHER_LAT`, `WEATHER_LON` | Location for the weather query. |
| `GCAL_CREDS_PATH` | Path to Google Calendar refresh-token JSON (default `/etc/hermes-agent/gcal-creds.json`). |
| `GCAL_CLIENT_PATH` | Path to OAuth client JSON (default `/etc/hermes-agent/gcal-client.json`). |
| `GCAL_CALENDAR_IDS` | Comma-separated calendar IDs to fetch. |
| `MNEME_WIKI_PATH` | Wiki working copy (default `/root/mneme/wiki` on LXC). |

All of these are provisioned by `infrastructure/hermes/ansible/roles/hermes_agent/` on the LXC.

## When to use this skill

- Cron-triggered at 7am — the canonical use.
- On-demand: the user types "Haley, give me the morning brief" — produces the same digest immediately (no calendar-day check). Skip `git_commit_push` on on-demand runs to avoid duplicate REPORT pages for the same day.

## When NOT to use this skill

- Ad-hoc questions about the wiki — use `mneme_wiki` directly.
- The user asks for an evening or weekly summary — those are separate skills (not yet built).
- Sub-report from another persona — those personas use their own skills and write fragments; this skill only consumes fragments, never produces them.

## Failure modes

| Symptom | Most likely cause |
|---------|------------------|
| Calendar block missing | OAuth refresh token expired (check `~/mneme/digest.log` on laptop for matching error during parallel-rail period); or `GCAL_CALENDAR_IDS` empty. |
| Weather block missing | `OPENWEATHER_API_KEY` unset or the OpenWeather One Call subscription lapsed. Script falls back to 2.5 silently — if both fail, block is omitted (no-filler rule). |
| Voice note shorter than text | `render_voice.py` truncated input; check the model's MAX_INPUT_CHARS guard. |
| Delivery succeeded but no wiki commit | `git_commit_push.py` race or lock timeout (concurrent writer). Soft-fail. Re-run later. |
| Empty digest text | All collectors returned nothing AND the agent decided to skip everything — usually a calendar-empty + weight-current + no-birthdays Saturday. Render at least the greeting + weather. |

## Notes for future expansion

- Sub-report aggregation lands in Weeks 5-7 (see persona handoff seam above).
- Multi-voice TTS rendering (Haley narrating + clipped Margot/Quinn quotes in their own voices) is Week 7's explicit deliverable.
- Cost tracking: token usage from Gemini chat is reported in the agent run summary; TTS cost is not currently logged — add a hook if monthly Gemini spend trends past $15.
- The 7am laptop cron (`infrastructure/mnemosyne/scripts/daily-digest`) runs in parallel through the reliability-rail window (7 consecutive clean Hermes-Agent digests). Two voice notes per morning are expected until cutover.
