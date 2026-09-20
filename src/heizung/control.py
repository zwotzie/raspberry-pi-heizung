import datetime
import json
import logging
import sys
from time import sleep, time

from prometheus_client import start_http_server

from heizung import metrics
from heizung.ta.fieldlists import get_messurements

logger = logging.getLogger("heizung")


def get_time_difference_from_now(timestamp) -> int:
    """Return minutes elapsed since timestamp."""
    time_diff = datetime.datetime.now() - timestamp
    return int(time_diff.total_seconds() / 60)


class FiringControl:
    def __init__(self, config: dict, gpio=None):
        """
        :param config: dict from config.load_config()
        :param gpio:   RPi.GPIO module when running on a Raspberry Pi, else None
        """
        self.ip = config["ip"]
        self.operating_mode: str = str(config.get("operating_mode", "pellets"))
        self._log2log = config.get("logger", "False")
        self._gpio = gpio
        self._relay_pin = config.get("relay_pin", 23)
        self._metrics_port: int = int(config.get("metrics_port", 9100))
        self.firing_start: float | None = None
        self.measurements: dict[datetime.datetime, dict] = {}

    def _log(self, message):
        if self._log2log == "True":
            logger.info(message)
        else:
            print(message)

    def start_firing(self):
        """Close relay to start/keep the boiler running."""
        message = "START_KESSEL: "
        if self._gpio is not None:
            message += "set RelaisHeizung-GPIO to HIGH"
            self._gpio.output(self._relay_pin, self._gpio.HIGH)
        else:
            message += "test only (no raspberry)"
        self._log(message)

    def stop_firing(self):
        """Open relay to stop the boiler."""
        message = "STOP_KESSEL: "
        if self._gpio is not None:
            message += "set RelaisHeizung-GPIO to LOW"
            self._gpio.output(self._relay_pin, self._gpio.LOW)
        else:
            message += "test only (no raspberry)"
        self._log(message)

    def _publish_metrics(self, mapping: dict, heizung_an: int) -> None:
        """Expose the latest measurement on the Prometheus endpoint."""
        metrics.set_operating_mode(self.operating_mode)
        metrics.set_measurement(mapping, heizung_an=heizung_an)

    def get_current_measurements_from_blnet(self) -> dict:
        """Fetch the latest dataset from the BL-Net and add it to the internal buffer."""
        mapping = get_messurements(ip=self.ip, reset=False)
        self.measurements[mapping["timestamp"]] = mapping
        self._log(f"dh={mapping}")

        if len(self.measurements) > 30:
            oldest = min(self.measurements.keys())
            del self.measurements[oldest]
        return mapping

    # ── helpers extracted to reduce cognitive complexity ──────────────────────

    @staticmethod
    def _evaluate_firing(m: dict) -> str:
        """Return 'ON', 'OFF' or '-' for a single measurement dict."""
        if m["speicher_5_boden"] > 72:
            return "OFF"
        low_storage = (
            m["speicher_3_kopf"] < 39
            and m["speicher_4_mitte"] < 35
            and m["speicher_5_boden"] < 32
            and m["speicher_2_kopf"] < 60
        )
        all_cold = all(
            m[k] < 45
            for k in [
                "speicher_1_kopf",
                "speicher_2_kopf",
                "speicher_3_kopf",
                "speicher_4_mitte",
                "speicher_5_boden",
            ]
        )
        return "ON" if (low_storage or all_cold) else "-"

    def _finalize_check(
        self,
        mapping: dict,
        start_list: list,
        solar_list: list,
        dt_now: str,
    ) -> str:
        """Evaluate collected lists, publish metrics and return the firing decision."""
        heizung_an = 1 if self.firing_start else 0

        if "OFF" in start_list or not start_list:
            result = "OFF"
        elif "ON" in start_list:
            result = "ON"
        else:
            result = "-"

        self._publish_metrics(mapping, heizung_an=heizung_an)

        mean_solar = sum(solar_list) // len(solar_list) if solar_list else 0
        if mean_solar > 400:
            result = "OFF"

        self._log(json.dumps({"t": dt_now, "mean solar": mean_solar, "solar_list_30m": solar_list}))
        self._log(
            json.dumps(
                {
                    "t": dt_now,
                    "firing_decision": result,
                    "start_list_30m": start_list,
                    "fire_since": self.firing_start,
                }
            )
        )
        return result

    def _handle_firewood(self, result: str) -> None:
        if result == "ON":
            self.start_firing()
            self.firing_start = time()
        else:
            self.stop_firing()
            self.firing_start = None

    def _handle_pellets(self, result: str) -> None:
        if result == "ON":
            if self.firing_start is None:
                self.firing_start = time()
                self.start_firing()
        elif result == "OFF":
            self.stop_firing()
            if self.firing_start:
                self._log(
                    f"combustion time: {round((time() - self.firing_start) / 3600, 1)!r} hours"
                )
                self.firing_start = None

    # ── public API ────────────────────────────────────────────────────────────

    def check_measurements(self) -> str:
        """
        Evaluate the most recent measurements and decide whether firing is needed.

        :returns: "ON", "OFF" or "-"
        """
        mapping: dict = {}
        start_list: list = []
        solar_list: list = []
        dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for attempt in range(10):
            dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log("=" * 99)
            self._log(f"New test on measurements: {dt_now}")
            try:
                mapping = self.get_current_measurements_from_blnet()
                break
            except Exception as e:
                self._log(f"#{attempt} Error while fetching data from BLNET: {e}")
                if attempt == 9:
                    return "OFF"
                sleep(30)

        try:
            for measurement_date in self.measurements:
                heizungs_dict = self.measurements[measurement_date]
                minutes_ago = get_time_difference_from_now(heizungs_dict["timestamp"])
                do_firing = self._evaluate_firing(heizungs_dict)
                if minutes_ago <= 30:
                    start_list.append(do_firing)
                    solar_list.append(int(heizungs_dict["solar_strahlung"]))
        except IndexError:
            self._log("ERROR: there is nothing to examine???")

        return self._finalize_check(mapping, start_list, solar_list, dt_now)

    def run(self):
        if len(sys.argv) > 1 and sys.argv[1] == "ON":
            self._log("Start burn-off per commandline...")
            self.start_firing()
            self._log("manually start done....")
            sleep(5)
            self.stop_firing()
            return

        start_http_server(self._metrics_port)
        self._log(f"Prometheus metrics on :{self._metrics_port}/metrics")

        while True:
            start = time()
            mode = self.operating_mode
            result = self.check_measurements()

            if mode == "firewood":
                self._handle_firewood(result)
            elif mode == "pellets":
                self._handle_pellets(result)

            to_sleep = 60 - (time() - start)
            if to_sleep > 0:
                sleep(to_sleep)


if __name__ == "__main__":
    from heizung.config import load_config, setup_gpio

    _config = load_config()
    _, _gpio = setup_gpio()
    fc = FiringControl(_config, _gpio)
    fc.run()
