# Daily Digest Prompts

Externalised prompt files for the `daily-digest` script. Pulled out of the
Python source so the voice, structure, and rules can be edited (or A/B tested)
without touching code.

## Files

| File | Role | Sent to Gemini as |
|------|------|-------------------|
| `daily-digest-system.md` | Voice, structure, rules, omission contract | `system_instruction` (timeless) |
| `daily-digest-user.md`   | Per-run input template with placeholders   | user prompt (changes daily)    |

The split mirrors the `google-generativeai` SDK pattern that Hermes uses: the
timeless half goes to `system_instruction=` on the model, the per-run half is
the actual `generate_content()` argument.

## Placeholders (user template only)

`daily-digest-user.md` is run through Python's `str.format()` at runtime. Every
placeholder below must be present; the script fills them all.

| Placeholder         | Source in script                       |
|---------------------|----------------------------------------|
| `{temporal_anchors}`| `format_temporal_anchors(...)`         |
| `{obligations}`     | `format_obligations(...)`              |
| `{forward_prep}`    | `format_forward_prep(...)`             |
| `{unfinished}`      | `format_unfinished(...)`               |
| `{stale_relevant}`  | `format_stale_relevant(None)`          |
| `{yesterday_log}`   | `format_yesterday_log(...)`            |
| `{yesterday}`       | `(today - 1).isoformat()`              |

The system file has **no placeholders** — `str.format()` is not called on it,
so curly braces in the system text are safe.

## Sentinel token

Empty sections are passed in as the literal token `[[OMIT_SECTION]]`. The
system prompt instructs Gemini to silently drop any section whose body is this
token, and to never echo the token itself. Do not change the spelling without
updating both the system prompt and the `OMIT` constant in `daily-digest`.

## A/B testing

The script accepts two override flags:

```
daily-digest --system-prompt /path/to/alt-system.md
daily-digest --user-prompt   /path/to/alt-user.md
```

Both default to the files in this directory. Use them to run a variant prompt
against the same day's inputs (typically with `--no-send` to keep the
experiment out of Telegram and the wiki report path).

Suggested workflow for an A/B run:

1. Copy `daily-digest-system.md` to e.g. `daily-digest-system-shorter.md` and
   edit the copy.
2. Run the baseline: `daily-digest --no-send > /tmp/baseline.txt`
3. Run the variant: `daily-digest --no-send --system-prompt prompts/daily-digest-system-shorter.md > /tmp/variant.txt`
4. Diff or read both, decide which to keep, delete the loser.

There is no committed naming convention for variants — keep them out of git
unless you are promoting one to the default.

## Editing notes

- Both files are loaded once per run, at the top of `main()`. No restart or
  reload mechanism is needed; the next cron tick picks up edits automatically.
- Keep the system file in plain text. Markdown headers (`#`, `##`) inside the
  system prompt are fine for human readability but the file is passed
  verbatim to Gemini — so anything you write here, Gemini will see. The
  prompt already tells the model not to emit Markdown; do not put model-facing
  examples of Markdown formatting in the file beyond the existing "Wrong vs.
  Correct" pair.
- The `== HEADING ==` style inside `daily-digest-system.md` is a convention,
  not a requirement. It exists to make the file readable while not biasing
  Gemini toward Markdown headers.
