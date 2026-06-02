#!/usr/bin/env python3
"""Fetch today's Google Calendar events for the daily digest.

Ported from infrastructure/mnemosyne/scripts/lib/gcal.py — pure stdlib,
OAuth refresh-token flow, raw urllib (no google-api-python-client).

Reads:
    GCAL_CREDS_PATH  — JSON {refresh_token: "..."}
                       default /etc/hermes-agent/gcal-creds.json
    GCAL_CLIENT_PATH — JSON {client_id: "...", client_secret: "..."}
                       default /etc/hermes-agent/gcal-client.json
    GCAL_CALENDAR_IDS — comma-separated calendar IDs (required)

Emits JSON to stdout: {"events": [...], "source": "google-calendar",
"day": "YYYY-MM-DD"}. On failure (any layer — auth, network, parse) prints
{"events": [], "error": "..."} and exits 0 anyway — the no-filler rule
treats a missing calendar block as silently correct.

Usage:
    fetch_calendar.py [--day YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
EVENTS_ENDPOINT = "https://www.googleapis.com/calendar/v3/calendars/{cal}/events"
REQUEST_TIMEOUT_SECONDS = 5
MAX_EVENTS_PER_CALENDAR = 50
DEFAULT_CREDS_PATH = "/etc/hermes-agent/gcal-creds.json"
DEFAULT_CLIENT_PATH = "/etc/hermes-agent/gcal-client.json"


def format_clock(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def post_form(url: str, fields: dict[str, str]) -> dict | None:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def get_json(url: str, access_token: str) -> dict | None:
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


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str | None:
    payload = post_form(TOKEN_ENDPOINT, {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    if payload is None:
        return None
    return payload.get("access_token") or None


def fetch_events(
    calendar_id: str, access_token: str, time_min: str, time_max: str
) -> list[dict] | None:
    query = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": str(MAX_EVENTS_PER_CALENDAR),
    })
    url = (
        EVENTS_ENDPOINT.format(cal=urllib.parse.quote(calendar_id, safe=""))
        + "?" + query
    )
    payload = get_json(url, access_token)
    if payload is None:
        return None
    items = payload.get("items")
    return items if items is not None else None


def parse_event(raw: dict, day: date, local_tz: tzinfo) -> tuple[tuple, dict] | None:
    if raw.get("status") == "cancelled":
        return None

    title = (raw.get("summary") or "(untitled)").strip()
    location = (raw.get("location") or "").strip()
    start = raw.get("start") or {}
    end = raw.get("end") or {}

    if "date" in start:
        try:
            start_date = date.fromisoformat(start["date"])
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

    start_dt = parse_dt(start.get("dateTime", ""))
    end_dt = parse_dt(end.get("dateTime", ""))
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
        "start": format_clock(start_local),
        "end": format_clock(end_local),
        "location": location,
    }
    minutes = start_local.hour * 60 + start_local.minute
    return (not ongoing, True, minutes), event


def load_creds() -> tuple[str, str, str] | None:
    """Resolve OAuth creds. Accepts either a single combined file (all three
    keys in GCAL_CREDS_PATH) or the split pattern (refresh_token in
    GCAL_CREDS_PATH; client_id/client_secret in GCAL_CLIENT_PATH, which may
    nest under an `installed` key per Google's OAuth client downloads)."""
    creds_path = Path(os.environ.get("GCAL_CREDS_PATH", DEFAULT_CREDS_PATH))
    try:
        creds = json.loads(creds_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    refresh_token = creds.get("refresh_token", "").strip()
    client_id = creds.get("client_id", "").strip()
    client_secret = creds.get("client_secret", "").strip()

    if not (client_id and client_secret):
        client_path = Path(os.environ.get("GCAL_CLIENT_PATH", DEFAULT_CLIENT_PATH))
        try:
            client = json.loads(client_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if "installed" in client:
            client_id = client["installed"].get("client_id", "").strip()
            client_secret = client["installed"].get("client_secret", "").strip()
        else:
            client_id = client.get("client_id", "").strip()
            client_secret = client.get("client_secret", "").strip()

    if not (refresh_token and client_id and client_secret):
        return None
    return client_id, client_secret, refresh_token


def fetch_calendar(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    calendar_ids: tuple[str, ...],
    day: date,
) -> list[dict] | None:
    if not (client_id and client_secret and refresh_token and calendar_ids):
        return None

    access_token = get_access_token(client_id, client_secret, refresh_token)
    if access_token is None:
        return None

    local_tz = datetime.now().astimezone().tzinfo
    day_start = datetime.combine(day, time.min, tzinfo=local_tz)
    day_end = day_start + timedelta(days=1)

    collected: list[tuple[tuple, dict]] = []
    for calendar_id in calendar_ids:
        items = fetch_events(
            calendar_id, access_token, day_start.isoformat(), day_end.isoformat()
        )
        if items is None:
            return None
        for raw in items:
            parsed = parse_event(raw, day, local_tz)
            if parsed is not None:
                collected.append(parsed)

    collected.sort(key=lambda pair: pair[0])
    return [event for _, event in collected]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch today's calendar events as JSON.")
    parser.add_argument(
        "--day",
        help="ISO date (default: today, local timezone).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.day:
        try:
            day = date.fromisoformat(args.day)
        except ValueError:
            json.dump({"events": [], "error": f"invalid --day: {args.day!r}"}, sys.stdout)
            return 0
    else:
        day = datetime.now().astimezone().date()

    calendar_ids_raw = os.environ.get("GCAL_CALENDAR_IDS", "").strip()
    if not calendar_ids_raw:
        json.dump({"events": [], "error": "GCAL_CALENDAR_IDS unset"}, sys.stdout)
        return 0
    calendar_ids = tuple(c.strip() for c in calendar_ids_raw.split(",") if c.strip())

    creds = load_creds()
    if creds is None:
        json.dump({"events": [], "error": "credentials missing or invalid"}, sys.stdout)
        return 0
    client_id, client_secret, refresh_token = creds

    events = fetch_calendar(client_id, client_secret, refresh_token, calendar_ids, day)
    if events is None:
        json.dump({"events": [], "error": "fetch failed"}, sys.stdout)
        return 0

    json.dump({
        "events": events,
        "source": "google-calendar",
        "day": day.isoformat(),
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
