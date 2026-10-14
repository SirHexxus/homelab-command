"""Tests for lib/admin_tasks.py.

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import admin_tasks  # noqa: E402

TODAY = date(2026, 10, 13)


def _page(**fields: str) -> str:
    body = "".join(f"{k}: {v}\n" for k, v in fields.items())
    return f"---\nbucket: ADMIN\n{body}---\n\nBody.\n"


class AdminTasksTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        admin = self.root / "admin"
        admin.mkdir()
        pages = {
            "Old Style": _page(due="null", status="Pending", task_type="user",
                               created="2026-01-01"),
            "Scored Low": _page(status="Pending", task_type="user", urgency="LOW",
                                impact="LOW", priority="LOW", reviewed="2026-10-01",
                                created="2026-09-01"),
            "Scored High": _page(status="Active", task_type="maintenance",
                                 urgency="HIGH", impact="HIGH", priority="HIGH",
                                 reviewed="2026-10-01", created="2026-09-01"),
            "Real Deadline": _page(status="Pending", task_type="user", urgency="LOW",
                                   impact="MEDIUM", reviewed="2026-10-12",
                                   due="2026-10-15T09:00"),
            "Finished": _page(status="Done", task_type="user", closed="2026-10-10"),
            "Stuck": _page(status="Blocked", task_type="user"),
        }
        for title, text in pages.items():
            (admin / f"{title}.md").write_text(text, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _tasks(self) -> dict[str, dict]:
        return {t["title"]: t for t in admin_tasks.load_open_tasks(self.root, TODAY)}

    def test_closed_excluded_blocked_flagged(self) -> None:
        tasks = self._tasks()
        self.assertNotIn("Finished", tasks)
        self.assertTrue(tasks["Stuck"]["blocked"])

    def test_pre_reframe_page_loads_unscored(self) -> None:
        old = self._tasks()["Old Style"]
        self.assertIsNone(old["priority"])
        self.assertIsNone(old["due"])
        self.assertTrue(old["unreviewed"])
        self.assertTrue(old["sla_breached"])

    def test_review_sla(self) -> None:
        tasks = self._tasks()
        self.assertTrue(tasks["Scored High"]["sla_breached"])   # 7-day Review SLA
        self.assertFalse(tasks["Scored Low"]["sla_breached"])   # 90-day Review SLA
        self.assertEqual(tasks["Scored High"]["sla_due"], "2026-10-08")

    def test_deadline_escalates_effective_priority(self) -> None:
        deadline = self._tasks()["Real Deadline"]
        self.assertEqual(deadline["priority"], "LOW")
        self.assertEqual(deadline["effective_priority"], "MEDIUM")

    def test_focus_order(self) -> None:
        tasks = [t for t in self._tasks().values() if not t["blocked"]]
        tasks.sort(key=admin_tasks.focus_key)
        self.assertEqual([t["title"] for t in tasks],
                         ["Scored High", "Real Deadline", "Scored Low", "Old Style"])

    def test_checkin_order_untriaged_first(self) -> None:
        tasks = [t for t in self._tasks().values()
                 if t["sla_breached"] and not t["blocked"]]
        tasks.sort(key=admin_tasks.checkin_key)
        self.assertEqual([t["title"] for t in tasks], ["Old Style", "Scored High"])


if __name__ == "__main__":
    unittest.main()
