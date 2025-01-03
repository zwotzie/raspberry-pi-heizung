#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import json
import logging
import os
import platform
import socket
import sys
import tomllib
from logging import config
from time import gmtime
from time import sleep
from time import strftime
from time import time

import requests

from ta.fieldlists import get_messurements

raspberry = False
if 'raspberrypi' in platform.uname():
    # global raspberry
    raspberry = True
    import RPi.GPIO as GPIO

    # gpio 4 = BCM 23 = Pin 16
    RelaisHeizung = 23
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RelaisHeizung, GPIO.OUT)
    GPIO.output(RelaisHeizung, GPIO.LOW)

# Set up a specific logger with our desired output level
_config_path = os.path.abspath(os.path.dirname(sys.argv[0]))
_config_file = _config_path + "/etc/heizung.conf"
_config_logger = _config_path + '/etc/logging.conf'

print("config heizung: ", _config_file)
print("config logger : ", _config_logger)

with open(_config_file, 'rb') as f:
    config = tomllib.load(f)

url             = config['heizung'].get('url')
api_url         = config['heizung'].get('api_url')
url_internal    = config['heizung'].get('url_internal')
blnet_host      = config['heizung'].get('blnet_host')
operating_mode  = config['heizung'].get('operating_mode')
ip              = socket.gethostbyname(blnet_host)

log2log = config['heizung'].get('logger')

print("print2logger  : ", log2log)

logging.config.fileConfig(_config_logger)
logger = logging.getLogger('heizung')
logger.propagate = False


def log_message(message):
    if log2log == "True":
        logger.info(message)
    else:
        print(message)


log_message("+-----  S T A R T  ----------------------------------")
log_message("|   %r" % strftime("%Y-%m-%d %H:%M:%S", gmtime()))
log_message("+----------------------------------------------------")
log_message("| operation mode: %s" % operating_mode)


def get_time_difference_from_now(timestamp):
    """ :return minutes from now """
    time_diff = datetime.datetime.now() - timestamp
    return int(time_diff.total_seconds() / 60)


class FiringControl(object):

    def __init__(self):
        self.firing_start = None
        self.measurements = {}

    @staticmethod
    def start_firing():
        """
        closes the relay which start the wood gasifier in firewood mode
        closes the relay which start/keep burning the wood gasifier in pellets mode
        :return:
        """
        message = "START_KESSEL: "
        if raspberry:
            message += " set RelaisHeizung-GPIO to HIGH"
            GPIO.output(RelaisHeizung, GPIO.HIGH)
        else:
            message += "test only (no raspberry)"
        log_message(message)

    @staticmethod
    def stop_firing():
        """
        stops burning in pellets mode, stop starting in firewood mode
        :return:
        """
        message = "STOP_KESSEL: "
        if raspberry:
            message += " set RelaisHeizung-GPIO to LOW"
            GPIO.output(RelaisHeizung, GPIO.LOW)
        else:
            message += "test only (no raspberry)"
        log_message(message)

    def transfer_data(self, data):
        """
        This method transfers the data from uvr1611 to the api of same project to hosting server
        """
        request_url = api_url + "/databasewrapper/insertData"
        result_insert = requests.post(request_url, json=[[data]])
        result = requests.get(api_url + "/databasewrapper/updateTables")

        log_message(f"transfer data uvr1611=>API: insertData: {result_insert.status_code} result: {result_insert.text} :: updateTables: {result.status_code}")

    def get_current_measurements_from_blnet(self):
        field_list, mapping, api_data = get_messurements(ip=ip, reset=False)
        self.measurements[mapping['timestamp']] = {
            "field_list": field_list,
            "mapping": mapping,
            "api_data": api_data
        }
        log_message(f"dh={mapping}")
        log_message(f"fl={field_list}")
        log_message(f"ad={api_data}")

        if len(self.measurements) > 30:
            oldest_measurement = min(self.measurements.keys())
            del self.measurements[oldest_measurement]
        return field_list, mapping, api_data

    def check_measurements(self):
        for attempt in range(10):
            dt_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message("=" * 99)
            log_message(f"New test on measurements: {dt_now}")
            try:
                field_list, mapping, api_data = self.get_current_measurements_from_blnet()
                break
            except Exception as e:
                # raise
                log_message(f"#{attempt} Error while fetching data from BLNET: {e}")
                if attempt == 9:
                    return "OFF"
                sleep(30)

        newest_date = max(self.measurements.keys())
        return_do_firing = "OFF"  # default

        start_list = []
        solar_list = []

        try:
            for messurement_date in self.measurements.keys():
                heizungs_dict = self.measurements[messurement_date]['mapping']

                minutes_ago_since_now = get_time_difference_from_now(heizungs_dict['timestamp'])
                do_firing = "-"
                # spread = heizungs_dict['heizung_vl'] - heizungs_dict['heizung_rl']

                if heizungs_dict['speicher_3_kopf'] < 39 \
                        and heizungs_dict['speicher_4_mitte'] < 35 \
                        and heizungs_dict['speicher_5_boden'] < 32:
                    do_firing = "ON"
                elif heizungs_dict['speicher_1_kopf'] < 45 \
                        and heizungs_dict['speicher_1_kopf'] < 45 \
                        and heizungs_dict['speicher_2_kopf'] < 45 \
                        and heizungs_dict['speicher_3_kopf'] < 45 \
                        and heizungs_dict['speicher_4_mitte'] < 45 \
                        and heizungs_dict['speicher_5_boden'] < 45:
                    do_firing = "ON"

                # elif heizungs_dict['speicher_3_kopf'] < 35 \
                #         and heizungs_dict['speicher_4_mitte'] < 30 \
                #         and heizungs_dict['speicher_5_boden'] < 30 \
                #         and spread <= 2:
                #         # if heizungs_dict['heizung_d'] == 0:
                #         #if minutes_ago_since_now < 15: # only if measurements are not so long ago
                #     do_firing = "ON"

                # this is enough energy!
                if heizungs_dict['speicher_5_boden'] > 72:
                    do_firing = "OFF"

                if minutes_ago_since_now <= 30:
                    start_list.append(do_firing)
                    solar_list.append(heizungs_dict['solar_strahlung'])

                # log_message("%r, %r, %.1f, %r, %r, data=%r" % (
                #       heizungs_dict['timestamp']
                #     # , heizungs_dict['heizung_d']  # not available
                #     , heizungs_dict['d_heizung_pumpe']
                #     , spread
                #     , do_firing
                #     , minutes_ago_since_now
                #     , data
                # ))
        except IndexError:
            log_message("ERROR: there is nothing to examine???")


        # check if wood gasifier start is necessary:
        api_data['digital1'] = 0
        if "OFF" in start_list or not start_list:
            return_do_firing = "OFF"
        elif "ON" in start_list:
            return_do_firing = "ON"
            api_data['digital1'] = 1
        else:
            return_do_firing = "-"
        self.transfer_data(api_data)
        # for a very sunny day exeception should be made here:
        # be optimistic that enough hot water will be produced
        # if the mean of the solar radiation values is big enough, shut off firing
        mean_solar = 0

        mean_solar = sum(solar_list) / len(solar_list)
        if mean_solar > 400:
            return_do_firing = "OFF"

        log_message(json.dumps({"t": dt_now, "mean solar": mean_solar, "solar_list_30m": solar_list}))
        log_message(json.dumps({"t": dt_now, "firing_decision": return_do_firing, "start_list_30m": start_list,
                                "fire_since": self.firing_start}))

        return return_do_firing

    def run(self):
        # blnet = getMeasurementsFromUVR1611(blnet_host, timeout=(3.05, 5), password=None)

        # this is only for operating_mode firewood!
        if len(sys.argv) > 1 and sys.argv[1] == 'ON':
            log_message("Start burn-off per comandline...")
            self.start_firing()
            log_message("manually start done....")
            sleep(5)
            # better wait some time?
            self.stop_firing()

        else:
            while True:
                start = time()

                result = self.check_measurements()

                if operating_mode == 'firewood':
                    if result == "ON":
                        self.start_firing()
                    else:
                        self.stop_firing()

                elif operating_mode == 'pellets':
                    if result == "ON":
                        if self.firing_start is None:
                            self.firing_start = time()
                            self.start_firing()

                    elif result == 'OFF':
                        self.stop_firing()

                        if self.firing_start:
                            message = "combustion time: %r hours" % (round((time() - self.firing_start) / 3600, 1))
                            log_message(message)

                            self.firing_start = None

                    else:  # result == '--'
                        pass

                end = time()

                seconds_processing = end - start
                to_sleep = 60 - seconds_processing
                if to_sleep > 0:
                    sleep(to_sleep)  # sleeping time in seconds


if __name__ == '__main__':
    h = FiringControl()
    h.run()
