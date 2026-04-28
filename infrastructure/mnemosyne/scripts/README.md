# Mnemosyne Maintenance Scripts

Housekeeping scripts for the Mnemosyne wiki. All scripts are read-only
(no wiki content is modified). Reports are written to `wiki/reports/` and
logged to `wiki/log.md`.

## Structure

```
scripts/
├── lib/
│   └── wiki-common.sh       # Shared functions; source, do not execute
└── maintenance/
    ├── check-ghost-links          # daily   — bash + optional haiku
    ├── check-index-completeness   # daily   — bash only
    ├── check-overdue-tasks        # daily   — bash only
    ├── check-person-followups     # daily   — bash only
    ├── check-inbox-drain          # daily   — bash only
    ├── check-frontmatter-types    # weekly  — bash only
    ├── check-updated-drift        # weekly  — bash only
    ├── check-log-coverage         # weekly  — bash only
    ├── check-orphan-files         # weekly  — bash + optional sonnet-4-6
    ├── audit-required-fields      # weekly  — bash + optional haiku-4-5
    ├── check-stub-pages           # weekly  — bash + optional haiku-4-5
    └── triage-stale-projects      # weekly  — bash + optional haiku-4-5
```

## Usage

All scripts write a Markdown report to `wiki/reports/` only when issues
are found. A clean run logs to stderr and exits 0 without writing a file.

```bash
# Run any script directly
./maintenance/check-ghost-links
./maintenance/check-overdue-tasks

# Run with LLM enrichment (suggestions/summaries appended to report)
./maintenance/check-ghost-links --enrich
./maintenance/check-orphan-files --enrich
./maintenance/audit-required-fields --enrich
./maintenance/check-stub-pages --enrich
./maintenance/triage-stale-projects --enrich
```

## Model Choices for --enrich

| Script                  | Model        | Reason                              |
|-------------------------|--------------|-------------------------------------|
| check-ghost-links       | haiku-4-5    | Fuzzy filename matching             |
| check-orphan-files      | sonnet-4-6   | Wiki-wide relational reasoning      |
| audit-required-fields   | haiku-4-5    | Field classification from content   |
| check-stub-pages        | haiku-4-5    | Binary judgment + brief suggestion  |
| triage-stale-projects   | haiku-4-5    | Summarization of short content      |

## Cron Schedule (suggested)

```cron
# Daily — fast, no LLM cost
0 7 * * * /path/to/scripts/maintenance/check-ghost-links
0 7 * * * /path/to/scripts/maintenance/check-index-completeness
0 7 * * * /path/to/scripts/maintenance/check-overdue-tasks
0 7 * * * /path/to/scripts/maintenance/check-person-followups
0 7 * * * /path/to/scripts/maintenance/check-inbox-drain

# Weekly Sunday — bash only
0 8 * * 0 /path/to/scripts/maintenance/check-frontmatter-types
0 8 * * 0 /path/to/scripts/maintenance/check-updated-drift
0 8 * * 0 /path/to/scripts/maintenance/check-log-coverage

# Weekly Sunday — with LLM enrichment
0 9 * * 0 /path/to/scripts/maintenance/check-orphan-files --enrich
0 9 * * 0 /path/to/scripts/maintenance/audit-required-fields --enrich
0 9 * * 0 /path/to/scripts/maintenance/check-stub-pages --enrich
0 9 * * 0 /path/to/scripts/maintenance/triage-stale-projects --enrich
```

## Dependencies

- `bash` 4.0+ (associative arrays, `${var^}` case expansion)
- `git` (for check-updated-drift, triage-stale-projects)
- `date` GNU coreutils (for date arithmetic)
- `claude` CLI (only for `--enrich` mode)
