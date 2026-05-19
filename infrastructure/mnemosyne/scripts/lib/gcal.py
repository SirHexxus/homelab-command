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
