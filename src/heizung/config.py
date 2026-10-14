"""Configuration loading and GPIO setup."""

import contextlib
import logging
import logging.config
import os
import platform
import socket
import sys
import tomllib


def load_config(config_path: str | None = None) -> dict:
    """Load config from config.toml, set up logging and resolve BLNET IP.

    Config path resolution order:
    1. explicit ``config_path`` argument
    2. ``HEIZUNG_CONFIG_PATH`` environment variable
    3. directory of the currently running script (sys.argv[0])

    Args:
        config_path: Base directory containing ``etc/config.toml`` and
            ``etc/logging.conf``.

    Returns:
        Configuration values as a dict, including the resolved ``ip``.
    """
    if config_path is None:
        config_path = os.environ.get("HEIZUNG_CONFIG_PATH")
        if not config_path:
            candidates = []
            with contextlib.suppress(OSError):
                candidates.append(os.getcwd())
            # Walk upwards from this module so an editable install finds the
            # project root (which contains etc/) rather than src/heizung.
            base = os.path.dirname(os.path.abspath(__file__))
            for _ in range(5):
                candidates.append(base)
                base = os.path.dirname(base)
            with contextlib.suppress(OSError, ValueError):
                candidates.append(os.path.abspath(os.path.dirname(sys.argv[0] or "")))
            for base in candidates:
                if base and os.path.isfile(os.path.join(base, "etc", "config.toml")):
                    config_path = base
                    break
        if not config_path:
            try:
                config_path = os.path.abspath(os.path.dirname(sys.argv[0] or "."))
            except (OSError, ValueError):
                config_path = os.getcwd()

    config_file = os.path.join(config_path, "etc", "config.toml")
    config_logger = os.path.join(config_path, "etc", "logging.conf")

    with open(config_file, "rb") as f:
        raw = tomllib.load(f)

    # Logging is optional on developer machines where the configured path
    # (typically /var/log/heizung/heizung.log) is not writable; fall back to
    # stderr/stdout logging instead of aborting the whole command.
    try:
        logging.config.fileConfig(config_logger, disable_existing_loggers=False)
        logging.getLogger("heizung").info(
            "config: %s, logging: %s", config_file, config_logger
        )
    except Exception as exc:  # noqa: BLE001 - never block config loading on logging
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("heizung").warning(
            "logging config %s could not be loaded (%s); using basic logging",
            config_logger,
            exc,
        )

    blnet_host = raw["heizung"].get("blnet_host")

    # BLNET host resolution is only needed for the daemon; do not crash tools
    # such as --test-weather on a missing/placeholder host.
    ip = None
    if blnet_host:
        try:
            ip = socket.gethostbyname(blnet_host)
        except (socket.gaierror, socket.herror, UnicodeError, TypeError):
            ip = None

    return {
        "blnet_host": blnet_host,
        "operating_mode": raw["heizung"].get("operating_mode"),
        "ip": ip,
        "metrics_port": raw["heizung"].get("metrics_port", 9100),  # Prometheus exporter in the daemon
        "metrics_stale_after": raw["heizung"].get("metrics_stale_after", 180),
        "prometheus_url": raw["heizung"].get("prometheus_url"),  # internal URL, used by the API
        # Optional push mode: when set, the daemon pushes every poll to this
        # TSDB (VictoriaMetrics) and skips the scrape HTTP server.
        "push_url": raw["heizung"].get("push_url"),
        "push_job": raw["heizung"].get("push_job", "heizung"),
        "push_instance": raw["heizung"].get("push_instance", "heizung"),
        # Optional Open-Meteo forecast source (pushed as its own job).
        "open_meteo_url": raw["heizung"].get(
            "open_meteo_url", "https://api.open-meteo.com/v1/forecast"
        ),
        "open_meteo_api_key": raw["heizung"].get("open_meteo_api_key"),
        "open_meteo_latitude": raw["heizung"].get("open_meteo_latitude"),
        "open_meteo_longitude": raw["heizung"].get("open_meteo_longitude"),
        "open_meteo_timezone": raw["heizung"].get("open_meteo_timezone", "Europe/Berlin"),
        "open_meteo_forecast_days": raw["heizung"].get("open_meteo_forecast_days", 2),
        "open_meteo_hourly": raw["heizung"].get(
            "open_meteo_hourly",
            "temperature_2m,apparent_temperature,precipitation,cloud_cover,"
            "shortwave_radiation",
        ),
        "open_meteo_daily": raw["heizung"].get(
            "open_meteo_daily",
            "sunshine_duration,temperature_2m_max,temperature_2m_min",
        ),
        "open_meteo_job": raw["heizung"].get("open_meteo_job", "open-meteo"),
        "open_meteo_instance": raw["heizung"].get("open_meteo_instance", "open-meteo"),
        "open_meteo_poll_seconds": raw["heizung"].get("open_meteo_poll_seconds", 3600),
    }


class _LgpioAdapter:
    """Adapter that mimics the small subset of the old RPi.GPIO API
    (``.output()``, ``.HIGH``, ``.LOW``, ``.cleanup()``) on top of lgpio.

    This keeps control.py unchanged while moving to lgpio, the library
    that works on Debian Trixie / Python 3.13.
    """

    HIGH = 1
    LOW = 0

    def __init__(self, relay_pin: int, chip: int = 0):
        """Open the GPIO chip and claim the relay pin as output (initially LOW).

        Args:
            relay_pin: GPIO pin number of the relay.
            chip: Index of the GPIO chip.
        """
        import lgpio

        self._lgpio = lgpio
        self._relay_pin = relay_pin
        self._handle = lgpio.gpiochip_open(chip)
        # claim as output, initial level LOW (0)
        lgpio.gpio_claim_output(self._handle, relay_pin, self.LOW)

    def output(self, pin: int, level: int) -> None:
        """Write a level to a pin.

        Args:
            pin: GPIO pin number.
            level: ``HIGH`` or ``LOW``.
        """
        self._lgpio.gpio_write(self._handle, pin, level)

    def cleanup(self) -> None:
        """Release the relay pin and close the GPIO chip."""
        try:
            self._lgpio.gpio_free(self._handle, self._relay_pin)
        finally:
            self._lgpio.gpiochip_close(self._handle)


def setup_gpio(relay_pin: int = 23, chip: int = 0):
    """
    Initialize GPIO relay if running on a Raspberry Pi.

    Uses ``lgpio`` (works on Debian Trixie / Python 3.13).

    Args:
        relay_pin: GPIO pin number of the boiler relay.
        chip: Index of the GPIO chip.

    Returns:
        Tuple ``(is_raspberry, gpio)``; ``gpio`` is None when not on a Raspberry Pi.
    """
    if "raspberrypi" in platform.uname():
        return True, _LgpioAdapter(relay_pin, chip=chip)
    return False, None
