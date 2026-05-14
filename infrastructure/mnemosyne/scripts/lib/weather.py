"""OpenWeatherMap fetcher for the Mnemosyne daily digest.

Pure stdlib. Library-shaped — no CLI, no prints, no exceptions raised
into callers. fetch_weather() returns a dict on success or None on any
failure (network, auth, parse, missing fields). The caller treats None
as "weather unavailable; omit the weather block silently" per the
digest's no-filler rule.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime

OWM_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT_SECONDS = 5


def _bucket_visibility(meters: int) -> str:
    """OpenWeather visibility is in meters and capped at 10000."""
    if meters > 9260:
        return "Clear"
    if meters > 3704:
        return "Moderate"
    if meters > 926:
        return "Poor"
    return "Very Poor"


def _format_clock(unix_ts: int, tz_offset_seconds: int) -> str:
    """Format a Unix timestamp into 'HH:MM AM/PM' in the location's local time.

    OpenWeather returns sunrise/sunset as UTC Unix timestamps plus a `timezone`
    field giving the location's offset in seconds. Applying the offset and
    formatting in UTC yields the local wall-clock time without pulling in
    pytz or zoneinfo.
    """
    local_ts = unix_ts + tz_offset_seconds
    return datetime.utcfromtimestamp(local_ts).strftime("%I:%M %p").lstrip("0")


def fetch_weather(
    lat: float,
    lon: float,
    api_key: str,
) -> dict | None:
    """Fetch current conditions from OpenWeatherMap.

    Returns a dict with fields: description, temp_f, feels_like_f, high_f,
    low_f, wind_mph, visibility (bucket label), sunrise, sunset. Or None on
    any failure.
    """
    if not api_key or lat is None or lon is None:
        return None

    query = urllib.parse.urlencode({
        "lat": f"{lat}",
        "lon": f"{lon}",
        "appid": api_key,
        "units": "imperial",
    })
    url = f"{OWM_ENDPOINT}?{query}"

    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    try:
        tz_offset = int(payload.get("timezone", 0))
        return {
            "description": payload["weather"][0]["description"].title(),
            "temp_f": round(payload["main"]["temp"]),
            "feels_like_f": round(payload["main"]["feels_like"]),
            "high_f": round(payload["main"]["temp_max"]),
            "low_f": round(payload["main"]["temp_min"]),
            "wind_mph": round(payload["wind"]["speed"], 1),
            "visibility": _bucket_visibility(int(payload.get("visibility", 0))),
            "sunrise": _format_clock(int(payload["sys"]["sunrise"]), tz_offset),
            "sunset": _format_clock(int(payload["sys"]["sunset"]), tz_offset),
        }
    except (KeyError, IndexError, TypeError, ValueError):
        return None
