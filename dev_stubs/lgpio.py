"""Development stub for the ``lgpio`` library.

The real :mod:`lgpio` only builds on Linux (it requires ``linux/gpio.h``),
so it cannot be installed on macOS / Windows. This stub provides no-op
implementations of the small subset of the API used in this project, so that
``import lgpio`` works while developing off-device.

It logs every call so you can see what would happen on the Raspberry Pi.

Activate it by putting the ``dev_stubs`` directory on ``PYTHONPATH`` (a
``.pth`` file in the venv's site-packages does this automatically — see the
project README).
"""

from __future__ import annotations

import logging

_log = logging.getLogger("lgpio.stub")

# Levels, mirrors the real library's integer levels.
LOW = 0
HIGH = 1

_next_handle = 0


def gpiochip_open(chip: int) -> int:
    global _next_handle
    _next_handle += 1
    _log.info("[stub] gpiochip_open(chip=%s) -> handle %s", chip, _next_handle)
    return _next_handle


def gpiochip_close(handle: int) -> int:
    _log.info("[stub] gpiochip_close(handle=%s)", handle)
    return 0


def gpio_claim_output(handle: int, gpio: int, level: int = LOW, *args, **kwargs) -> int:
    _log.info("[stub] gpio_claim_output(handle=%s, gpio=%s, level=%s)", handle, gpio, level)
    return 0


def gpio_claim_input(handle: int, gpio: int, *args, **kwargs) -> int:
    _log.info("[stub] gpio_claim_input(handle=%s, gpio=%s)", handle, gpio)
    return 0


def gpio_free(handle: int, gpio: int) -> int:
    _log.info("[stub] gpio_free(handle=%s, gpio=%s)", handle, gpio)
    return 0


def gpio_write(handle: int, gpio: int, level: int) -> int:
    _log.info("[stub] gpio_write(handle=%s, gpio=%s, level=%s)", handle, gpio, level)
    return 0


def gpio_read(handle: int, gpio: int) -> int:
    _log.info("[stub] gpio_read(handle=%s, gpio=%s) -> %s", handle, gpio, LOW)
    return LOW

