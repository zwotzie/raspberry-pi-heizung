import sys
import types

import heizung.config as config


def _fake_uname(contains_raspberry: bool):
    fields = ["Linux", "raspberrypi" if contains_raspberry else "host", "6.1", "#1", "aarch64", ""]
    return lambda: tuple(fields)


def test_setup_gpio_returns_false_off_device(monkeypatch):
    monkeypatch.setattr(config.platform, "uname", _fake_uname(False))
    assert config.setup_gpio() == (False, None)


def test_setup_gpio_uses_lgpio_on_device(monkeypatch):
    calls = []
    fake = types.ModuleType("lgpio")
    fake.gpiochip_open = lambda chip: calls.append(("open", chip)) or 7
    fake.gpio_claim_output = lambda h, pin, level: calls.append(("claim", h, pin, level))
    fake.gpio_write = lambda h, pin, level: calls.append(("write", h, pin, level))
    fake.gpio_free = lambda h, pin: calls.append(("free", h, pin))
    fake.gpiochip_close = lambda h: calls.append(("close", h))
    monkeypatch.setitem(sys.modules, "lgpio", fake)
    monkeypatch.setattr(config.platform, "uname", _fake_uname(True))

    is_pi, gpio = config.setup_gpio(relay_pin=23, chip=0)
    assert is_pi is True
    assert ("claim", 7, 23, 0) in calls

    gpio.output(23, gpio.HIGH)
    assert ("write", 7, 23, 1) in calls
    gpio.cleanup()
    assert ("free", 7, 23) in calls
    assert ("close", 7) in calls
