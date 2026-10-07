#!/usr/bin/env python

from time import sleep

import lgpio

# gpio 4 = BCM 23 = Pin 16
RelaisHeizung = 23

h = lgpio.gpiochip_open(0)
# Relais als Output, initial LOW
lgpio.gpio_claim_output(h, RelaisHeizung, 0)

try:
    # start fire
    lgpio.gpio_write(h, RelaisHeizung, 1)

    t = int(3600 * 1.5)
    sleep(t)

    # stop fire
    lgpio.gpio_write(h, RelaisHeizung, 0)
finally:
    # cleanup
    lgpio.gpio_free(h, RelaisHeizung)
    lgpio.gpiochip_close(h)
