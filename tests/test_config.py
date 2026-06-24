import sys
import types
from pathlib import Path

import pytest

import heizung.config as config

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def patch_dns(monkeypatch):
    monkeypatch.setattr(config.socket, "gethostbyname", lambda host: "127.0.0.1")


def test_load_config_reads_conf_and_resolves_ip(patch_dns):
    cfg = config.load_config(config_path=str(PROJECT_ROOT))
    assert cfg["ip"] == "127.0.0.1"
    assert cfg["operating_mode"] in ("pellets", "firewood")
    assert "blnet_host" in cfg
    assert "api_url" in cfg


def test_load_config_uses_env_var(monkeypatch, patch_dns):
    monkeypatch.setenv("HEIZUNG_CONFIG_PATH", str(PROJECT_ROOT))
    cfg = config.load_config()
    assert cfg["ip"] == "127.0.0.1"


def _fake_platform_uname(contains_raspberry: bool):
    fields = ["Linux", "host", "6.1", "#1", "armv7l", ""]
    if contains_raspberry:
        fields[1] = "raspberrypi"
    return lambda: tuple(fields)


def test_setup_gpio_returns_false_off_device(monkeypatch):
    monkeypatch.setattr(config.platform, "uname", _fake_platform_uname(False))
    is_pi, gpio = config.setup_gpio()
    assert is_pi is False
    assert gpio is None


def test_setup_gpio_initialises_lgpio_on_device(monkeypatch):
    calls = []

    fake = types.ModuleType("lgpio")
    fake.gpiochip_open = lambda chip: calls.append(("open", chip)) or 7
    fake.gpio_claim_output = lambda h, pin, level: calls.append(("claim", h, pin, level))
    fake.gpio_write = lambda h, pin, level: calls.append(("write", h, pin, level))
    fake.gpio_free = lambda h, pin: calls.append(("free", h, pin))
    fake.gpiochip_close = lambda h: calls.append(("close", h))
    monkeypatch.setitem(sys.modules, "lgpio", fake)
    monkeypatch.setattr(config.platform, "uname", _fake_platform_uname(True))

    is_pi, gpio = config.setup_gpio(relay_pin=23, chip=0)
    assert is_pi is True
    assert ("open", 0) in calls
    assert ("claim", 7, 23, 0) in calls

    # the adapter mimics the RPi.GPIO interface
    gpio.output(23, gpio.HIGH)
    assert ("write", 7, 23, 1) in calls
    gpio.cleanup()
    assert ("free", 7, 23) in calls
    assert ("close", 7) in calls

