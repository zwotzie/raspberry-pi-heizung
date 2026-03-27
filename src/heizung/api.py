"""
FastAPI application – serves UVR1611 chart data for uvr-charts.js.

Start:
    uvicorn heizung.api:app --host 0.0.0.0 --port 8000

The application reads all configuration from ``etc/heizung.conf``.
Set the environment variable ``HEIZUNG_CONFIG_PATH`` to the directory
that contains ``etc/heizung.conf`` when the working directory differs
from the project root.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from heizung import db
from heizung.config import load_config

_cfg = load_config()


def _db_url() -> str:
    url = _cfg.get("db_url")
    if not url:
        raise RuntimeError("'db_url' is not set in heizung.conf")
    return str(url)


STATIC_DIR = Path(_cfg.get("static_dir") or Path(__file__).parent / "static")


class MeasurementIn(BaseModel):
    """One measurement row as sent by the heizung daemon."""

    timestamp: datetime
    # analog sensors
    kessel_rl: float | None = None
    kessel_d_ladepumpe: float | None = None
    kessel_betriebstemperatur: float | None = None
    speicher_ladeleitung: float | None = None
    aussentemperatur: float | None = None
    raum_rasp: float | None = None
    speicher_1_kopf: float | None = None
    speicher_2_kopf: float | None = None
    speicher_3_kopf: float | None = None
    speicher_4_mitte: float | None = None
    speicher_5_boden: float | None = None
    heizung_vl: float | None = None
    heizung_rl: float | None = None
    heizung_d: float | None = None
    solar_strahlung: float | None = None
    solar_vl: float | None = None
    solar_d_ladepumpe: float | None = None
    # digital outputs
    d_heizung_pumpe: int | None = None
    d_kessel_ladepumpe: int | None = None
    d_kessel_freigabe: int | None = None
    d_heizung_mischer_auf: int | None = None
    d_heizung_mischer_zu: int | None = None
    d_kessel_mischer_auf: int | None = None
    d_kessel_mischer_zu: int | None = None
    d_solar_kreispumpe: int | None = None
    d_solar_ladepumpe: int | None = None
    d_solar_freigabepumpe: int | None = None
    # derived
    heizung_an: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db(_db_url())
    yield


app = FastAPI(
    title="UVR Heizung API",
    description="Serves sensor data for uvr-charts.js Plotly dashboards.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.post(
    "/measurements",
    status_code=201,
    summary="Ingest one measurement from the heizung daemon",
)
def create_measurement(data: MeasurementIn) -> dict:
    db.insert(_db_url(), data.model_dump())
    return {"status": "ok"}


# ── Operating mode ────────────────────────────────────────────────────────────


class OperatingMode(str, Enum):
    pellets = "pellets"
    firewood = "firewood"


@app.get(
    "/settings/operating-mode",
    summary="Get current operating mode",
)
def get_operating_mode() -> dict:
    mode = db.get_setting(_db_url(), "operating_mode", "pellets")
    return {"operating_mode": mode}


@app.put(
    "/settings/operating-mode",
    summary="Set operating mode  [LAN-only via Traefik IP-allowlist]",
)
def set_operating_mode(mode: OperatingMode) -> dict:
    db.upsert_setting(_db_url(), "operating_mode", mode.value)
    return {"operating_mode": mode.value}


@app.get(
    "/analogChart.php",
    summary="Chart data compatible with uvr-charts.js",
    response_description="Array of rows: [unix_ts, *analog_values, *digital_values]",
    responses={400: {"description": "Invalid period, must be 'day' or 'week'"}},
)
def analog_chart(
    date: Annotated[str, Query(description="Date in YYYY-MM-DD format", example="2026-03-26")],
    id: Annotated[int, Query(description="Dataset id (4 = all sensors)")] = 4,
    period: Annotated[str, Query(description="'day' or 'week'")] = "day",
) -> list[list]:
    if period not in ("day", "week"):
        raise HTTPException(status_code=400, detail="period must be 'day' or 'week'")
    return db.query(_db_url(), date=date, period=period)


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
