import logging
import logging.config
import os
import platform
import socket
import sys
import tomllib


def load_config(config_path: str | None = None) -> dict:
    """Load config from heizung.conf, set up logging and resolve BLNET IP.

    Config path resolution order:
    1. explicit ``config_path`` argument
    2. ``HEIZUNG_CONFIG_PATH`` environment variable
    3. directory of the currently running script (sys.argv[0])
    """
    if config_path is None:
        config_path = os.environ.get("HEIZUNG_CONFIG_PATH") or os.path.abspath(
            os.path.dirname(sys.argv[0])
        )

    config_file = os.path.join(config_path, "etc", "heizung.conf")
    config_logger = os.path.join(config_path, "etc", "logging.conf")

    print("config heizung: ", config_file)
    print("config logger : ", config_logger)

    with open(config_file, "rb") as f:
        raw = tomllib.load(f)

    print("print2logger  : ", raw["heizung"].get("logger"))

    logging.config.fileConfig(config_logger)

    blnet_host = raw["heizung"].get("blnet_host")

    return {
        "url": raw["heizung"].get("url"),
        "api_url": raw["heizung"].get("api_url"),
        "url_internal": raw["heizung"].get("url_internal"),
        "blnet_host": blnet_host,
        "operating_mode": raw["heizung"].get("operating_mode"),
        "logger": raw["heizung"].get("logger"),
        "ip": socket.gethostbyname(blnet_host),
        "measurements_url": raw["heizung"].get("measurements_url"),  # optional – URL of the FastAPI
        "db_url": raw["heizung"].get("db_url"),  # used by the API server
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
        import lgpio

        self._lgpio = lgpio
        self._relay_pin = relay_pin
        self._handle = lgpio.gpiochip_open(chip)
        # claim as output, initial level LOW (0)
        lgpio.gpio_claim_output(self._handle, relay_pin, self.LOW)

    def output(self, pin: int, level: int) -> None:
        self._lgpio.gpio_write(self._handle, pin, level)

    def cleanup(self) -> None:
        try:
            self._lgpio.gpio_free(self._handle, self._relay_pin)
        finally:
            self._lgpio.gpiochip_close(self._handle)


def setup_gpio(relay_pin: int = 23, chip: int = 0):
    """
    Initialize GPIO relay if running on a Raspberry Pi.

    Uses ``lgpio`` (works on Debian Trixie / Python 3.13).

    :returns: (is_raspberry: bool, gpio object or None)
    """
    if "raspberrypi" in platform.uname():
        return True, _LgpioAdapter(relay_pin, chip=chip)
    return False, None
