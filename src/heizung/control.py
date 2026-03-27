import datetime
import json
import logging
import sys
from time import sleep, time

import requests

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
        self.api_url = config["api_url"]
        self.ip = config["ip"]
        self.operating_mode: str = str(config.get("operating_mode", "pellets"))
        self._log2log = config.get("logger", "False")
        self._gpio = gpio
        self._relay_pin = config.get("relay_pin", 23)
        self._measurements_url: str | None = config.get("measurements_url")
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

    def transfer_data(self, data):
        """Push measurement data to the remote API."""
        try:
            result_insert = requests.post(
                self.api_url + "/databasewrapper/insertData", json=[[data]], timeout=60
            )
            result = requests.get(self.api_url + "/databasewrapper/updateTables", timeout=60)
            self._log(
                f"transfer data uvr1611=>API: insertData: {result_insert.status_code} "
                f"result: {result_insert.text} :: updateTables: {result.status_code}"
            )
        except requests.exceptions.Timeout:
            self._log("ERROR: Request timed out")
        except requests.exceptions.RequestException as e:
            self._log(f"ERROR: (RequestException) {e}")

    def _push_measurement(self, mapping: dict, heizung_an: int = 0) -> None:
        """POST the latest measurement to the FastAPI /measurements endpoint."""
        if not self._measurements_url:
            return
        payload = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in mapping.items()}
        payload["heizung_an"] = heizung_an
        try:
            requests.post(
                self._measurements_url.rstrip("/") + "/measurements",
                json=payload,
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            self._log(f"ERROR: could not push measurement to API: {e}")

    def get_current_measurements_from_blnet(self):
        """Fetch the latest dataset from the BL-Net and add it to the internal buffer."""
        field_list, mapping, api_data = get_messurements(ip=self.ip, reset=False)
        self.measurements[mapping["timestamp"]] = {
            "field_list": field_list,
            "mapping": mapping,
            "api_data": api_data,
        }
        self._log(f"dh={mapping}")
        self._log(f"fl={field_list}")
        self._log(f"ad={api_data}")

        if len(self.measurements) > 30:
            oldest = min(self.measurements.keys())
            del self.measurements[oldest]
        return field_list, mapping, api_data

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
        api_data: dict,
        start_list: list,
        solar_list: list,
        dt_now: str,
    ) -> str:
        """Evaluate collected lists, push data and return the firing decision."""
        api_data["digital1"] = 1 if self.firing_start else 0

        if "OFF" in start_list or not start_list:
            result = "OFF"
        elif "ON" in start_list:
            result = "ON"
        else:
            result = "-"

        self.transfer_data(api_data)

        if self._measurements_url and self.measurements:
            newest = self.measurements[max(self.measurements.keys())]["mapping"]
            self._push_measurement(newest, heizung_an=api_data.get("digital1", 0))

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
        api_data: dict = {}
        start_list: list = []
        solar_list: list = []
        dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for attempt in range(10):
            dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log("=" * 99)
            self._log(f"New test on measurements: {dt_now}")
            try:
                _, _, api_data = self.get_current_measurements_from_blnet()
                break
            except Exception as e:
                self._log(f"#{attempt} Error while fetching data from BLNET: {e}")
                if attempt == 9:
                    return "OFF"
                sleep(30)

        try:
            for measurement_date in self.measurements:
                heizungs_dict = self.measurements[measurement_date]["mapping"]
                minutes_ago = get_time_difference_from_now(heizungs_dict["timestamp"])
                do_firing = self._evaluate_firing(heizungs_dict)
                if minutes_ago <= 30:
                    start_list.append(do_firing)
                    solar_list.append(int(heizungs_dict["solar_strahlung"]))
        except IndexError:
            self._log("ERROR: there is nothing to examine???")

        return self._finalize_check(api_data, start_list, solar_list, dt_now)

    def _fetch_operating_mode(self) -> str:
        """Fetch the current operating mode from the API.

        Falls back to the value from config if the API is unreachable.
        """
        if not self._measurements_url:
            return self.operating_mode
        try:
            resp = requests.get(
                self._measurements_url.rstrip("/") + "/settings/operating-mode",
                timeout=5,
            )
            if resp.ok:
                return str(resp.json().get("operating_mode", self.operating_mode))
        except requests.exceptions.RequestException:
            pass
        return self.operating_mode

    def run(self):
        if len(sys.argv) > 1 and sys.argv[1] == "ON":
            self._log("Start burn-off per commandline...")
            self.start_firing()
            self._log("manually start done....")
            sleep(5)
            self.stop_firing()
            return

        while True:
            start = time()
            mode = self._fetch_operating_mode()
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
