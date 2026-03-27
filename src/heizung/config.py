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


def setup_gpio(relay_pin: int = 23):
    """
    Initialize GPIO relay if running on a Raspberry Pi.

    :returns: (is_raspberry: bool, gpio_module or None)
    """
    if "raspberrypi" in platform.uname():
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(relay_pin, GPIO.OUT)
        GPIO.output(relay_pin, GPIO.LOW)
        return True, GPIO
    return False, None
