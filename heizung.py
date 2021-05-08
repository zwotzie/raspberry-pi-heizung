#!/usr/bin/env python
# -*- coding: utf-8 -*-

import simplejson
import urllib2
import datetime
from time import gmtime, strftime, time, sleep
import platform
from ConfigParser import SafeConfigParser
import logging
from logging import config
import sys, os
from ta.get_measurements import getMeasurementsFromUVR1611
from ta.fieldlists import fields
# import html
# import json


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

parser = SafeConfigParser()
parser.read(_config_file)
url             = parser.get('heizung', 'url')
url_internal    = parser.get('heizung', 'url_internal')
blnet_host      = parser.get('heizung', 'blnet_host')
operating_mode  = parser.get('heizung', 'operating_mode')

log2log = parser.get('heizung', 'logger')

print("print2logger  : ", log2log)

logging.config.fileConfig(_config_logger)
logger = logging.getLogger('heizung')
logger.propagate = False


def logmessage(message):
    if log2log == "True":
        logger.info(message)
    else:
        print(message)

logmessage("+-----  S T A R T  ----------------------------------")
logmessage("|   %r" % strftime("%Y-%m-%d %H:%M:%S", gmtime()))
logmessage("+----------------------------------------------------")
logmessage("| operation mode: %s" % operating_mode)


def getTimeDifferenceFromNow(timestamp):
    """ :return minutes from now """
    timeDiff = datetime.datetime.now() - datetime.datetime.fromtimestamp(timestamp)
    return int(timeDiff.total_seconds() / 60)


class heating(object):
    def __init__(self):
        self.firing_start = None

    def start_firing(self):
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
        logmessage(message)


    def stop_firing(self):
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
        logmessage(message)


    def getResonseResult(self, url):
        request = urllib2.Request(url)
        response = urllib2.urlopen(request, timeout=30)
        response_result = response.read()

        return response_result


    def transferData(self):
        """
        This method transfers the data from uvr1611 to the api of same project to hosting server
        """
        logmessage('+------------------ transfer data from uvr1611 ------------------------')
        try:
            if raspberry:
    #            response = urllib.urlopen(url_internal)
    #            data = response.read()

                data = self.getResonseResult(url_internal)

                if data == "[]":
                    message = "| OK: []"
                else:
                    message = "| response is not what expected"
            else:
                message="| i'm not on raspberry..."
            logmessage(message)

        except:
            logger.error("| something went wrong while retrieving from %s" % url_internal)
            logger.error("  Unexpected error:", sys.exc_info()[0])

        logmessage('+----------------- transfer done -------------------------------------')


    def pushDataToHosting(self, data):
        """
        Will send data to uvr1611 api to hosting server
        :param data:
        :return:
        """
        pass


    def getMeasurementsFromHttp(self):
        response = self.getResonseResult(url)
        data = ''
        if response:
            data = simplejson.loads(response)[-20:]
        return data

    def check_measurements(self, uvr_direct_data=None):
        logmessage("-"*77)
        dt_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logmessage("------------- New Test on Measurements: %s -----------------" % dt_now)
        logmessage("-"*77)

        if uvr_direct_data is None or len(uvr_direct_data) == 0:
            data = self.getMeasurementsFromHttp()
        else:
            data = [uvr_direct_data]

        return_do_firing = "OFF"  # default

        start_list = []
        solar_list = []

        try:
            heizungs_dict = dict(zip(fields, data[-1]))
            for key, val in sorted(heizungs_dict.items()):
                logmessage('  {0:25} : {1:}'.format(key, val))
            logmessage('  {0:25} : {1:}'.format('datetime',
                                            datetime.datetime.fromtimestamp(heizungs_dict['timestamp']).strftime(
                                                '%Y-%m-%d %H:%M:%S')))
            logmessage("-"*77)

            for l in data:
                heizungs_dict = dict(zip(fields, l))

                minutes_ago_since_now = getTimeDifferenceFromNow(heizungs_dict['timestamp'])
                do_firing = "--"
                spread = heizungs_dict['heizung_vl'] - heizungs_dict['heizung_rl']

                if heizungs_dict['speicher_3_kopf'] < 39 \
                        and heizungs_dict['speicher_4_mitte'] < 35 \
                        and heizungs_dict['speicher_5_boden'] < 32:
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

                logmessage("%r %r %r %.1f %r %r %r" % (
                      datetime.datetime.fromtimestamp(l[0]).strftime('%Y-%m-%d %H:%M:%S')
                    , heizungs_dict['heizung_d']
                    , heizungs_dict['d_heizung_pumpe']
                    , spread
                    , do_firing
                    , minutes_ago_since_now
                    , l
                ))
        except IndexError:
            logmessage("-"*77)
            logmessage("there is nothing to examine...")
        logmessage("-"*77)

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
        logmessage(simplejson.dumps({"t": dt_now, "mean solar": mean_solar, "solar_list_30m": solar_list}))
        logmessage(simplejson.dumps({"t": dt_now, "firing_decision": return_do_firing, "start_list_30m": start_list, "fire_since": self.firing_start}))
        logmessage("-" * 77)

        return return_do_firing

    def run(self):
        # blnet = getMeasurementsFromUVR1611(blnet_host, timeout=(3.05, 5), password=None)

        # this is only for operating_mode firewood!
        if len(sys.argv) > 1 and sys.argv[1] == 'ON':
            logmessage("Start burn-off per comandline...")
            self.start_firing()
            logmessage("manually start done....")
            sleep(5)
            # better wait some time?
            self.stop_firing()

        else:
            while True:
                start = time()
                data = []

                # moved to extra process transfer_blnet_data.py
                # old way to transfer the data to uvr1611
                # if raspberry:
                #    self.transferData()

                result = self.check_measurements(data)

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
                            logmessage(message)

                            self.firing_start = None

                    else: # result == '--'
                        pass

                end = time()

                seconds_processing = end - start
                to_sleep = 120 - seconds_processing
                if seconds_processing > 0:
                    sleep(to_sleep)  # sleeping time in seconds

if __name__ == '__main__':
    h = heating()
    h.run()
