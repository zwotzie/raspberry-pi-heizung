#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform


# gpio 4 = BCM 23 = Pin 16
RelaisHeizung = 23

if "raspberrypi" in platform.uname():
    import lgpio

    h = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_input(h, RelaisHeizung)
    state = lgpio.gpio_read(h, RelaisHeizung)
    lgpio.gpio_free(h, RelaisHeizung)
    lgpio.gpiochip_close(h)

    if state == 0:
        print("Heizungsrelais ist aus")
    else:
        print("Heizungsrelais ist an")
else:
    print("not running on a raspberry pi")
