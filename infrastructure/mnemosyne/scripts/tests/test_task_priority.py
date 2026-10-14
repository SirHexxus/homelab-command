"""Tests for lib/task_priority.py and lib/admin_page.py.

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import admin_page  # noqa: E402
import task_priority as tp  # noqa: E402

TODAY = date(2026, 10, 13)


class MatrixTests(unittest.TestCase):
    def test_every_cell_is_a_level(self) -> None:
        for u in tp.levels():
            for i in tp.levels():
                self.assertIn(tp.compute_priority(u, i), tp.levels())

    def test_impact_weighted_above_urgency(self) -> None:
        self.assertEqual(tp.compute_priority("CRITICAL", "LOW"), "MEDIUM")
        self.assertEqual(tp.compute_priority("LOW", "CRITICAL"), "HIGH")

    def test_diagonal_is_identity(self) -> None:
        for level in tp.levels():
            self.assertEqual(tp.compute_priority(level, level), level)

    def test_monotonic_in_both_inputs(self) -> None:
        lv = tp.levels()
        for a in range(len(lv)):
            for b in range(len(lv) - 1):
                self.assertLessEqual(tp.rank(tp.compute_priority(lv[a], lv[b])),
                                     tp.rank(tp.compute_priority(lv[a], lv[b + 1])))
                self.assertLessEqual(tp.rank(tp.compute_priority(lv[b], lv[a])),
                                     tp.rank(tp.compute_priority(lv[b + 1], lv[a])))

    def test_null_and_case(self) -> None:
        self.assertIsNone(tp.compute_priority(None, "LOW"))
        self.assertIsNone(tp.compute_priority("null", "LOW"))
        self.assertIsNone(tp.compute_priority("urgent", "LOW"))
        self.assertEqual(tp.compute_priority("high", " medium "), "MEDIUM")


class DueTests(unittest.TestCase):
    def test_valid_forms(self) -> None:
        for raw in (None, "", "null", "2026-10-20", "2026-10-20T15:30", "'2026-10-20'"):
            self.assertTrue(tp.is_valid_due(raw), raw)
        for raw in ("2026-13-01", "next week", "2026-10-20 15:30", "2026-10-20T15"):
            self.assertFalse(tp.is_valid_due(raw), raw)

    def test_parse_due_datetime(self) -> None:
        self.assertEqual(tp.parse_due("2026-10-20T15:30"), date(2026, 10, 20))

    def test_escalation(self) -> None:
        self.assertEqual(tp.effective_urgency("LOW", None, TODAY), "LOW")
        self.assertEqual(tp.effective_urgency("LOW", "2026-11-30", TODAY), "LOW")
        self.assertEqual(tp.effective_urgency("LOW", "2026-10-20", TODAY), "HIGH")
        self.assertEqual(tp.effective_urgency("LOW", "2026-10-13T18:00", TODAY), "CRITICAL")
        self.assertEqual(tp.effective_urgency("MEDIUM", "2026-10-01", TODAY), "CRITICAL")
        # Escalation only raises, never lowers.
        self.assertEqual(tp.effective_urgency("CRITICAL", "2026-10-20", TODAY), "CRITICAL")

    def test_deadline_without_impact_still_scored(self) -> None:
        self.assertEqual(tp.effective_priority(None, None, "2026-10-13", TODAY), "HIGH")
        self.assertIsNone(tp.effective_priority(None, None, None, TODAY))


class ReviewSlaTests(unittest.TestCase):
    def test_unreviewed_breaches_sla(self) -> None:
        self.assertTrue(tp.is_unreviewed(""))
        self.assertTrue(tp.is_sla_breached("LOW", None, TODAY))
        self.assertTrue(tp.is_sla_breached("LOW", "null", TODAY))

    def test_sla_boundaries(self) -> None:
        self.assertFalse(tp.is_sla_breached("HIGH", "2026-10-06", TODAY))
        self.assertTrue(tp.is_sla_breached("HIGH", "2026-10-05", TODAY))
        self.assertFalse(tp.is_sla_breached("CRITICAL", "2026-10-12", TODAY))
        self.assertTrue(tp.is_sla_breached("CRITICAL", "2026-10-11", TODAY))

    def test_unset_priority_uses_default_sla(self) -> None:
        self.assertEqual(tp.review_sla_days(None), tp.review_sla_days("MEDIUM"))


class AdminPageTests(unittest.TestCase):
    PAGE = ("---\ntitle: Example\nbucket: ADMIN\ndue: 2026-05-01\n"
            "status: Pending\ntags:\n  - homelab\n---\n\nBody: keep me.\n")

    def test_replace_add_remove(self) -> None:
        out = admin_page.set_fields(self.PAGE, {
            "status": "Done", "closed": "2026-10-13", "due": None,
        })
        fields = admin_page.read_fields(out)
        self.assertEqual(fields["status"], "Done")
        self.assertEqual(fields["closed"], "2026-10-13")
        self.assertNotIn("due", fields)
        self.assertIn("  - homelab\n", out)
        self.assertTrue(out.endswith("---\n\nBody: keep me.\n"))

    def test_no_change_is_identity(self) -> None:
        self.assertEqual(admin_page.set_fields(self.PAGE, {}), self.PAGE)

    def test_no_frontmatter_raises(self) -> None:
        with self.assertRaises(ValueError):
            admin_page.set_fields("just text\n", {"status": "Done"})


if __name__ == "__main__":
    unittest.main()
