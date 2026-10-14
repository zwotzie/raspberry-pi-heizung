#!/usr/bin/env python
"""Entry point: ``python -m heizung`` starts the heating control daemon."""

import argparse
import logging
from time import gmtime, sleep, strftime

from heizung import weather
from heizung.config import load_config, setup_gpio
from heizung.control import FiringControl

logger = logging.getLogger("heizung")


def _test_weather(config: dict) -> None:
    """Fetch Open-Meteo once, print representative samples, then exit."""
    latitude = config.get("open_meteo_latitude")
    longitude = config.get("open_meteo_longitude")
    if latitude is None or longitude is None:
        print(
            "Open-Meteo Test nicht möglich: open_meteo_latitude und "
            "open_meteo_longitude fehlen in der Config."
        )
        return

    print(f"Open-Meteo Abfrage: lat={latitude}, lon={longitude}")
    print(f"Timezone: {config.get('open_meteo_timezone', 'Europe/Berlin')}")
    print(f"Forecast-Tage: {config.get('open_meteo_forecast_days', 2)}")

    try:
        payload = weather.fetch_forecast(config)
    except Exception as exc:  # pragma: no cover - network/runtime environment dependent
        print(f"Open-Meteo-Fetch fehlgeschlagen: {exc}")
        return

    samples = weather.upsert_health_samples(
        weather.build_forecast_samples(payload, include_forecast=False)
    )
    print(f"Erhalten: {len(samples)} Samples")

    job = str(config.get("open_meteo_job") or "open-meteo")
    instance = str(config.get("open_meteo_instance") or "open-meteo")
    push_url = str(config.get("push_url") or "").strip()
    push_payload = weather.render_weather_push_payload(samples, job=job, instance=instance)

    print("\nErste Samples:")
    for sample in samples[:15]:
        print(sample)
    print("\nLetzte Samples:")
    for sample in samples[-5:]:
        print(sample)

    print(f"\nAktuelle Bedingungen: {payload.get('current')}")

    if push_url:
        print(f"Push-Zielsystem: {push_url.rstrip('/')}/api/v1/import/prometheus")
    else:
        print("Push-Zielsystem: (kein push_url gesetzt – im Daemon deaktiviert)")
    print(f"job={job!r}, instance={instance!r}, Zeilen={len(push_payload.splitlines())}")

    print("\n=== VictoriaMetrics-Push-Payload (Open-Meteo) ===")
    print(push_payload, end="")
    if not push_payload.endswith("\n"):
        print()
    print("=== Ende VictoriaMetrics-Push-Payload (Open-Meteo) ===")


def _build_parser() -> argparse.ArgumentParser:
    """Build the heizung command line parser."""
    parser = argparse.ArgumentParser(
        prog="heizung",
        description="Heizungssteuerung, Diagnose und Wetter-Test.",
    )
    parser.add_argument(
        "--test-weather",
        action="store_true",
        help="Open-Meteo einmal abfragen und Weather-Samples ausgeben",
    )
    parser.add_argument(
        "--start-burning",
        action="store_true",
        help="Relais fuer 5 Sekunden schalten (Burn-off-Test)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Load config and dispatch command line options."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    _, gpio = setup_gpio()

    if args.test_weather:
        _test_weather(config)
        return

    if args.start_burning:
        logger.info("Start burn-off per commandline...")
        control = FiringControl(config, gpio)
        control.start_firing()
        sleep(5)
        control.stop_firing()
        logger.info("manually start done....")
        return

    logger.info("+-----  S T A R T  ----------------------------------")
    logger.info("|   {!r}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))
    logger.info("+----------------------------------------------------")
    logger.info("| operation mode: {}".format(config["operating_mode"]))
    FiringControl(config, gpio).run()


if __name__ == "__main__":
    main()
