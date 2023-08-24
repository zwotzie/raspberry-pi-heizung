#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform


raspberry = False
if 'raspberrypi' in platform.uname():
    # global raspberry
    raspberry = True
    import RPi.GPIO as GPIO

    # gpio 4 = BCM 23 = Pin 16
    RelaisHeizung = 23
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)


GPIO.setup(RelaisHeizung, GPIO.IN)
state = GPIO.input(RelaisHeizung)


if state == 0:
    print("Heizungsrelais ist aus")
elif state == 1:
    print("Heizungsrelais ist an")
