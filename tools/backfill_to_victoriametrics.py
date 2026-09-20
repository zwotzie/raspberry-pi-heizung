#!/usr/bin/env python3
"""
Import one year of Heizung data (gzipped CSV) into VictoriaMetrics.
"""

import argparse
import gzip
import sys
from datetime import datetime

import requests

# Spalten-Reihenfolge muss zum Export passen!
COLUMNS = [
    "id", "date",
    "analog1", "analog2", "analog3", "analog4", "analog5", "analog6",
    "analog7", "analog8", "analog9", "analog10", "analog11", "analog13",
    "analog15", "analog16",
    "speed2", "speed3", "speed4",
    "digital1", "digital2", "digital3", "digital4", "digital5",
    "digital6", "digital7", "digital8", "digital9", "digital10", "digital11",
]

ANALOG_MAP = {
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
SPEED_MAP = {
    "speed2": "kessel_ladepumpe_drehzahl",
    "speed3": "heizung_pumpe_drehzahl",
    "speed4": "solar_ladepumpe_drehzahl",
}
DIGITAL_MAP = {
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
ALL_MAP = {**ANALOG_MAP, **SPEED_MAP, **DIGITAL_MAP}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file", help="heizung-YYYY.csv.gz")
    p.add_argument("--vm-url", default="http://victoriametrics.lan:8428")
    p.add_argument("--job", default="heizung")
    p.add_argument("--instance", default="heizung")
    p.add_argument("--batch", type=int, default=3000, help="samples per push")
    args = p.parse_args()

    import_url = f"{args.vm_url.rstrip('/')}/api/v1/import/prometheus"
    buffer = []
    samples = 0
    rows = 0

    def flush():
        nonlocal buffer, samples
        if not buffer:
            return
        payload = "\n".join(buffer) + "\n"
        r = requests.post(import_url, data=payload.encode(), timeout=60)
        if r.status_code not in (200, 204):
            print(f"ERROR {r.status_code}: {r.text}", file=sys.stderr)
            sys.exit(1)
        samples += len(buffer)
        buffer.clear()

    opener = gzip.open if args.file.endswith(".gz") else open

    with opener(args.file, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != len(COLUMNS):
                continue

            row = dict(zip(COLUMNS, parts))
            try:
                when = datetime.fromisoformat(row["date"].replace(" ", "T"))
            except ValueError:
                continue

            ts_ms = int(when.timestamp() * 1000)
            rows += 1

            for col, metric in ALL_MAP.items():
                val = row.get(col)
                if not val or val.lower() in ("null", "none", ""):
                    continue
                try:
                    num = float(val)
                except ValueError:
                    continue
                if num != num:  # NaN
                    continue

                line_out = f'{metric}{{job="{args.job}",instance="{args.instance}"}} {num:g} {ts_ms}'
                buffer.append(line_out)

            if len(buffer) >= args.batch:
                flush()
                if rows % 50000 == 0:
                    print(f"... {rows} rows, {samples} samples", file=sys.stderr)

    flush()
    print(f"Fertig: {rows} rows → {samples} samples", file=sys.stderr)


if __name__ == "__main__":
    main()
