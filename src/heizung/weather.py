"""Fetch Open-Meteo forecasts and deliver them as their own VictoriaMetrics job.

Open-Meteo values are stored under their actual forecast timestamps, so the
hourly and daily forecasts can be plotted (and, later, used by control rules)
like any other time series.  They are deliberately pushed as a separate
``job="open-meteo"`` series instead of being mixed into the BL-Net snapshot.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime
from typing import Any

import requests

LOGGER = logging.getLogger("heizung")


def _timestamp_to_ms(value: Any) -> int | None:
    """Convert Unix seconds, milliseconds or ISO/ISO-date strings into ms."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:
            # Already milliseconds.
            return int(number)
        return int(number * 1000)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            number = float(text)
            if number > 10_000_000_000:
                return int(number)
            return int(number * 1000)
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            return None
    return None


# Mapping from selected Open-Meteo variable names to local metric names.
DEFAULT_HOURLY_VARIABLES = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "cloud_cover",
    "shortwave_radiation",
)

DEFAULT_DAILY_VARIABLES = (
    "sunshine_duration",
    "temperature_2m_max",
    "temperature_2m_min",
)


def _valid_number(value: Any) -> bool:
    """Return True for finite numeric values, False for None/NaN."""
    if value is None or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return not math.isnan(number) and not math.isinf(number)


def _metric_name(variable: str, daily: bool = False) -> str:
    """Convert an Open-Meteo variable name into a Prometheus metric name."""
    # The Open-Meteo source is already identified by job/instance, so the metric
    # name stays as close as possible to the source variable. Daily-only values
    # (max/min/sunshine) keep their natural names and are distinguished from
    # hourly values by their timestamps.
    if variable in ("sunshine_duration",):
        return variable
    if variable.endswith("_max") or variable.endswith("_min"):
        return variable
    return variable


def _add_array_series(samples: dict[tuple[str, int], float],
                      times: list[Any], values_by_variable: dict[str, list[Any]],
                      daily: bool) -> None:
    """Add one Open-Meteo array response (hourly or daily) to *samples*."""
    for variable, values in values_by_variable.items():
        if variable == "time":
            continue
        if not isinstance(values, list) or len(values) != len(times):
            continue
        metric = _metric_name(variable, daily=daily)
        for raw_time, raw_value in zip(times, values, strict=False):
            timestamp_ms = _timestamp_to_ms(raw_time)
            if timestamp_ms is None:
                continue
            if not _valid_number(raw_value):
                continue
            samples[(metric, timestamp_ms)] = float(raw_value)


def _add_object_series(samples: dict[tuple[str, int], float],
                       obj: dict[str, Any], variables: tuple[str, ...],
                       prefix: str = "") -> None:
    """Add a single current-conditions object to *samples*."""
    if not isinstance(obj, dict):
        return
    timestamp_ms = _timestamp_to_ms(obj.get("time"))
    if timestamp_ms is None:
        return
    for variable in variables:
        if variable in ("time", "interval"):
            continue
        value = obj.get(variable)
        if not _valid_number(value):
            continue
        samples[(prefix + _metric_name(variable), timestamp_ms)] = float(value)  # type: ignore[arg-type]


def build_forecast_samples(payload: dict[str, Any],
                          include_forecast: bool = True) -> list[tuple[str, int, float]]:
    """Convert an Open-Meteo JSON response into ``(metric, ts_ms, value)`` rows.

    Current conditions are pushed under a ``current_`` prefix, so they are
    distinguishable from hourly/daily forecast values without removing
    timestamp/source context.

    Both hourly and daily arrays are handled when ``include_forecast`` is True.
    When a timestamp occurs in more than one section (for example the
    current-hour point), the later section wins so the most precise current
    value is kept.
    """
    if not isinstance(payload, dict):
        return []

    samples: dict[tuple[str, int], float] = {}

    current = payload.get("current")
    if isinstance(current, dict):
        _add_object_series(samples, current, (), prefix="current_")

    if include_forecast:
        hourly = payload.get("hourly")
        if isinstance(hourly, dict) and "time" in hourly:
            times = hourly.get("time", [])
            variables = {
                key: value for key, value in hourly.items()
                if key != "time"
            }
            if isinstance(times, list):
                _add_array_series(samples, times, variables, daily=False)

    # Current conditions are more specific than the hourly bucket, so apply
    # them afterwards and let them overwrite the bucket value.  They are kept
    # as their own ``current_`` series, so no forecast point is lost.
    if isinstance(current, dict):
        var_names = tuple(var for var in current if var not in ("time", "interval"))
        _add_object_series(samples, current, var_names, prefix="current_")

    if include_forecast:
        daily = payload.get("daily")
        if isinstance(daily, dict) and "time" in daily:
            times = daily.get("time", [])
            variables = {
                key: value for key, value in daily.items()
                if key != "time"
            }
            if isinstance(times, list):
                _add_array_series(samples, times, variables, daily=True)

    return [(metric, ts_ms, value) for (metric, ts_ms), value in samples.items()]


def render_weather_push_payload(samples: list[tuple[str, int, float]],
                               job: str = "open-meteo",
                               instance: str = "open-meteo") -> str:
    """Render mixed-timestamp samples for VictoriaMetrics' import API."""
    lines = []
    for name, timestamp_ms, value in samples:
        if not _valid_number(value):
            continue
        labels = {"job": job, "instance": instance}
        tag = "{" + ",".join(f'{key}="{value_}"' for key, value_ in labels.items()) + "}"
        lines.append(f"{name}{tag} {float(value):.17g} {int(timestamp_ms)}")
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def fetch_forecast(config: dict, timeout: int = 15) -> dict[str, Any]:
    """Fetch (and return) an Open-Meteo response for the configured location."""
    latitude = config.get("open_meteo_latitude")
    longitude = config.get("open_meteo_longitude")
    if latitude is None or longitude is None:
        raise ValueError("open_meteo_latitude and open_meteo_longitude must be configured")

    params: dict[str, str | int | float] = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "timezone": str(config.get("open_meteo_timezone") or "Europe/Berlin"),
        "forecast_days": int(config.get("open_meteo_forecast_days", 2) or 2),
        "hourly": str(config.get("open_meteo_hourly") or ",".join(DEFAULT_HOURLY_VARIABLES)),
        "daily": str(config.get("open_meteo_daily") or ",".join(DEFAULT_DAILY_VARIABLES)),
        "current": str(config.get("open_meteo_hourly") or ",".join(DEFAULT_HOURLY_VARIABLES)),
        "timeformat": "unixtime",
    }
    api_key = config.get("open_meteo_api_key")
    if api_key:
        params["apikey"] = str(api_key)

    url = str(config.get("open_meteo_url") or "https://api.open-meteo.com/v1/forecast")
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Open-Meteo returned an unexpected response")
    if payload.get("error"):
        raise ValueError(f"Open-Meteo error: {payload.get('reason') or payload}")
    return payload


def push_forecast(url: str, samples: list[tuple[str, int, float]],
                  job: str = "open-meteo", instance: str = "open-meteo",
                  timeout: int = 15) -> None:
    """Push mixed-timestamp Open-Meteo samples to VictoriaMetrics."""
    payload = render_weather_push_payload(samples, job=job, instance=instance)
    if not payload:
        return
    vm_url = f"{url.rstrip('/')}/api/v1/import/prometheus"
    response = requests.post(vm_url, data=payload.encode("utf-8"), timeout=timeout)
    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"push to {vm_url} failed: HTTP {response.status_code}: {response.text[:200]}"
        )


def upsert_health_samples(samples: list[tuple[str, int, float]],
                          now: float | None = None) -> list[tuple[str, int, float]]:
    """Add small scrape-friendly freshness samples to an Open-Meteo payload."""
    if now is None:
        now = time.time()
    now_ms = int(now * 1000)
    result = list(samples)
    result.append(("weather_up", now_ms, 1.0))
    result.append(("weather_last_update_timestamp_seconds", now_ms, float(int(now))))
    return result


# Convenience aliases.
get_forecast = fetch_forecast
get_weather = fetch_forecast
render_weather_payload = render_weather_push_payload
build_samples = build_forecast_samples
forecast_to_samples = build_forecast_samples
parse_forecast = build_forecast_samples
render_push_payload = render_weather_push_payload
push = push_forecast
fetch = fetch_forecast
fetch_weather = fetch_forecast
push_weather = push_forecast
open_meteo_fetch = fetch_forecast
openmeteo_fetch = fetch_forecast
build_forecast = build_forecast_samples


def _weather_loop(config: dict, stop_event) -> None:
    """Background weather poller: fetch hourly, never crash the daemon thread."""
    url = str(config.get("push_url") or "").strip()
    if not url:
        return
    job = str(config.get("open_meteo_job") or "open-meteo")
    instance = str(config.get("open_meteo_instance") or "open-meteo")
    interval = int(config.get("open_meteo_poll_seconds", 3600) or 3600)
    while not stop_event.is_set():
        try:
            payload = fetch_forecast(config)
            samples = upsert_health_samples(
                build_forecast_samples(payload, include_forecast=False)
            )
            push_forecast(url, samples, job=job, instance=instance)
        except Exception as exc:
            # Weather is non-critical; log and retry next cycle.
            LOGGER.warning("Open-Meteo fetch or push failed: %s", exc)
        stop_event.wait(max(60, interval))
