"""Tests for daily-digest's breached-CRITICAL classifier.

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from datetime import date
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "daily-digest"
_LOADER = importlib.machinery.SourceFileLoader("daily_digest", str(_SCRIPT))
_SPEC = importlib.util.spec_from_loader("daily_digest", _LOADER)
digest = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(digest)

TODAY = date(2026, 10, 13)


def _task(**override: object) -> dict:
    task = {"priority": "HIGH", "impact": "CRITICAL", "sla_breached": True,
            "unreviewed": False, "created": "2026-01-01"}
    task.update(override)
    return task


class HardBreachTests(unittest.TestCase):
    def test_reviewed_critical_impact_breach(self) -> None:
        self.assertTrue(digest._hard_breach(_task(), TODAY))

    def test_critical_priority_breach(self) -> None:
        self.assertTrue(digest._hard_breach(_task(priority="CRITICAL", impact="HIGH"), TODAY))

    def test_not_breached_or_not_critical(self) -> None:
        self.assertFalse(digest._hard_breach(_task(sla_breached=False), TODAY))
        self.assertFalse(digest._hard_breach(_task(impact="HIGH"), TODAY))

    def test_unreviewed_clock_runs_from_created(self) -> None:
        # HIGH priority -> 7-day Review SLA, counted from capture.
        fresh = _task(unreviewed=True, created="2026-10-10")
        stale = _task(unreviewed=True, created="2026-10-01")
        self.assertFalse(digest._hard_breach(fresh, TODAY))
        self.assertTrue(digest._hard_breach(stale, TODAY))


if __name__ == "__main__":
    unittest.main()
