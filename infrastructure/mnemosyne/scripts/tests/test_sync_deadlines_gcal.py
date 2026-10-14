"""Tests for sync-deadlines-gcal's reconcile logic (offline, no Google).

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "sync-deadlines-gcal"
_LOADER = importlib.machinery.SourceFileLoader("sync_deadlines_gcal", str(_SCRIPT))
_SPEC = importlib.util.spec_from_loader("sync_deadlines_gcal", _LOADER)
sync = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(sync)


def _task(title: str, due: str | None) -> dict:
    return {"title": title, "due": due, "effective_priority": "HIGH", "impact": "HIGH",
            "task_type": "user"}


def _event(task: dict, event_id: str, **override: object) -> dict:
    """An event exactly as the sync would have written it, plus overrides."""
    event = {"id": event_id, "status": "confirmed", **sync.event_body(task)}
    event.update(override)
    return event


class EventShapeTests(unittest.TestCase):
    def test_all_day_end_is_exclusive(self) -> None:
        body = sync.event_body(_task("A", "2026-10-20"))
        self.assertEqual(body["start"], {"date": "2026-10-20"})
        self.assertEqual(body["end"], {"date": "2026-10-21"})

    def test_timed_event_is_one_hour_local(self) -> None:
        body = sync.event_body(_task("A", "2026-10-20T15:30"))
        self.assertEqual(body["start"]["dateTime"], "2026-10-20T15:30:00")
        self.assertEqual(body["end"]["dateTime"], "2026-10-20T16:30:00")
        self.assertEqual(body["start"]["timeZone"], sync.TIMEZONE)

    def test_event_due_round_trips_google_offsets(self) -> None:
        # Google echoes timed starts back with a numeric offset.
        self.assertEqual(sync.event_due({"start": {"dateTime": "2026-10-20T15:30:00-07:00"}}),
                         "2026-10-20T15:30")
        self.assertEqual(sync.event_due({"start": {"date": "2026-10-20"}}), "2026-10-20")


class PlanTests(unittest.TestCase):
    def test_create_update_delete(self) -> None:
        new, moved_in_wiki, gone = (_task("New", "2026-11-01"),
                                    _task("Moved", "2026-11-05"),
                                    _task("Gone", "2026-11-09"))
        events = [_event(_task("Moved", "2026-11-02"), "e1"), _event(gone, "e2")]
        actions, drift = sync.plan_sync([new, moved_in_wiki, _task("Undated", None)], events)
        verbs = {(a[0], a[1]) for a in actions}
        self.assertEqual(verbs, {("create", "New"), ("update", "Moved"), ("delete", "Gone")})
        self.assertEqual(drift, [])

    def test_in_sync_is_a_no_op(self) -> None:
        # DST ends 2026-11-01, so 09:00 Pacific that day is -08:00, not -07:00.
        task = _task("Same", "2026-11-01T09:00")
        event = _event(task, "e1", start={"dateTime": "2026-11-01T09:00:00-08:00"})
        self.assertEqual(sync.plan_sync([task], [event]), ([], []))

    def test_hand_moved_event_is_drift_and_reverted(self) -> None:
        task = _task("Fixed", "2026-11-01")
        event = _event(task, "e1", start={"date": "2026-11-03"}, end={"date": "2026-11-04"})
        actions, drift = sync.plan_sync([task], [event])
        self.assertEqual([(a[0], a[1]) for a in actions], [("update", "Fixed")])
        self.assertEqual(len(drift), 1)
        self.assertIn("moved by hand to 2026-11-03", drift[0])

    def test_hand_deleted_event_is_drift_and_recreated(self) -> None:
        task = _task("Deleted", "2026-11-01")
        actions, drift = sync.plan_sync([task], [_event(task, "e1", status="cancelled")])
        self.assertEqual([(a[0], a[1]) for a in actions], [("create", "Deleted")])
        self.assertIn("deleted in Google Calendar", drift[0])

    def test_duplicates_collapse_to_one(self) -> None:
        task = _task("Dup", "2026-11-01")
        actions, _ = sync.plan_sync([task], [_event(task, "e1"), _event(task, "e2")])
        self.assertEqual(actions, [("delete", "Dup", "e2", None)])


if __name__ == "__main__":
    unittest.main()
