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
    GPIO.setup(RelaisHeizung,  GPIO.OUT)
    GPIO.output(RelaisHeizung,  GPIO.LOW)

# Set up a specific logger with our desired output level
_config_path = os.path.abspath(os.path.dirname(sys.argv[0]))
_config_file = _config_path + "/etc/heizung.conf"
_config_logger = _config_path+'/etc/logging.conf'

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

log2log = config.get('heizung', 'logger')

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


class HeatingControl(object):
    def __init__(self):
        self.firing_start = None
        self.messurements = {}

    @staticmethod
    def start_firing():
        """
        closes the relay which start the wood gasifier in firewood mode
        closes the relay which start/keep burning the wood gasifier in pellets mode
        :return:
        """
        message = ""
        if raspberry:
            GPIO.output(RelaisHeizung, GPIO.HIGH)
        else:
            message = "doing : "
        message += "START_KESSEL"
        log_message(message)


    @staticmethod
    def stop_firing():
        """
        stops burning in pellets mode, stop starting in firewood mode
        :return:
        """
        message = ""
        if raspberry:
            GPIO.output(RelaisHeizung, GPIO.LOW)
        else:
            message = "doing : "
        message += "STOP_KESSEL"
        log_message(message)


    def transfer_data(self, data):
        """
        This method transfers the data from uvr1611 to the api of same project to hosting server
        """
        log_message('+------------------ transfer data uvr1611=>API ------------------------')
        request_url = api_url + "/databasewrapper/insertData"

        result = requests.post(request_url, json=[[data]])
        log_message(f"{result.status_code} result: {result.text}")

        result = requests.get(api_url + "/databasewrapper/updateTables")
        log_message(f"{result.status_code} result: {result.text}")


    def get_current_measurements_from_blnet(self):
        field_list, mapping, api_data = get_messurements(ip=ip, reset=False)
        self.messurements[mapping['timestamp']] = {
            "field_list": field_list,
            "mapping": mapping
        }
        log_message(f"dh={mapping}")
        log_message(f"fl={field_list}")
        self.transfer_data(api_data)
        if len(self.messurements) > 30:
            self.messurements.popitem()

    def check_measurements(self):
        dt_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message("=" * 99)
        log_message(f"New test on measurements: {dt_now}")
        try:
            self.get_current_measurements_from_blnet()
        except Exception as e:
            log_message(f"Error while fetching data from BLNET: {e}")
            return "OFF"

        last_date = max(self.messurements.keys())
        return_do_firing = "OFF"  # default

        start_list = []
        solar_list = []

        try:
            for messurement_date in self.messurements.keys():
                data = self.messurements[messurement_date]['field_list']
                heizungs_dict = self.messurements[messurement_date]['mapping']


                minutes_ago_since_now = get_time_difference_from_now(heizungs_dict['timestamp'])
                do_firing = "--"
                spread = heizungs_dict['heizung_vl'] - heizungs_dict['heizung_rl']

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
                #         #if minutes_ago_since_now < 15: # only if messurements are not so long ago
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
            log_message("-" * 77)
            log_message("there is nothing to examine...")
        log_message("-" * 77)

        # check if wood gasifier start is necessary:
        if not start_list:
            # exceptions if it is between 0:00 and 0:10!
            if int(strftime("%H")) == 0 and int(strftime("%M")) <= 10:
                return_do_firing = "--"  # no values available :(
                # Todo build an api for last 30 Minutes values!
            else:
                return_do_firing = "OFF"
        elif "OFF" in start_list or not start_list:
            return_do_firing = "OFF"
        elif "ON" in start_list:
            return_do_firing = "ON"
        else:
            return_do_firing = "--"

        # for a very sunny day exeception should be made here:
        # be optimistic that enough hot water will be produced
        # if the mean of the solar radiation values is big enough, shut off firing
        mean_solar = 0
        try:
            mean_solar = sum(solar_list)/len(solar_list)
            if mean_solar > 400:
                return_do_firing = "OFF"
        except ZeroDivisionError:
            # empty list
            pass
        log_message(json.dumps({"t": dt_now, "mean solar": mean_solar, "solar_list_30m": solar_list}))
        log_message(json.dumps({"t": dt_now, "firing_decision": return_do_firing, "start_list_30m": start_list, "fire_since": self.firing_start}))

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
                            message = "combustion time: %r hours" % (round((time() - self.firing_start)/3600, 1))
                            log_message(message)

                            self.firing_start = None

                    else: # result == '--'
                        pass

                end = time()

                seconds_processing = end - start
                to_sleep = 60 - seconds_processing
                if seconds_processing > 0:
                    sleep(to_sleep)  # sleeping time in seconds


if __name__ == '__main__':
    h = HeatingControl()
    h.run()
