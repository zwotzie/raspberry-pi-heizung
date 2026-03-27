"""
PostgreSQL storage layer for UVR1611 measurements.

Schema:  one row per measurement, columns match the key order expected
         by uvr-charts.js (keys_analog + keys_digital).
Access:  DB URL is read from the HEIZUNG_DB_URL environment variable or
         passed explicitly to each function.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import psycopg2
import psycopg2.extras

logger = logging.getLogger("heizung")

# ── column order must match keys_all in uvr-charts.js ─────────────────────────
COLUMNS_ANALOG: list[str] = [
    "kessel_rl",
    "kessel_d_ladepumpe",
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
    "heizung_d",
    "solar_strahlung",
    "solar_vl",
    "solar_d_ladepumpe",
]

COLUMNS_DIGITAL: list[str] = [
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

# All data columns in JS order (without measured_at)
DATA_COLUMNS: list[str] = COLUMNS_ANALOG + COLUMNS_DIGITAL

DDL = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO settings (key, value)
VALUES ('operating_mode', 'pellets')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS measurements (
    id                          BIGSERIAL       PRIMARY KEY,
    measured_at                 TIMESTAMPTZ     NOT NULL,

    -- analog sensors
    kessel_rl                   NUMERIC(6, 2),
    kessel_d_ladepumpe          NUMERIC(6, 2),
    kessel_betriebstemperatur   NUMERIC(6, 2),
    speicher_ladeleitung        NUMERIC(6, 2),
    aussentemperatur            NUMERIC(6, 2),
    raum_rasp                   NUMERIC(6, 2),
    speicher_1_kopf             NUMERIC(6, 2),
    speicher_2_kopf             NUMERIC(6, 2),
    speicher_3_kopf             NUMERIC(6, 2),
    speicher_4_mitte            NUMERIC(6, 2),
    speicher_5_boden            NUMERIC(6, 2),
    heizung_vl                  NUMERIC(6, 2),
    heizung_rl                  NUMERIC(6, 2),
    heizung_d                   NUMERIC(6, 2),
    solar_strahlung             NUMERIC(8, 2),
    solar_vl                    NUMERIC(6, 2),
    solar_d_ladepumpe           NUMERIC(6, 2),

    -- digital outputs
    d_heizung_pumpe             SMALLINT,
    d_kessel_ladepumpe          SMALLINT,
    d_kessel_freigabe           SMALLINT,
    d_heizung_mischer_auf       SMALLINT,
    d_heizung_mischer_zu        SMALLINT,
    d_kessel_mischer_auf        SMALLINT,
    d_kessel_mischer_zu         SMALLINT,
    d_solar_kreispumpe          SMALLINT,
    d_solar_ladepumpe           SMALLINT,
    d_solar_freigabepumpe       SMALLINT,
    heizung_an                  SMALLINT        DEFAULT 0,

    UNIQUE (measured_at)
);

CREATE INDEX IF NOT EXISTS idx_measurements_measured_at
    ON measurements (measured_at DESC);
"""


def _connect(db_url: str):
    return psycopg2.connect(db_url)


def init_db(db_url: str) -> None:
    """Create table and index if they don't exist yet."""
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(DDL)
    logger.info("db: schema initialised")


def insert(db_url: str, mapping: dict) -> None:
    """
    Insert one measurement row.  Silently ignores duplicate timestamps.

    :param mapping: dict with field names matching the DB columns;
                    must contain 'timestamp'; 'heizung_an' defaults to 0.
    """
    ts: datetime | None = mapping.get("timestamp")
    if ts is None:
        logger.warning("db.insert: mapping has no 'timestamp', skipping")
        return
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)

    row: dict[str, object] = {"measured_at": ts}
    for col in COLUMNS_ANALOG:
        row[col] = mapping.get(col)
    for col in COLUMNS_DIGITAL[:-1]:  # skip heizung_an
        row[col] = mapping.get(col, 0)
    row["heizung_an"] = mapping.get("heizung_an", 0)

    cols = ", ".join(row.keys())
    placeholders = ", ".join(f"%({k})s" for k in row)
    sql = f"""
        INSERT INTO measurements ({cols})
        VALUES ({placeholders})
        ON CONFLICT (measured_at) DO NOTHING
    """
    try:
        with _connect(db_url) as conn, conn.cursor() as cur:
            cur.execute(sql, row)
    except Exception as exc:
        logger.error("db.insert failed: %s", exc)


def query(db_url: str, date: str, period: str = "day") -> list[list]:
    """
    Return all rows for the requested time window as a list of lists.

    Column order matches keys_all in uvr-charts.js:
      [unix_timestamp, *analog_values, *digital_values]

    :param date:   ISO date string  YYYY-MM-DD
    :param period: 'day' or 'week'
    """
    start = datetime.fromisoformat(date).replace(tzinfo=UTC)
    end = start + timedelta(days=7 if period == "week" else 1)

    col_list = ", ".join(DATA_COLUMNS)
    sql = f"""
        SELECT measured_at, {col_list}
        FROM   measurements
        WHERE  measured_at >= %(start)s
          AND  measured_at <  %(end)s
        ORDER  BY measured_at
    """
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(sql, {"start": start, "end": end})
        rows = cur.fetchall()

    result = []
    for row in rows:
        r = list(row)
        r[0] = int(r[0].timestamp())  # datetime → Unix timestamp for JS
        result.append(r)
    return result


def get_setting(db_url: str, key: str, default: str | None = None) -> str | None:
    """Return the value of a settings key, or *default* if not found."""
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cur.fetchone()
    return row[0] if row else default


def upsert_setting(db_url: str, key: str, value: str) -> None:
    """Insert or update a settings key."""
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
            (key, value),
        )
