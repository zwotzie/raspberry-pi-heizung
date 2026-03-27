#!/usr/bin/env python

from time import gmtime, strftime, time, sleep
import RPi.GPIO as GPIO

# gpio 4 = BCM 23 = Pin 16
RelaisHeizung = 23
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RelaisHeizung,  GPIO.OUT)
GPIO.output(RelaisHeizung,  GPIO.LOW)

# start fire
GPIO.output(RelaisHeizung, GPIO.HIGH)


t = 3600 * 1.5
sleep(t)

# stop fire
GPIO.output(RelaisHeizung, GPIO.LOW)

# cleanup
GPIO.cleanup()