#!/usr/bin/env python
from time import gmtime, strftime

from heizung.config import load_config, setup_gpio
from heizung.control import FiringControl


def main():
    config = load_config()
    _, gpio = setup_gpio()

    def _log(msg):
        if config.get("logger") == "True":
            import logging

            logging.getLogger("heizung").info(msg)
        else:
            print(msg)

    _log("+-----  S T A R T  ----------------------------------")
    _log("|   {!r}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))
    _log("+----------------------------------------------------")
    _log("| operation mode: {}".format(config["operating_mode"]))

    FiringControl(config, gpio).run()


if __name__ == "__main__":
    main()
