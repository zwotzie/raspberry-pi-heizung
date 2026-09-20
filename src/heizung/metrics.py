"""
Prometheus metrics for the heizung daemon.

The daemon exposes one Gauge per sensor.  Metric names are identical to the
column names used by the frontend (keys_all in uvr-charts.js), so the API can
map Prometheus series back to the JS column order without a lookup table.

Start the HTTP server once (from control.py::run):
    from prometheus_client import start_http_server
    start_http_server(metrics_port)
"""

from __future__ import annotations

from prometheus_client import Gauge

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

_analog: dict[str, Gauge] = {
    name: Gauge(name, f"Heizung sensor: {name}") for name in ANALOG
}
_digital: dict[str, Gauge] = {
    name: Gauge(name, f"Heizung digital output: {name}") for name in DIGITAL
}

HEIZUNG_UP = Gauge("heizung_up", "1 if the daemon has data, 0 otherwise")
LAST_MEASUREMENT_TS = Gauge(
    "heizung_last_measurement_timestamp_seconds",
    "Unix timestamp of the most recent measurement",
)
OPERATING_MODE = Gauge(
    "heizung_operating_mode",
    "Current operating mode (1 = active mode, 0 = inactive)",
    ["mode"],
)

VALID_MODES = ("pellets", "firewood")


def set_measurement(mapping: dict, heizung_an: int = 0) -> None:
    """Populate all Gauges from a single measurement mapping."""
    for name in ANALOG:
        value = mapping.get(name)
        if value is not None:
            _analog[name].set(float(value))
    for name in DIGITAL[:-1]:  # heizung_an is handled below
        value = mapping.get(name, 0)
        _digital[name].set(float(value))
    _digital["heizung_an"].set(float(heizung_an))

    HEIZUNG_UP.set(1)
    ts = mapping.get("timestamp")
    if ts is not None:
        LAST_MEASUREMENT_TS.set(float(ts.timestamp()) if hasattr(ts, "timestamp") else float(ts))


def set_operating_mode(mode: str) -> None:
    for m in VALID_MODES:
        OPERATING_MODE.labels(mode=m).set(1 if m == mode else 0)
