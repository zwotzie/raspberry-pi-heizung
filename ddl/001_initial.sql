-- migrations/001_initial.sql
-- Run once on the PostgreSQL server to set up the heizung schema.
--
-- Example:
--   psql -U heizung -d heizung -f migrations/001_initial.sql

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- default operating mode; update via API to switch without restarting the daemon
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

    -- digital outputs (0 = off, 1 = on)
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

    -- heizung_an: 1 when boiler relay is closed (firing active)
    heizung_an                  SMALLINT        DEFAULT 0,

    UNIQUE (measured_at)
);

CREATE INDEX IF NOT EXISTS idx_measurements_measured_at
    ON measurements (measured_at DESC);

-- ── helper functions (mirror the API query logic) ────────────────────────────
-- Usage:
--   SELECT * FROM measurements_for_day('2026-03-26');
--   SELECT * FROM measurements_for_week('2026-03-26');

CREATE OR REPLACE FUNCTION measurements_for_day(p_date DATE)
RETURNS SETOF measurements
LANGUAGE sql STABLE AS
$$
    SELECT *
    FROM   measurements
    WHERE  measured_at >= p_date::TIMESTAMPTZ
      AND  measured_at <  (p_date + INTERVAL '1 day')::TIMESTAMPTZ
    ORDER  BY measured_at;
$$;

CREATE OR REPLACE FUNCTION measurements_for_week(p_date DATE)
RETURNS SETOF measurements
LANGUAGE sql STABLE AS
$$
    SELECT *
    FROM   measurements
    WHERE  measured_at >= p_date::TIMESTAMPTZ
      AND  measured_at <  (p_date + INTERVAL '7 days')::TIMESTAMPTZ
    ORDER  BY measured_at;
$$;
