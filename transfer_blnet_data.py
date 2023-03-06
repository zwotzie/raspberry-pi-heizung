#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import urllib2
from ConfigParser import SafeConfigParser
from logging import config
from time import gmtime, strftime, time, sleep

# Set up a specific logger with our desired output level
_config_path = os.path.abspath(os.path.dirname(sys.argv[0]))
_config_file = _config_path + "/etc/heizung.conf"
_config_logger = _config_path+'/etc/logging.conf'

print("config heizung: ", _config_file)
print("config logger : ", _config_logger)

parser = SafeConfigParser()
parser.read(_config_file)

url_internal    = parser.get('heizung', 'url_internal')

log2log = parser.get('heizung', 'logger')

print("print2logger  : ", log2log)

logging.config.fileConfig(_config_logger)
logger = logging.getLogger('transfer')
logger.propagate = False


def logmessage(message):
    if log2log == "True":
        logger.info(message)
    else:
        print(message)

logmessage("+-------  S T A R T  T R A N S F E R  ---------------")
logmessage("|   %r" % strftime("%Y-%m-%d %H:%M:%S", gmtime()))
logmessage("+----------------------------------------------------")
logmessage("url_internal: %s" % url_internal)

class heating(object):
    def __init__(self):
        pass

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
            data = self.getResonseResult(url_internal)

            if data == "[]":
                message = "| OK: []"
            else:
                message = "| response is not what expected"
            logmessage(message)

        except:
            logger.error("| something went wrong while retrieving from %s" % url_internal)

        logmessage('+----------------- transfer done -------------------------------------')

    def run(self):
        while True:
            start = time()
            data = []

            # old way to transfer the data to uvr1611
            self.transferData()

            end = time()

            seconds_processing = end - start
            to_sleep = 60 - seconds_processing
            if seconds_processing > 0:
                sleep(to_sleep)  # sleeping time in seconds

if __name__ == '__main__':
    h = heating()
    h.run()
