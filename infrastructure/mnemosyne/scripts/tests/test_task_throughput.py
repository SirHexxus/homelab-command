"""Tests for lib/task_throughput.py (disk sources only, no Postgres).

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
import task_throughput  # noqa: E402

TODAY = date(2026, 10, 13)


def _page(**fields: str) -> str:
    body = "".join(f"{k}: {v}\n" for k, v in fields.items())
    return f"---\nbucket: ADMIN\ntask_type: user\n{body}---\n\nBody.\n"


class ThroughputTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        admin = self.root / "admin"
        archive = self.root / "archive" / "admin-closed"
        admin.mkdir()
        archive.mkdir(parents=True)
        pages = {
            admin / "Open High.md": _page(status="Pending", priority="HIGH",
                                          urgency="HIGH", impact="HIGH",
                                          reviewed="2026-10-12", created="2026-10-10"),
            admin / "Open Old.md": _page(status="Pending", created="2026-01-01"),
            admin / "Closed Unswept.md": _page(status="Done", priority="HIGH",
                                               created="2026-10-03", closed="2026-10-11"),
            archive / "Closed Swept.md": _page(status="Cancelled", priority="HIGH",
                                               created="2026-09-20", closed="2026-10-10"),
            archive / "Closed Long Ago.md": _page(status="Done", priority="LOW",
                                                  created="2026-01-01", closed="2026-08-01"),
            archive / "Closed Pre Rollout.md": _page(status="Done", priority="LOW",
                                                     created="2026-10-01"),
        }
        for path, text in pages.items():
            path.write_text(text, encoding="utf-8")
        self.stats = task_throughput.compute(self.root, TODAY, use_postgres=False)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_totals(self) -> None:
        t = self.stats["totals"]
        self.assertEqual(t["open"], 2)
        self.assertEqual(t["closed"], 2)
        self.assertEqual(t["cancelled"], 1)
        self.assertEqual(t["opened"], 1)   # Open High; Closed Unswept was 10 days ago
        self.assertTrue(self.stats["complete"])

    def test_rows_and_median(self) -> None:
        high = self.stats["rows"]["HIGH"]
        self.assertEqual(high["open"], 1)
        self.assertEqual(high["closed"], 2)
        self.assertEqual(high["median_days"], 14)   # median of 8 and 20
        self.assertEqual(self.stats["rows"]["LOW"]["closed"], 0)
        self.assertEqual(self.stats["rows"]["untriaged"]["unreviewed"], 1)

    def test_renderers(self) -> None:
        md = task_throughput.to_markdown(self.stats)
        self.assertIn("| HIGH | 1 | 0 | 0 | 1 | 2 | 14 |", md)
        self.assertNotIn("Partial", md)
        self.assertIn("2 closed (1 cancelled or skipped)",
                      task_throughput.digest_summary(self.stats))


if __name__ == "__main__":
    unittest.main()
