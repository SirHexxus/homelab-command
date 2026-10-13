"""Tests for the set-task-priority script's pure helpers.

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "set-task-priority"
_LOADER = importlib.machinery.SourceFileLoader("set_task_priority", str(_SCRIPT))
_SPEC = importlib.util.spec_from_loader("set_task_priority", _LOADER)
stp = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(stp)

TODAY = "2026-10-13"


class PlanChangeTests(unittest.TestCase):
    def test_merges_with_existing_and_recomputes(self) -> None:
        fields = {"urgency": "LOW", "impact": "HIGH", "priority": "MEDIUM",
                  "updated": "2026-01-01"}
        updates = stp.plan_change(fields, "CRITICAL", None, None, False, TODAY)
        self.assertEqual(updates["urgency"], "CRITICAL")
        self.assertEqual(updates["impact"], "HIGH")
        self.assertEqual(updates["priority"], "CRITICAL")
        self.assertEqual(updates["reviewed"], TODAY)
        self.assertEqual(updates["updated"], TODAY)
        self.assertNotIn("due", updates)

    def test_partial_inputs_leave_priority_null(self) -> None:
        updates = stp.plan_change({}, "HIGH", None, None, False, TODAY)
        self.assertEqual(updates["impact"], "null")
        self.assertEqual(updates["priority"], "null")
        self.assertNotIn("updated", updates)

    def test_due_and_clear(self) -> None:
        self.assertEqual(stp.plan_change({}, None, None, "2026-11-01", False, TODAY)["due"],
                         "2026-11-01")
        self.assertEqual(stp.plan_change({"due": "2026-05-01"}, None, None, None, True,
                                         TODAY)["due"], "null")


class IndexDueTests(unittest.TestCase):
    INDEX = (
        "## Admin\n"
        "- [[Renew Cert]] | ADMIN | [User] Pending due 2026-05-01 — certbot renewal\n"
        "- [[Add Rubric]] | ADMIN | [Maintenance] due null — prompt edit\n"
        "- [[Read Book]] | ADMIN | [User] Pending — overdue 2026-01-01 mention stays\n"
    )

    def test_replace_existing(self) -> None:
        out, changed = stp.rewrite_index_due(self.INDEX, "Renew Cert", "2026-12-01")
        self.assertTrue(changed)
        self.assertIn("- [[Renew Cert]] | ADMIN | [User] due 2026-12-01 Pending — certbot",
                      out)

    def test_remove_token(self) -> None:
        out, changed = stp.rewrite_index_due(self.INDEX, "Add Rubric", None)
        self.assertTrue(changed)
        self.assertIn("- [[Add Rubric]] | ADMIN | [Maintenance] — prompt edit\n", out)

    def test_insert_datetime_and_leave_prose(self) -> None:
        out, changed = stp.rewrite_index_due(self.INDEX, "Read Book", "2026-11-02T09:30")
        self.assertTrue(changed)
        self.assertIn("[User] due 2026-11-02T09:30 Pending — overdue 2026-01-01 mention",
                      out)

    def test_missing_title_unchanged(self) -> None:
        out, changed = stp.rewrite_index_due(self.INDEX, "Nope", "2026-12-01")
        self.assertFalse(changed)
        self.assertEqual(out, self.INDEX)


if __name__ == "__main__":
    unittest.main()
