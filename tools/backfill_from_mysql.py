#!/usr/bin/env python3
"""Export historical UVR1611 measurements from MySQL to OpenMetrics files.

Reads the ``t_data`` table (one row per ``frame1`` measurement) over a local
MySQL connection (typically behind an SSH tunnel, e.g. ``ssh -L 13306:3306
user@host``), maps the generic ``analog1..16`` / ``digital1..16`` / ``speed1..4``
columns onto the Prometheus metric names used by ``src/heizung/metrics.py`` and
writes one OpenMetrics text file per calendar year.

Each output file ends with ``# EOF`` and is ready for::

    promtool tsdb create-blocks-from openmetrics heizung-2015.openmetrics /tmp/blocks \
        --label job=heizung --label instance=heizung

See ``tools/README.md`` for the full workflow.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import pymysql
except ImportError as exc:  # pragma: no cover - depends on install
    sys.stderr.write(
        "pymysql is not installed. Install the backfill extra first:\n"
        "    uv sync --extra backfill\n"
    )
    raise SystemExit(1) from exc


# ── column → metric mapping (see tools/README.md for the source) ───────────────
ANALOG_MAP: dict[str, str] = {
    "analog1": "aussentemperatur",
    "analog2": "speicher_1_kopf",
    "analog3": "speicher_2_kopf",
    "analog4": "speicher_3_kopf",
    "analog5": "speicher_5_boden",
    "analog6": "speicher_ladeleitung",
    "analog7": "kessel_betriebstemperatur",
    "analog8": "raum_rasp",
    "analog9": "kessel_rl",
    "analog10": "heizung_vl",
    "analog11": "heizung_rl",
    "analog13": "solar_vl",
    "analog15": "solar_strahlung",
    "analog16": "speicher_4_mitte",
}
SPEED_MAP: dict[str, str] = {
    "speed2": "kessel_ladepumpe_drehzahl",
    "speed3": "heizung_pumpe_drehzahl",
    "speed4": "solar_ladepumpe_drehzahl",
}
DIGITAL_MAP: dict[str, str] = {
    "digital1": "heizung_an",
    "digital2": "d_kessel_ladepumpe",
    "digital3": "d_solar_ladepumpe",
    "digital4": "d_solar_kreispumpe",
    "digital5": "d_kessel_freigabe",
    "digital6": "d_heizung_pumpe",
    "digital7": "d_solar_freigabepumpe",
    "digital8": "d_kessel_mischer_auf",
    "digital9": "d_kessel_mischer_zu",
    "digital10": "d_heizung_mischer_auf",
    "digital11": "d_heizung_mischer_zu",
}

# Ordered so the emitted samples per timestamp are stable (analog → speed → digital).
ALL_MAP: dict[str, str] = {**ANALOG_MAP, **SPEED_MAP, **DIGITAL_MAP}


def _num(value: Any) -> float | None:
    """Convert a DB value to a finite float, or None if unusable."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):  # NaN / inf
        return None
    return result


def format_value(value: float) -> str:
    """Render a float without a trailing-`.0` surprise and without scientific drift."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.10g}"


def render_row(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Map one DB row to (year, [openmetrics lines]).

    Returns an empty line list if the row carries no usable value.
    """
    when = row.get("date")
    if not isinstance(when, datetime):
        return -1, []
    ts = f"{when.timestamp():.3f}"
    lines: list[str] = []
    for column, metric in ALL_MAP.items():
        number = _num(row.get(column))
        if number is None:
            continue
        lines.append(f"{metric} {format_value(number)} {ts}")
    return when.year, lines


@dataclass
class Stats:
    rows: int = 0
    samples: int = 0
    skipped: int = 0
    files: dict[int, Path] = field(default_factory=dict)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    conn = parser.add_argument_group("MySQL connection (behind an SSH tunnel)")
    conn.add_argument("--host", default=os.environ.get("HEIZUNG_MYSQL_HOST", "127.0.0.1"))
    conn.add_argument(
        "--port", type=int, default=int(os.environ.get("HEIZUNG_MYSQL_PORT", "13306"))
    )
    conn.add_argument("--user", default=os.environ.get("HEIZUNG_MYSQL_USER", ""))
    conn.add_argument("--password", default=os.environ.get("HEIZUNG_MYSQL_PASSWORD", ""))
    conn.add_argument("--database", default=os.environ.get("HEIZUNG_MYSQL_DATABASE", ""))
    conn.add_argument(
        "--table",
        default=os.environ.get("HEIZUNG_MYSQL_TABLE", "t_data"),
    )
    conn.add_argument(
        "--frame", default="frame1", help="frame value to filter on (default: frame1)"
    )

    out = parser.add_argument_group("output")
    out.add_argument(
        "--out",
        default=".",
        help="directory to write heizung-<year>.openmetrics files into (created if missing)",
    )

    run = parser.add_argument_group("run control")
    run.add_argument("--batch", type=int, default=50000, help="rows per query (default: 50000)")
    run.add_argument("--min-id", type=int, default=0, help="start after this id (default: 0)")
    run.add_argument("--max-id", type=int, default=None, help="stop after this id (default: none)")
    run.add_argument(
        "--start", type=datetime.fromisoformat, default=None, help="only rows >= this date"
    )
    run.add_argument(
        "--end", type=datetime.fromisoformat, default=None, help="only rows <= this date"
    )
    run.add_argument(
        "--progress-every",
        type=int,
        default=200000,
        help="print progress every N rows (default: 200000)",
    )
    args = parser.parse_args(argv)

    if not args.database:
        parser.error("--database (or HEIZUNG_MYSQL_DATABASE) is required")
    if not args.user:
        parser.error("--user (or HEIZUNG_MYSQL_USER) is required")
    if args.start and args.end and args.start > args.end:
        parser.error("--start must not be after --end")
    return args


def build_where(
    frame: str, start: datetime | None, end: datetime | None
) -> tuple[str, dict[str, Any]]:
    clauses = ["frame = %(frame)s"]
    params: dict[str, Any] = {"frame": frame}
    if start is not None:
        clauses.append("date >= %(start)s")
        params["start"] = start
    if end is not None:
        clauses.append("date <= %(end)s")
        params["end"] = end
    return " AND ".join(clauses), params


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    where, base_params = build_where(args.frame, args.start, args.end)
    columns = ", ".join(["id", "date", *ALL_MAP])
    query = (
        f"SELECT {columns} FROM `{args.table}` "
        f"WHERE {where} AND id > %(cursor)s "
        "ORDER BY id LIMIT %(batch)s"
    )

    connection = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    stats = Stats()
    open_files: dict[int, Any] = {}

    def handle_for(year: int):
        path = out_dir / f"heizung-{year}.openmetrics"
        handle = open_files.get(year)
        if handle is None:
            handle = path.open("w", encoding="utf-8")
            open_files[year] = handle
            stats.files[year] = path
        return handle

    cursor = connection.cursor()
    try:
        last_id = args.min_id
        while True:
            params = dict(base_params)
            params["cursor"] = last_id
            params["batch"] = args.batch
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                break

            for row in rows:
                year, lines = render_row(row)
                stats.rows += 1
                if not lines:
                    stats.skipped += 1
                    last_id = row["id"]
                    continue
                handle = handle_for(year)
                handle.writelines(line + "\n" for line in lines)
                stats.samples += len(lines)
                last_id = row["id"]

                if args.progress_every and stats.rows % args.progress_every == 0:
                    print(
                        f"... processed {stats.rows} rows ({stats.samples} samples)",
                        file=sys.stderr,
                    )

            if args.max_id is not None and last_id >= args.max_id:
                break
    finally:
        for handle in open_files.values():
            handle.write("# EOF\n")
            handle.close()
        connection.close()

    print(
        f"Done. rows={stats.rows} samples={stats.samples} skipped={stats.skipped}",
        file=sys.stderr,
    )
    for year in sorted(stats.files):
        path = stats.files[year]
        print(f"  {year}: {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
