# Case Studies and Lessons Learned

Blameless reviews of things that went wrong in this homelab, or nearly did: what happened, how it was found and fixed, why it happened, and what changed afterwards. Each review ends with its lessons, and the ones worth carrying forward are collected below.

---

## Case Studies

| Date | Case study | Summary |
|------|------------|---------|
| 2026-09-29 | [Secrets Committed to a Public IaC Repository](2026-09-29-leaked-secrets-in-public-repo.md) | Credentials in public git history for seven months: detection, same-day containment, verified rotation, and a history rewrite |

---

## Lessons Learned

Lessons that apply beyond the incident they came from. Each links to its source.

| Lesson | Source |
|--------|--------|
| A control that depends on memory fails silently. Put the rule in a hook, not a comment. | [2026-09-29](2026-09-29-leaked-secrets-in-public-repo.md#lessons) |
| `.gitignore` protects the future, never the past. Pair each ignore rule with `git rm --cached` and a check that nothing matching it is still tracked. | [2026-09-29](2026-09-29-leaked-secrets-in-public-repo.md#lessons) |
| Deleting a secret in the next commit still publishes it. Rotation is the only real fix; rewriting history only limits who can find it later. | [2026-09-29](2026-09-29-leaked-secrets-in-public-repo.md#lessons) |
| "I changed the password" is a fact only once the old one is shown to fail. | [2026-09-29](2026-09-29-leaked-secrets-in-public-repo.md#lessons) |
| During incident response, prefer a narrow, tagged task over an idempotent everything-playbook. | [2026-09-29](2026-09-29-leaked-secrets-in-public-repo.md#lessons) |

---

## Writing a New Case Study

- Name the file `YYYY-MM-DD-short-description.md` and add it to both tables above.
- Keep it blameless: describe systems and decisions, not fault.
- Never include secret values, current credentials, or public addresses. Describe the shape of anything sensitive, not its content.
- Suggested sections: Summary, Impact, Timeline, Detection, Response, Root Causes, What Went Well, What Went Poorly, Corrective Actions, Lessons.
