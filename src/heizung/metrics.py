"""
Prometheus metrics for the heizung daemon.

The latest BL-Net snapshot is rendered through the shared ``_families()``
selection and can reach the TSDB two ways:

* **scrape mode (default)**: a custom collector registered in the
  ``REGISTRY`` is exposed by a local HTTP server (``start_http_server``)
  that Prometheus / VictoriaMetrics scrapt, or
* **push mode** (optional ``push_url`` in ``heizung.conf``): ``push()``
  POSTs the same sample set to VictoriaMetrics'
  ``/api/v1/import/prometheus`` API after every poll.

If the snapshot is older than ``stale_after`` seconds (BL-Net unreachable)
the sensor samples are omitted, so the stored series ends instead of
serving old values as if they were current.

Metric names are identical to the
column names used by the frontend (keys_all in uvr-charts.js), so the API can
map Prometheus series back to the JS column order without a lookup table.
"""

from __future__ import annotations

import threading
import time

import requests
from prometheus_client import REGISTRY
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

# ── metric names (must match keys_all order in uvr-charts.js) ────────────────
ANALOG: list[str] = [
    "kessel_rl",
    "kessel_ladepumpe_drehzahl",
    "kessel_betriebstemperatur",
    "speicher_ladeleitung",
    "aussentemperatur",
    "raum_rasp",
    "speicher_1_kopf",
    "speicher_2_kopf",
    "speicher_3_kopf",
    "speicher_4_mitte",
    "speicher_5_boden",
    "heizung_vl",
    "heizung_rl",
    "heizung_pumpe_drehzahl",
    "solar_strahlung",
    "solar_vl",
    "solar_ladepumpe_drehzahl",
]

DIGITAL: list[str] = [
    "d_heizung_pumpe",
    "d_kessel_ladepumpe",
    "d_kessel_freigabe",
    "d_heizung_mischer_auf",
    "d_heizung_mischer_zu",
    "d_kessel_mischer_auf",
    "d_kessel_mischer_zu",
    "d_solar_kreispumpe",
    "d_solar_ladepumpe",
    "d_solar_freigabepumpe",
    "heizung_an",
]

ALL = ANALOG + DIGITAL

DEFAULT_STALE_AFTER = 180.0

# Logical counter name; stored/exported as ``heizung_poll_errors_total``.
POLL_ERRORS = "heizung_poll_errors"

# Help strings for the fixed (non-sensor) metrics.
HELP: dict[str, str] = {
    "heizung_up": "1 if the latest BL-Net data is fresh, 0 otherwise",
    POLL_ERRORS: "Failed BL-Net polls",
    "heizung_data_age_seconds": "Seconds since the last successful BL-Net poll",
    "heizung_last_measurement_timestamp_seconds": "Unix timestamp of the most recent successful BL-Net poll",
    "heizung_poll_duration_seconds": "Duration of the last BL-Net poll",
    "heizung_operating_mode": "Current operating mode (1 = active mode, 0 = inactive)",
}

VALID_MODES = ("pellets", "firewood")


class _State:
    """Thread-safe snapshot shared between the poller and the collectors."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        """Reset all values to their initial (no data yet) state."""
        self.values: dict[str, float] = {}
        self.fetched_at: float | None = None  # time.time() of last successful poll
        self.heizung_an = 0
        self.poll_errors = 0
        self.poll_duration: float | None = None
        self.stale_after = DEFAULT_STALE_AFTER
        self.operating_mode: str | None = None


_state = _State()


def _families() -> list[tuple[str, float, dict[str, str]]]:
    """Return the current metric selection as ``(name, value, labels)`` tuples.

    This is the single source of truth for both the scrape collector and the
    push payload.  Sensor values and sensor-related health metrics are omitted
    once the snapshot is stale, so the stored series stops instead of
    continuing with old values.
    """
    with _state.lock:
        values = dict(_state.values)
        fetched_at = _state.fetched_at
        heizung_an = _state.heizung_an
        errors = _state.poll_errors
        duration = _state.poll_duration
        stale_after = _state.stale_after
        operating_mode = _state.operating_mode

    now = time.time()
    age = None if fetched_at is None else max(0.0, now - fetched_at)
    fresh = age is not None and age <= stale_after

    fams: list[tuple[str, float, dict[str, str]]] = [
        ("heizung_up", 1.0 if fresh else 0.0, {}),
        (POLL_ERRORS, float(errors), {}),
    ]
    if age is not None:
        assert fetched_at is not None
        fams.append(("heizung_data_age_seconds", age, {}))
        fams.append(("heizung_last_measurement_timestamp_seconds", float(fetched_at), {}))
    if duration is not None:
        fams.append(("heizung_poll_duration_seconds", duration, {}))

    for mode in VALID_MODES:
        fams.append(
            ("heizung_operating_mode", 1.0 if mode == operating_mode else 0.0, {"mode": mode})
        )

    if not fresh:
        return fams

    for name in ALL:
        if name == "heizung_an":
            value: float = float(heizung_an)
        else:
            raw = values.get(name)
            if raw is None:
                continue
            value = float(raw)
        fams.append((name, value, {}))
    return fams


class HeizungCollector:
    """Renders the latest BL-Net snapshot; emits no sensor samples once stale."""

    def collect(self):
        """Yield the metric families for one Prometheus scrape."""
        for name, value, labels in _families():
            if name == POLL_ERRORS:
                fam: CounterMetricFamily | GaugeMetricFamily = CounterMetricFamily(
                    POLL_ERRORS, HELP[POLL_ERRORS]
                )
            else:
                # label *names* go into the constructor (prometheus_client API).
                fam = GaugeMetricFamily(
                    name, HELP.get(name, f"Heizung sensor: {name}"), labels=list(labels)
                )
            fam.add_metric(list(labels.values()), value)
            yield fam


REGISTRY.register(HeizungCollector())


def _export_name(name: str) -> str:
    """Stored series name in the TSDB (Counter gains the ``_total`` suffix)."""
    return name + "_total" if name == POLL_ERRORS else name


def render_push_payload(
    job: str = "heizung",
    instance: str = "heizung",
    timestamp_ms: int | None = None,
) -> str:
    """Render the current sample set as Prometheus text lines for the import API.

    Each line is ``name{job="…",instance="…",…} value ts_ms``; the whole
    payload shares a single millisecond timestamp, matching the format
    VictoriaMetrics' ``/api/v1/import/prometheus`` expects (see
    ``tools/backfill_to_victoriametrics.py``).

    Args:
        job: Value of the ``job`` label.
        instance: Value of the ``instance`` label.
        timestamp_ms: Millisecond timestamp for all samples; ``time.time()``
            when None.
    """
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)
    lines = []
    for name, value, labels in _families():
        all_labels = {"job": job, "instance": instance, **labels}
        tag = "{" + ",".join(f'{k}="{v}"' for k, v in all_labels.items()) + "}"
        lines.append(f"{_export_name(name)}{tag} {value:.17g} {timestamp_ms}")
    return "\n".join(lines) + "\n"


def push(vm_url: str, job: str = "heizung", instance: str = "heizung", timeout: int = 15) -> None:
    """Push the current sample set to VictoriaMetrics' import API.

    Args:
        vm_url: Base URL of the VictoriaMetrics instance, e.g.
            ``http://victoriametrics.lan:8428``.
        job: Value of the ``job`` label.
        instance: Value of the ``instance`` label.
        timeout: HTTP timeout in seconds.

    Raises:
        RuntimeError: If the server responds with a non-2xx status code.
    """
    url = f"{vm_url.rstrip('/')}/api/v1/import/prometheus"
    resp = requests.post(
        url, data=render_push_payload(job, instance).encode(), timeout=timeout
    )
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"push to {url} failed: HTTP {resp.status_code}: {resp.text[:200]}")


def configure(stale_after: float) -> None:
    """Set the age after which sensor values are no longer exposed.

    Args:
        stale_after: Maximum data age in seconds.
    """
    with _state.lock:
        _state.stale_after = float(stale_after)


def set_measurement(mapping: dict, heizung_an: int = 0, duration: float | None = None) -> None:
    """Store a successful poll; missing sensors are not invented.

    Args:
        mapping: Measurement dict keyed by metric name.
        heizung_an: 1 if firing is active, else 0.
        duration: Duration of the poll in seconds.
    """
    values = {
        name: float(mapping[name]) for name in ALL if name != "heizung_an" and mapping.get(name) is not None
    }
    with _state.lock:
        _state.values = values
        _state.fetched_at = time.time()
        _state.heizung_an = int(heizung_an)
        if duration is not None:
            _state.poll_duration = duration


def set_heizung_an(value: int) -> None:
    """Update the firing-active flag.

    Args:
        value: 1 if firing is active, else 0.
    """
    with _state.lock:
        _state.heizung_an = int(value)


def record_poll_failure(duration: float | None = None) -> None:
    """Count a failed poll and optionally store its duration.

    Args:
        duration: Duration of the failed poll in seconds.
    """
    with _state.lock:
        _state.poll_errors += 1
        if duration is not None:
            _state.poll_duration = duration


def set_operating_mode(mode: str) -> None:
    """Store the currently active operating mode.

    Args:
        mode: Operating mode, one of ``VALID_MODES``.
    """
    with _state.lock:
        _state.operating_mode = mode
