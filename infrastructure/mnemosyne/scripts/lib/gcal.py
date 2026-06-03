"""Google Calendar fetcher for the Mnemosyne daily digest.

Pure stdlib. Library-shaped — no CLI, no prints, no exceptions raised
into callers. fetch_calendar() returns a list of event dicts on success
(an empty list when the day genuinely has no events) or None on any
failure (network, auth, parse). The caller treats both None and the
empty list as "no calendar line" per the digest's no-filler rule — a
missing calendar block is silently correct, never an apologetic
placeholder.

Auth is OAuth 2.0 with a long-lived refresh token: fetch_calendar()
exchanges the refresh token for a short-lived access token at Google's
token endpoint, then queries the Calendar REST API. Raw urllib only —
no google-api-python-client — consistent with the weather module.

Failure is strict: if the token exchange fails, or any one calendar's
event query fails, the whole fetch returns None. A partial digest built
from one of two calendars would be quietly wrong, so all-or-nothing is
the safer contract.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, tzinfo

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
EVENTS_ENDPOINT = "https://www.googleapis.com/calendar/v3/calendars/{cal}/events"
REQUEST_TIMEOUT_SECONDS = 5
MAX_EVENTS_PER_CALENDAR = 50


def _format_clock(dt: datetime) -> str:
    """Format a datetime into 'H:MM AM/PM', dropping the leading zero."""
    return dt.strftime("%I:%M %p").lstrip("0")


def _parse_dt(value: str) -> datetime | None:
    """Parse an RFC 3339 timestamp into an aware datetime. None on failure.

    Google's `dateTime` fields usually carry a numeric offset, but a 'Z'
    suffix is normalised first so older Pythons' fromisoformat accepts it.
    """
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _post_form(url: str, fields: dict[str, str]) -> dict | None:
    """POST a form-encoded body and parse JSON. None on any failure."""
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _get_json(url: str, access_token: str) -> dict | None:
    """GET a bearer-authenticated URL and parse JSON. None on any failure."""
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _get_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str | None:
    """Exchange a refresh token for a short-lived access token. None on failure."""
    payload = _post_form(TOKEN_ENDPOINT, {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    if payload is None:
        return None
    token = payload.get("access_token")
    return token if token else None


def _fetch_events(
    calendar_id: str,
    access_token: str,
    time_min: str,
    time_max: str,
) -> list[dict] | None:
    """Fetch raw events overlapping [time_min, time_max] for one calendar.

    `singleEvents=true` expands recurring events into concrete instances,
    so callers see real occurrences rather than the recurrence rule.
    None on any failure.
    """
    query = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": str(MAX_EVENTS_PER_CALENDAR),
    })
    url = (
        EVENTS_ENDPOINT.format(cal=urllib.parse.quote(calendar_id, safe=""))
        + "?"
        + query
    )
    payload = _get_json(url, access_token)
    if payload is None:
        return None
    items = payload.get("items")
    if items is None:
        return None
    return items


def _parse_event(
    raw: dict,
    day: date,
    local_tz: tzinfo,
) -> tuple[tuple, dict] | None:
    """Parse one raw event into (sort_key, event_dict). None to skip.

    Skipped: cancelled events, events with unparseable times, and events
    that do not actually intersect `day` (Google's overlap query can
    return adjacent events on the boundary).

    All-day events carry a `date`; timed events carry a `dateTime`. An
    event whose start precedes `day` but which still covers it is flagged
    `ongoing` so the digest renders it as in-progress rather than new.
    """
    if raw.get("status") == "cancelled":
        return None

    title = (raw.get("summary") or "(untitled)").strip()
    location = (raw.get("location") or "").strip()
    start = raw.get("start") or {}
    end = raw.get("end") or {}

    if "date" in start:
        try:
            start_date = date.fromisoformat(start["date"])
            # Google's all-day end.date is exclusive.
            end_date = date.fromisoformat(end.get("date", start["date"]))
        except (ValueError, TypeError):
            return None
        if start_date > day or end_date <= day:
            return None
        ongoing = start_date < day
        event = {
            "title": title,
            "all_day": True,
            "ongoing": ongoing,
            "start": "",
            "end": "",
            "location": location,
        }
        return (not ongoing, False, 0), event

    start_dt = _parse_dt(start.get("dateTime", ""))
    end_dt = _parse_dt(end.get("dateTime", ""))
    if start_dt is None or end_dt is None:
        return None

    start_local = start_dt.astimezone(local_tz)
    end_local = end_dt.astimezone(local_tz)
    day_start = datetime.combine(day, time.min, tzinfo=local_tz)
    day_end = day_start + timedelta(days=1)
    if end_local <= day_start or start_local >= day_end:
        return None

    ongoing = start_local < day_start
    event = {
        "title": title,
        "all_day": False,
        "ongoing": ongoing,
        "start": _format_clock(start_local),
        "end": _format_clock(end_local),
        "location": location,
    }
    minutes = start_local.hour * 60 + start_local.minute
    return (not ongoing, True, minutes), event


def fetch_calendar(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    calendar_ids: tuple[str, ...],
    day: date,
) -> list[dict] | None:
    """Fetch `day`'s events across all given calendars, merged and sorted.

    Returns a list of event dicts, each carrying: title, all_day (bool),
    ongoing (bool), start, end (local 'H:MM AM/PM' strings, empty for
    all-day), and location ('' when absent). Ordered ongoing-first, then
    all-day, then timed events by start time. Empty list when the day has
    no events; None on any auth or network failure.
    """
    if not (client_id and client_secret and refresh_token and calendar_ids):
        return None

    access_token = _get_access_token(client_id, client_secret, refresh_token)
    if access_token is None:
        return None

    local_tz = datetime.now().astimezone().tzinfo
    day_start = datetime.combine(day, time.min, tzinfo=local_tz)
    day_end = day_start + timedelta(days=1)
    time_min = day_start.isoformat()
    time_max = day_end.isoformat()

    collected: list[tuple[tuple, dict]] = []
    for calendar_id in calendar_ids:
        items = _fetch_events(calendar_id, access_token, time_min, time_max)
        if items is None:
            return None
        for raw in items:
            parsed = _parse_event(raw, day, local_tz)
            if parsed is not None:
                collected.append(parsed)

    collected.sort(key=lambda pair: pair[0])
    return [event for _, event in collected]


# ── Calendar writes ──────────────────────────────────────────────────────────
#
# Writes are intentionally additive — added below the read API, never edits
# of it. The read contract (None on failure) carries over: write helpers
# return per-call result dicts; apply_calendar_overrides aggregates them
# into a per-override status array. No exceptions propagate to callers.

INSTANCES_ENDPOINT = (
    "https://www.googleapis.com/calendar/v3/calendars/{cal}/events/{eid}/instances"
)


def _request_with_body(
    url: str,
    method: str,
    access_token: str,
    body: dict,
) -> tuple[int, dict | None]:
    """Issue a method-with-JSON-body request. Returns (status, parsed body or None)."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            err_body = None
        return exc.code, err_body
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None
    try:
        return status, json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return status, None


def _find_event_instance(
    calendar_id: str,
    access_token: str,
    title: str,
    target_date: str,
) -> dict | None:
    """Find the concrete event instance matching `title` on `target_date`.

    Lists events in the target date's 24-hour window (singleEvents=True) and
    returns the first non-cancelled instance whose summary matches `title`
    exactly. This walks live instances directly — no need to locate the
    recurrence master first, which is brittle when the calendar has multiple
    dead recurring masters with the same title.

    Returns the instance dict (which includes `recurringEventId` if it came
    from a recurring series) or None if no match.
    """
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        return None
    time_min = datetime.combine(d, time.min).astimezone().isoformat()
    time_max = datetime.combine(d + timedelta(days=1), time.min).astimezone().isoformat()
    query = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "maxResults": "250",
        "orderBy": "startTime",
    })
    url = (
        EVENTS_ENDPOINT.format(cal=urllib.parse.quote(calendar_id, safe=""))
        + "?"
        + query
    )
    payload = _get_json(url, access_token)
    if payload is None:
        return None
    items = payload.get("items") or []
    for item in items:
        if item.get("status") == "cancelled":
            continue
        if (item.get("summary") or "").strip() == title:
            return item
    return None


def _apply_move_instance(
    calendar_id: str,
    access_token: str,
    override: dict,
) -> dict:
    match = override.get("match") or {}
    title = match.get("title")
    target_date = match.get("date")
    new_start = override.get("new_start")
    new_end = override.get("new_end")
    if not (title and target_date and new_start and new_end):
        return {"status": "skipped", "reason": "missing required fields"}
    instance = _find_event_instance(calendar_id, access_token, title, target_date)
    if instance is None:
        return {"status": "failed", "reason": f"no live instance of {title!r} on {target_date}"}
    body = {
        "start": {"dateTime": new_start},
        "end": {"dateTime": new_end},
    }
    if override.get("note"):
        body["description"] = override["note"]
    url = (
        EVENTS_ENDPOINT.format(cal=urllib.parse.quote(calendar_id, safe=""))
        + "/"
        + urllib.parse.quote(instance["id"], safe="")
    )
    status, body_resp = _request_with_body(url, "PATCH", access_token, body)
    if status == 200:
        return {"status": "applied", "instance_id": instance["id"]}
    return {"status": "failed", "reason": f"PATCH returned {status}", "body": body_resp}


def _apply_cancel_instance(
    calendar_id: str,
    access_token: str,
    override: dict,
) -> dict:
    match = override.get("match") or {}
    title = match.get("title")
    target_date = match.get("date")
    if not (title and target_date):
        return {"status": "skipped", "reason": "missing required fields"}
    instance = _find_event_instance(calendar_id, access_token, title, target_date)
    if instance is None:
        return {"status": "failed", "reason": f"no live instance of {title!r} on {target_date}"}
    url = (
        EVENTS_ENDPOINT.format(cal=urllib.parse.quote(calendar_id, safe=""))
        + "/"
        + urllib.parse.quote(instance["id"], safe="")
    )
    status, body_resp = _request_with_body(
        url, "PATCH", access_token, {"status": "cancelled"}
    )
    if status == 200:
        return {"status": "applied", "instance_id": instance["id"]}
    return {"status": "failed", "reason": f"PATCH returned {status}", "body": body_resp}


def _apply_add_event(
    calendar_id: str,
    access_token: str,
    override: dict,
) -> dict:
    title = override.get("title")
    start = override.get("start")
    end = override.get("end")
    if not (title and start and end):
        return {"status": "skipped", "reason": "missing required fields"}
    body = {
        "summary": title,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }
    if override.get("note"):
        body["description"] = override["note"]
    if override.get("location"):
        body["location"] = override["location"]
    url = EVENTS_ENDPOINT.format(cal=urllib.parse.quote(calendar_id, safe=""))
    status, body_resp = _request_with_body(url, "POST", access_token, body)
    if status in (200, 201):
        return {"status": "applied", "event_id": (body_resp or {}).get("id")}
    return {"status": "failed", "reason": f"POST returned {status}", "body": body_resp}


_ACTION_DISPATCH = {
    "move_instance": _apply_move_instance,
    "cancel_instance": _apply_cancel_instance,
    "add_event": _apply_add_event,
}


def apply_calendar_overrides(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    calendar_id: str,
    overrides: list[dict],
) -> dict:
    """Apply a list of schedule overrides to one Google Calendar.

    Per-override status; no transactional rollback. Returns:
        {
            "applied": [...],   # successful overrides with their action results
            "failed":  [...],   # overrides that hit an API error
            "skipped": [...],   # overrides missing required fields or unknown actions
        }
    Auth failures or absent inputs return an error sentinel:
        {"error": "..."}
    """
    if not (client_id and client_secret and refresh_token and calendar_id):
        return {"error": "missing auth or calendar_id"}
    if not overrides:
        return {"applied": [], "failed": [], "skipped": []}

    access_token = _get_access_token(client_id, client_secret, refresh_token)
    if access_token is None:
        return {"error": "token exchange failed (scope may be too narrow for writes)"}

    applied: list[dict] = []
    failed: list[dict] = []
    skipped: list[dict] = []
    for override in overrides:
        action = (override.get("action") or "").strip()
        handler = _ACTION_DISPATCH.get(action)
        if handler is None:
            skipped.append({"override": override, "reason": f"unknown action {action!r}"})
            continue
        result = handler(calendar_id, access_token, override)
        status = result.get("status")
        entry = {"override": override, "result": result}
        if status == "applied":
            applied.append(entry)
        elif status == "skipped":
            skipped.append(entry)
        else:
            failed.append(entry)
    return {"applied": applied, "failed": failed, "skipped": skipped}
