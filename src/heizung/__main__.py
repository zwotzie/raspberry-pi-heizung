#!/usr/bin/env python
"""Entry point: ``python -m heizung`` starts the heating control daemon."""

import logging
from time import gmtime, strftime

from heizung.config import load_config, setup_gpio
from heizung.control import FiringControl

logger = logging.getLogger("heizung")


def main():
    """Load config, set up GPIO and run the control loop (blocks)."""
    config = load_config()
    _, gpio = setup_gpio()

    logger.info("+-----  S T A R T  ----------------------------------")
    logger.info("|   {!r}".format(strftime("%Y-%m-%d %H:%M:%S", gmtime())))
    logger.info("+----------------------------------------------------")
    logger.info("| operation mode: {}".format(config["operating_mode"]))

    FiringControl(config, gpio).run()


if __name__ == "__main__":
    main()
