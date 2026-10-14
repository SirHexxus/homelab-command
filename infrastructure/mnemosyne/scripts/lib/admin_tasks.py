"""Load and rank open ADMIN tasks — the shared query layer.

`next-tasks` (CLI), `daily-digest`, and `report-task-throughput` all read the
admin/ bucket through this module, so "what counts as open", "what is past
its Review SLA", and "what order do tasks come in" have one implementation.

Every task is annotated with values derived through `lib/task_priority.py`:
effective priority (deadline-escalated, reports only), unreviewed, and
Review-SLA-breached. Pages written before the priority reframe (no urgency/impact/
reviewed) load fine: they are simply unscored and unreviewed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import admin_page
import task_priority
import task_status


def _clean(raw: str | None) -> str | None:
    """Frontmatter value with quotes stripped; None for null/empty."""
    if task_priority.is_null(raw):
        return None
    return raw.strip().strip("'\"")


def load_task(path: Path, today: date) -> dict:
    """One admin page as an annotated task dict."""
    fields = admin_page.read_fields(path.read_text(encoding="utf-8"))
    urgency = task_priority.normalize(fields.get("urgency"))
    impact = task_priority.normalize(fields.get("impact"))
    due = _clean(fields.get("due"))
    reviewed = _clean(fields.get("reviewed"))
    priority = task_priority.compute_priority(urgency, impact)
    status = _clean(fields.get("status")) or "Pending"
    return {
        "title": path.stem,
        "path": str(path),
        "status": status,
        "task_type": _clean(fields.get("task_type")) or "user",
        "urgency": urgency,
        "impact": impact,
        "priority": priority,
        "effective_priority": task_priority.effective_priority(urgency, impact, due, today),
        "due": due if task_priority.is_valid_due(due) else None,
        "created": _clean(fields.get("created")),
        "reviewed": reviewed,
        "closed": _clean(fields.get("closed")),
        "unreviewed": task_priority.is_unreviewed(reviewed),
        "sla_breached": task_priority.is_sla_breached(priority, reviewed, today),
        "sla_due": (str(task_priority.sla_due(priority, reviewed))
                        if reviewed else None),
        "blocked": status.lower() == "blocked",
    }


def load_open_tasks(wiki_root: Path, today: date) -> list[dict]:
    """Every non-closed task in admin/, annotated."""
    tasks = []
    for path in sorted((wiki_root / "admin").glob("*.md")):
        task = load_task(path, today)
        if not task_status.is_closed(task["status"]):
            tasks.append(task)
    return tasks


def focus_key(task: dict) -> tuple:
    """Highest effective priority first; then soonest deadline; then the
    task reviewed longest ago (unreviewed first)."""
    due_date = task_priority.parse_due(task["due"])
    return (
        -task_priority.rank(task["effective_priority"]),
        due_date or date.max,
        task["reviewed"] or "",
        task["title"].lower(),
    )


def checkin_key(task: dict) -> tuple:
    """Untriaged (no impact) first, then highest impact; then priority; then
    the oldest task. Unknown impact is exactly what a check-in should fix."""
    return (
        task["impact"] is not None,
        -task_priority.rank(task["impact"]),
        -task_priority.rank(task["priority"]),
        task["created"] or "",
        task["title"].lower(),
    )


def due_key(task: dict) -> tuple:
    """Soonest real deadline first (undated last)."""
    return (task["due"] or "9999", task["title"].lower())


SORTS = {"focus": focus_key, "checkin": checkin_key, "due": due_key}
