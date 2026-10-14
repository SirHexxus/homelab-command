"""Tests for the migrate-admin-priority script's pure helpers.

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "maintenance" / "migrate-admin-priority"
_LOADER = importlib.machinery.SourceFileLoader("migrate_admin_priority", str(_SCRIPT))
_SPEC = importlib.util.spec_from_loader("migrate_admin_priority", _LOADER)
mig = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(mig)

TODAY = "2026-10-13"
PAGE = """---
bucket: ADMIN
created: 2026-06-01
updated: 2026-06-01
due: 2026-07-01
status: Pending
task_type: user
priority: medium
---

# Do The Thing

Body text.
"""


class ParseProposalTests(unittest.TestCase):
    def test_valid_reply_in_a_fence(self) -> None:
        raw = ('```json\n{"urgency": "high", "impact": "LOW", "due_verdict": "drop", '
               '"due_anchor": "ignored", "action": "keep", "reason": "Self-set."}\n```')
        got = mig.parse_proposal(raw, has_due=True)
        self.assertEqual((got["urgency"], got["impact"], got["priority"]),
                         ("HIGH", "LOW", "MEDIUM"))
        self.assertEqual(got["due_verdict"], "drop")
        self.assertIsNone(got["due_anchor"])

    def test_verdict_forced_null_without_due(self) -> None:
        raw = ('{"urgency": "MEDIUM", "impact": "MEDIUM", "due_verdict": "keep", '
               '"due_anchor": "x", "action": "cancel", "reason": "r"}')
        got = mig.parse_proposal(raw, has_due=False)
        self.assertIsNone(got["due_verdict"])
        self.assertIsNone(got["due_anchor"])

    def test_missing_verdict_on_dated_task_is_rejected(self) -> None:
        raw = ('{"urgency": "MEDIUM", "impact": "MEDIUM", "due_verdict": null, '
               '"action": "keep", "reason": "r"}')
        with self.assertRaises(ValueError):
            mig.parse_proposal(raw, has_due=True)

    def test_bad_level_and_action_rejected(self) -> None:
        with self.assertRaises(ValueError):
            mig.parse_proposal('{"urgency": "URGENT", "impact": "LOW", "action": "keep"}', False)
        with self.assertRaises(ValueError):
            mig.parse_proposal('{"urgency": "LOW", "impact": "LOW", "action": "defer"}', False)
        with self.assertRaises(ValueError):
            mig.parse_proposal("not json", False)


class IndexTests(unittest.TestCase):
    def test_strips_status_and_dropped_due(self) -> None:
        self.assertEqual(
            mig.normalize_index_summary("[User] Pending due 2026-07-01 — call the bank\n", None),
            "[User] call the bank\n")

    def test_keeps_real_due_after_tag(self) -> None:
        self.assertEqual(
            mig.normalize_index_summary("[User] Pending — renew passport", "2026-11-02"),
            "[User] due 2026-11-02 — renew passport")

    def test_leaves_status_like_words_in_prose(self) -> None:
        self.assertEqual(
            mig.normalize_index_summary("[Maintenance] Active Directory notes", None),
            "[Maintenance] Active Directory notes")

    def test_untagged_summary_unchanged(self) -> None:
        self.assertEqual(mig.normalize_index_summary("Pending — x", None), "Pending — x")

    def test_rewrite_index_only_touches_listed_titles(self) -> None:
        index = ("- [[A]] | ADMIN | [User] Pending due 2026-07-01 — a\n"
                 "- [[B]] | ADMIN | [User] Pending — b\n")
        new, changed = mig.rewrite_index(index, {"A": None})
        self.assertEqual(new, "- [[A]] | ADMIN | [User] a\n"
                              "- [[B]] | ADMIN | [User] Pending — b\n")
        self.assertEqual(changed, ["A"])


class PlanPageTests(unittest.TestCase):
    def proposal(self, verdict: str) -> dict:
        return {"urgency": "MEDIUM", "impact": "HIGH", "due": "2026-07-01",
                "due_verdict": verdict}

    def test_drop_moves_date_into_body_note(self) -> None:
        new, _, kept = mig.plan_page(PAGE, self.proposal("drop"), TODAY)
        self.assertIsNone(kept)
        self.assertIn("due: null\n", new)
        self.assertIn("priority: HIGH\n", new)
        self.assertIn("updated: 2026-10-13\n", new)
        self.assertNotIn("reviewed:", new)
        self.assertTrue(new.endswith(
            "Body text.\n\n*Former due date 2026-07-01 removed 2026-10-13 — "
            "not an external deadline.*\n"))

    def test_keep_leaves_date_and_body(self) -> None:
        new, _, kept = mig.plan_page(PAGE, self.proposal("keep"), TODAY)
        self.assertEqual(kept, "2026-07-01")
        self.assertIn("due: 2026-07-01\n", new)
        self.assertTrue(new.endswith("Body text.\n"))

    def test_reviewed_or_changed_due_is_skipped(self) -> None:
        reviewed = PAGE.replace("status:", "reviewed: 2026-10-12\nstatus:")
        with self.assertRaises(ValueError):
            mig.plan_page(reviewed, self.proposal("drop"), TODAY)
        moved = PAGE.replace("due: 2026-07-01", "due: 2026-12-01")
        with self.assertRaises(ValueError):
            mig.plan_page(moved, self.proposal("drop"), TODAY)


if __name__ == "__main__":
    unittest.main()
