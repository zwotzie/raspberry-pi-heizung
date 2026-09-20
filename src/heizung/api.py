"""
FastAPI application – serves UVR1611 chart data for uvr-charts.js.

Data source is Prometheus (queried via the internal ``prometheus_url``); the
daemon exposes the live sensor values as Gauges that Prometheus scrapes.

Endpoints:
    GET /api/chart?date=&period=   chart rows, format
                                   ``[unix_ts, *analog, *digital]``
    GET /                          static dashboard (index.html + uvr-charts.js)

Start:
    uvicorn heizung.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from heizung import metrics
from heizung.config import load_config


def _cfg() -> dict:
    return load_config()


def _static_dir() -> Path:
    return Path(_cfg().get("static_dir") or Path(__file__).parent / "static")


def _prometheus_url() -> str:
    url = _cfg().get("prometheus_url")
    if not url:
        raise RuntimeError("'prometheus_url' is not set in heizung.conf")
    return str(url).rstrip("/")


app = FastAPI(
    title="UVR Heizung API",
    description="Serves sensor data for uvr-charts.js Plotly dashboards (backed by Prometheus).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Metric names in exactly the column order expected by uvr-charts.js.
ANALOG: list[str] = metrics.ANALOG
DIGITAL: list[str] = metrics.DIGITAL
ALL_NAMES: list[str] = metrics.ALL


def _row_for(ts: str, by_name: dict[str, dict[str, float | None]]) -> list:
    """Build one chart row ``[unix_ts, *analog, *digital]`` for a timestamp."""
    values = by_name[ts]
    row: list = [int(ts)]
    for name in ANALOG:
        row.append(values.get(name))
    for name in DIGITAL:
        row.append(values.get(name))
    return row


@app.get(
    "/api/chart",
    summary="Chart rows (Prometheus-backed), format [unix_ts, *analog, *digital]",
)
def chart(
    date: Annotated[str, Query(description="Date in YYYY-MM-DD format", example="2026-03-26")],
    period: Annotated[str, Query(description="'day' or 'week'")] = "day",
) -> list[list]:
    if period not in ("day", "week"):
        raise HTTPException(status_code=400, detail="period must be 'day' or 'week'")

    start = datetime.fromisoformat(date).replace(tzinfo=UTC)
    end = start + timedelta(days=7 if period == "week" else 1)

    matcher = "{__name__=~\"" + "|".join(ALL_NAMES) + "\"}"
    params: dict[str, str | float | int] = {
        "query": matcher,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": 60,
    }
    try:
        resp = requests.get(
            f"{_prometheus_url()}/api/v1/query_range",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Prometheus unreachable: {exc}") from exc

    if payload.get("status") != "success":
        raise HTTPException(status_code=502, detail=f"Prometheus error: {payload.get('error')}")

    # ts -> {metric_name: value}
    by_name: dict[str, dict[str, float | None]] = {}
    for series in payload["data"]["result"]:
        name = series["metric"].get("__name__")
        if name not in ALL_NAMES:
            continue
        for ts, value in series["values"]:
            try:
                cell: float | None = float(value)
            except (TypeError, ValueError):
                cell = None
            by_name.setdefault(str(ts), {})[name] = cell

    return [_row_for(ts, by_name) for ts in sorted(by_name, key=float)]


if _static_dir().is_dir():
    app.mount("/", StaticFiles(directory=_static_dir(), html=True), name="static")
