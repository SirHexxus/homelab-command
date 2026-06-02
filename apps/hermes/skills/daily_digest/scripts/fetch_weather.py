#!/usr/bin/env python3
"""Fetch today's weather (current + forecast) for the daily digest.

Ported from infrastructure/mnemosyne/scripts/lib/weather.py — pure stdlib,
OpenWeather One Call 3.0 with silent fallback to 2.5 current.

Reads:
    OPENWEATHER_API_KEY — required
    WEATHER_LAT, WEATHER_LON — required, decimal degrees

Emits JSON to stdout: {"weather": {...}, "source": "openweather", "endpoint": "3.0"|"2.5"}
or {"weather": null, "error": "..."} on any failure (always exit 0;
no-filler rule treats missing weather as silently correct).

Usage:
    fetch_weather.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CURRENT_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
ONECALL_ENDPOINT = "https://api.openweathermap.org/data/3.0/onecall"
REQUEST_TIMEOUT_SECONDS = 5


def bucket_visibility(meters: int) -> str:
    if meters > 9260:
        return "Clear"
    if meters > 3704:
        return "Moderate"
    if meters > 926:
        return "Poor"
    return "Very Poor"


def format_clock(unix_ts: int, tz_offset_seconds: int) -> str:
    local_ts = unix_ts + tz_offset_seconds
    return (
        datetime.fromtimestamp(local_ts, tz=timezone.utc)
        .strftime("%I:%M %p")
        .lstrip("0")
    )


def get_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def fetch_onecall(lat: float, lon: float, api_key: str) -> dict | None:
    query = urllib.parse.urlencode({
        "lat": f"{lat}",
        "lon": f"{lon}",
        "appid": api_key,
        "units": "imperial",
        "exclude": "minutely,alerts",
    })
    payload = get_json(f"{ONECALL_ENDPOINT}?{query}")
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
            "visibility": bucket_visibility(int(current.get("visibility", 0))),
            "sunrise": format_clock(int(current["sunrise"]), tz_offset),
            "sunset": format_clock(int(current["sunset"]), tz_offset),
            "forecast_summary": today.get("summary", "").strip(),
            "day_description": today["weather"][0]["description"].title(),
            "pop_percent": round(float(today.get("pop", 0)) * 100),
        }
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def fetch_current(lat: float, lon: float, api_key: str) -> dict | None:
    query = urllib.parse.urlencode({
        "lat": f"{lat}",
        "lon": f"{lon}",
        "appid": api_key,
        "units": "imperial",
    })
    payload = get_json(f"{CURRENT_ENDPOINT}?{query}")
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
            "visibility": bucket_visibility(int(payload.get("visibility", 0))),
            "sunrise": format_clock(int(payload["sys"]["sunrise"]), tz_offset),
            "sunset": format_clock(int(payload["sys"]["sunset"]), tz_offset),
        }
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def main() -> int:
    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    raw_lat = os.environ.get("WEATHER_LAT", "").strip()
    raw_lon = os.environ.get("WEATHER_LON", "").strip()

    if not (api_key and raw_lat and raw_lon):
        json.dump({
            "weather": None,
            "error": "OPENWEATHER_API_KEY / WEATHER_LAT / WEATHER_LON unset",
        }, sys.stdout)
        return 0

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
    except ValueError:
        json.dump({"weather": None, "error": "WEATHER_LAT/LON not numeric"}, sys.stdout)
        return 0

    weather = fetch_onecall(lat, lon, api_key) or fetch_current(lat, lon, api_key)
    if weather is None:
        json.dump({"weather": None, "error": "both endpoints failed"}, sys.stdout)
        return 0

    endpoint = weather.pop("source")
    json.dump({
        "weather": weather,
        "source": "openweather",
        "endpoint": endpoint,
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
