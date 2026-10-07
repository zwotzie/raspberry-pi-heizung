"""
Prometheus metrics for the heizung daemon.

Sensors are exposed as Gauges by a custom collector that renders the
latest snapshot on every scrape.  If the snapshot is older than ``stale_after``
seconds (BL-Net unreachable) the sensor samples are omitted, so Prometheus marks
the series stale instead of serving old values as if they were current.

Metric names are identical to the
column names used by the frontend (keys_all in uvr-charts.js), so the API can
map Prometheus series back to the JS column order without a lookup table.

Start the HTTP server once (from control.py::run):
    from prometheus_client import start_http_server
    start_http_server(metrics_port)
"""

from __future__ import annotations

import threading
import time

from prometheus_client import REGISTRY, Gauge
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


class _State:
    """Thread-safe snapshot shared between the poller and the collector."""

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


_state = _State()


class HeizungCollector:
    """Renders the latest BL-Net snapshot; emits no sensor samples once stale."""

    def collect(self):
        """Yield the metric families for one Prometheus scrape."""
        with _state.lock:
            values = dict(_state.values)
            fetched_at = _state.fetched_at
            heizung_an = _state.heizung_an
            errors = _state.poll_errors
            duration = _state.poll_duration
            stale_after = _state.stale_after

        now = time.time()
        age = None if fetched_at is None else max(0.0, now - fetched_at)
        fresh = age is not None and age <= stale_after

        up = GaugeMetricFamily("heizung_up", "1 if the latest BL-Net data is fresh, 0 otherwise")
        up.add_metric([], 1 if fresh else 0)
        yield up

        errs = CounterMetricFamily("heizung_poll_errors", "Failed BL-Net polls")
        errs.add_metric([], errors)
        yield errs

        if age is not None:
            g_age = GaugeMetricFamily(
                "heizung_data_age_seconds", "Seconds since the last successful BL-Net poll"
            )
            g_age.add_metric([], age)
            yield g_age
            last = GaugeMetricFamily(
                "heizung_last_measurement_timestamp_seconds",
                "Unix timestamp of the most recent successful BL-Net poll",
            )
            last.add_metric([], fetched_at)
            yield last
        if duration is not None:
            d = GaugeMetricFamily("heizung_poll_duration_seconds", "Duration of the last BL-Net poll")
            d.add_metric([], duration)
            yield d

        if not fresh:
            return
        for name in ALL:
            if name == "heizung_an":
                value = heizung_an
            else:
                value = values.get(name)
            if value is None:
                continue
            fam = GaugeMetricFamily(name, f"Heizung sensor: {name}")
            fam.add_metric([], float(value))
            yield fam


REGISTRY.register(HeizungCollector())

OPERATING_MODE = Gauge(
    "heizung_operating_mode",
    "Current operating mode (1 = active mode, 0 = inactive)",
    ["mode"],
)

VALID_MODES = ("pellets", "firewood")


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
    """Mark a mode as active (1) and the other valid modes as inactive (0).

    Args:
        mode: Operating mode, one of ``VALID_MODES``.
    """
    for m in VALID_MODES:
        OPERATING_MODE.labels(mode=m).set(1 if m == mode else 0)
