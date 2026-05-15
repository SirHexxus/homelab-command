"""OpenWeatherMap fetcher for the Mnemosyne daily digest.

Pure stdlib. Library-shaped — no CLI, no prints, no exceptions raised
into callers. fetch_weather() returns a dict on success or None on any
failure (network, auth, parse, missing fields). The caller treats None
as "weather unavailable; omit the weather block silently" per the
digest's no-filler rule.

Dual-endpoint behaviour: fetch_weather() tries the One Call 3.0 endpoint
first, which yields current conditions plus today's forecast arc. One
Call 3.0 requires the "One Call by Call" subscription; if it is not
active (HTTP 401) or any other failure occurs, the fetch silently falls
back to the 2.5 current-weather endpoint. The returned dict carries a
`source` key ("3.0" or "2.5") so callers can render the forecast fields
only when they are present.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

CURRENT_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
ONECALL_ENDPOINT = "https://api.openweathermap.org/data/3.0/onecall"
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

    OpenWeather returns sunrise/sunset as UTC Unix timestamps plus a timezone
    offset in seconds. Applying the offset and formatting in UTC yields the
    local wall-clock time without pulling in pytz or zoneinfo.
    """
    local_ts = unix_ts + tz_offset_seconds
    return datetime.utcfromtimestamp(local_ts).strftime("%I:%M %p").lstrip("0")


def _get_json(url: str) -> dict | None:
    """GET a URL and parse JSON. None on any network/parse failure."""
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _fetch_onecall(lat: float, lon: float, api_key: str) -> dict | None:
    """Fetch current conditions plus today's forecast from One Call 3.0.

    Returns the 2.5-compatible fields plus `source: "3.0"` and forecast
    fields (forecast_summary, day_description, morn_f, eve_f, pop_percent).
    None on any failure — including HTTP 401 when the "One Call by Call"
    subscription is not active, which lets fetch_weather() fall back to 2.5.
    """
    query = urllib.parse.urlencode({
        "lat": f"{lat}",
        "lon": f"{lon}",
        "appid": api_key,
        "units": "imperial",
        "exclude": "minutely,alerts",
    })
    payload = _get_json(f"{ONECALL_ENDPOINT}?{query}")
    if payload is None:
        return None

    try:
        tz_offset = int(payload.get("timezone_offset", 0))
        current = payload["current"]
        today = payload["daily"][0]
        return {
            "source": "3.0",
            "description": current["weather"][0]["description"].title(),
            "temp_f": round(current["temp"]),
            "feels_like_f": round(current["feels_like"]),
            "high_f": round(today["temp"]["max"]),
            "low_f": round(today["temp"]["min"]),
            "morn_f": round(today["temp"]["morn"]),
            "eve_f": round(today["temp"]["eve"]),
            "wind_mph": round(current["wind_speed"], 1),
            "visibility": _bucket_visibility(int(current.get("visibility", 0))),
            "sunrise": _format_clock(int(current["sunrise"]), tz_offset),
            "sunset": _format_clock(int(current["sunset"]), tz_offset),
            "forecast_summary": today.get("summary", "").strip(),
            "day_description": today["weather"][0]["description"].title(),
            "pop_percent": round(float(today.get("pop", 0)) * 100),
        }
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _fetch_current(lat: float, lon: float, api_key: str) -> dict | None:
    """Fetch current conditions from the 2.5 weather endpoint.

    Fallback path when One Call 3.0 is unavailable. Returns the dict with
    `source: "2.5"` and no forecast fields. None on any failure.
    """
    query = urllib.parse.urlencode({
        "lat": f"{lat}",
        "lon": f"{lon}",
        "appid": api_key,
        "units": "imperial",
    })
    payload = _get_json(f"{CURRENT_ENDPOINT}?{query}")
    if payload is None:
        return None

    try:
        tz_offset = int(payload.get("timezone", 0))
        return {
            "source": "2.5",
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


def fetch_weather(
    lat: float,
    lon: float,
    api_key: str,
) -> dict | None:
    """Fetch weather, preferring One Call 3.0 and falling back to 2.5.

    Returns a dict with at least: source, description, temp_f, feels_like_f,
    high_f, low_f, wind_mph, visibility, sunrise, sunset. When source is
    "3.0" it also carries morn_f, eve_f, forecast_summary, day_description,
    and pop_percent. Returns None only when both endpoints fail.
    """
    if not api_key or lat is None or lon is None:
        return None
    return (
        _fetch_onecall(lat, lon, api_key)
        or _fetch_current(lat, lon, api_key)
    )
