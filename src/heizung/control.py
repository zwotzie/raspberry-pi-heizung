"""Control logic: polls the BL-Net, decides on firing and switches the boiler relay."""

import datetime
import json
import logging
import sys
import threading
from time import monotonic, sleep, time

from prometheus_client import start_http_server

from heizung import metrics, sdnotify
from heizung.ta.fieldlists import get_messurements

logger = logging.getLogger("heizung")

POLL_INTERVAL = 60  # seconds between BL-Net polls / control decisions
POLL_RETRIES = 3
POLL_RETRY_DELAY = 5
WATCHDOG_MAX_SILENCE = 240  # poller must have finished an attempt within this time


def get_time_difference_from_now(timestamp) -> int:
    """Return minutes elapsed since timestamp.

    Args:
        timestamp: Naive local ``datetime`` in the past.

    Returns:
        Whole minutes (rounded down).
    """
    time_diff = datetime.datetime.now() - timestamp
    return int(time_diff.total_seconds() / 60)


class FiringControl:
    """Polls sensor data in a background thread and switches the boiler relay.

    Two operating modes: ``pellets`` (switch on/off on decision changes) and
    ``firewood`` (relay follows the decision on every cycle).
    """

    def __init__(self, config: dict, gpio=None):
        """Initialize the controller.

        Args:
            config: Configuration dict from ``config.load_config()``.
            gpio: lgpio adapter (output/HIGH/LOW) when running on a Raspberry Pi,
                else None.
        """
        self.ip = config["ip"]
        self.operating_mode: str = str(config.get("operating_mode", "pellets"))
        self._gpio = gpio
        self._relay_pin = config.get("relay_pin", 23)
        self._metrics_port: int = int(config.get("metrics_port", 9100))
        self.firing_start: float | None = None
        self.measurements: dict[datetime.datetime, dict] = {}
        self._lock = threading.Lock()
        self._last_attempt: float = monotonic()
        self._polled = threading.Event()
        self._stop = threading.Event()
        metrics.configure(float(config.get("metrics_stale_after", metrics.DEFAULT_STALE_AFTER)))

    def start_firing(self):
        """Close relay to start/keep the boiler running."""
        message = "START_KESSEL: "
        if self._gpio is not None:
            message += "set RelaisHeizung-GPIO to HIGH"
            self._gpio.output(self._relay_pin, self._gpio.HIGH)
        else:
            message += "test only (no raspberry)"
        logger.info(message)

    def stop_firing(self):
        """Open relay to stop the boiler."""
        message = "STOP_KESSEL: "
        if self._gpio is not None:
            message += "set RelaisHeizung-GPIO to LOW"
            self._gpio.output(self._relay_pin, self._gpio.LOW)
        else:
            message += "test only (no raspberry)"
        logger.info(message)

    def _heizung_an(self) -> int:
        """1 while firing is active, else 0 (exported as metric)."""
        return 1 if self.firing_start else 0

    def _publish_metrics(self, mapping: dict, duration: float | None = None) -> None:
        """Expose the latest measurement on the Prometheus endpoint.

        Args:
            mapping: Measurement dict as returned by ``get_messurements``.
            duration: Duration of the poll in seconds.
        """
        metrics.set_operating_mode(self.operating_mode)
        metrics.set_measurement(mapping, heizung_an=self._heizung_an(), duration=duration)

    def get_current_measurements_from_blnet(self) -> dict:
        """Fetch the latest dataset from the BL-Net and add it to the internal buffer.

        Returns:
            The measurement dict.

        Raises:
            Exception: If the BL-Net cannot be reached or returns no data.
        """
        mapping = get_messurements(ip=self.ip, reset=False)
        with self._lock:
            self.measurements[mapping["timestamp"]] = mapping
            while len(self.measurements) > 30:
                del self.measurements[min(self.measurements)]
        logger.info(f"dh={mapping}")
        return mapping

    def poll_once(self) -> bool:
        """One poll cycle with short retries; always updates metrics. Never raises.

        Returns:
            True if a measurement was fetched, False after all retries failed.
        """
        start = monotonic()
        try:
            for attempt in range(POLL_RETRIES):
                try:
                    mapping = self.get_current_measurements_from_blnet()
                except Exception as e:
                    logger.warning(f"#{attempt} Error while fetching data from BLNET: {e}")
                    metrics.record_poll_failure(monotonic() - start)
                    if attempt < POLL_RETRIES - 1 and not self._stop.wait(POLL_RETRY_DELAY):
                        continue
                    return False
                self._publish_metrics(mapping, duration=monotonic() - start)
                return True
            return False
        finally:
            self._last_attempt = monotonic()
            self._polled.set()

    def _poll_loop(self) -> None:
        """Poll the BL-Net on a fixed monotonic cadence, independent of the control logic."""
        next_run = monotonic()
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception:
                logger.exception("unexpected error in poller")
            next_run += POLL_INTERVAL
            delay = next_run - monotonic()
            if delay < 0:  # overran: do not burst, restart the cadence
                next_run = monotonic()
                delay = 0
            self._stop.wait(delay)

    # ── helpers extracted to reduce cognitive complexity ──────────────────────

    @staticmethod
    def _evaluate_firing(m: dict) -> str:
        """Return 'ON', 'OFF' or '-' for a single measurement dict.

        Args:
            m: Measurement dict with the storage temperature fields.

        Returns:
            "OFF" if the storage bottom is hot, "ON" if the storage is low or
            all cold, otherwise "-".
        """
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
        start_list: list,
        solar_list: list,
        dt_now: str,
    ) -> str:
        """Evaluate collected lists and return the firing decision.

        Args:
            start_list: Per-measurement results of ``_evaluate_firing``.
            solar_list: Solar radiation values of the same period.
            dt_now: Current time as formatted string (for logging).

        Returns:
            "ON", "OFF" or "-". "OFF" wins on missing data or high solar radiation.
        """
        if "OFF" in start_list or not start_list:
            result = "OFF"
        elif "ON" in start_list:
            result = "ON"
        else:
            result = "-"

        mean_solar = sum(solar_list) // len(solar_list) if solar_list else 0
        if mean_solar > 400:
            result = "OFF"

        logger.info(json.dumps({"t": dt_now, "mean solar": mean_solar, "solar_list_30m": solar_list}))
        logger.info(
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
        """Firewood mode: relay simply follows the decision (ON, otherwise off).

        Args:
            result: Decision from ``check_measurements``.
        """
        if result == "ON":
            self.start_firing()
            self.firing_start = time()
        else:
            self.stop_firing()
            self.firing_start = None

    def _handle_pellets(self, result: str) -> None:
        """Pellet mode: start only once on ON, stop on OFF; '-' keeps the current state.

        Args:
            result: Decision from ``check_measurements``.
        """
        if result == "ON":
            if self.firing_start is None:
                self.firing_start = time()
                self.start_firing()
        elif result == "OFF":
            self.stop_firing()
            if self.firing_start:
                logger.info(
                    f"combustion time: {round((time() - self.firing_start) / 3600, 1)!r} hours"
                )
                self.firing_start = None

    # ── public API ────────────────────────────────────────────────────────────

    def check_measurements(self) -> str:
        """
        Evaluate the buffered measurements of the last 30 minutes and decide whether firing is needed.
        Without recent data the result is "OFF".

        Returns:
            "ON", "OFF" or "-".
        """
        start_list: list = []
        solar_list: list = []
        dt_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 99)
        logger.info(f"New test on measurements: {dt_now}")

        with self._lock:
            buffered = list(self.measurements.values())
        for heizungs_dict in buffered:
            if get_time_difference_from_now(heizungs_dict["timestamp"]) <= 30:
                start_list.append(self._evaluate_firing(heizungs_dict))
                solar_list.append(int(heizungs_dict["solar_strahlung"]))
        if not start_list:
            logger.warning("no measurements within the last 30 minutes")

        return self._finalize_check(start_list, solar_list, dt_now)

    def run(self):
        """Run the daemon: start metrics server and poller, then the control loop (never returns).

        With the command line argument ``ON`` the relay is only switched on
        for 5 seconds (manual burn-off test) and the function returns.
        Sends READY/WATCHDOG notifications to systemd.
        """
        if len(sys.argv) > 1 and sys.argv[1] == "ON":
            logger.info("Start burn-off per commandline...")
            self.start_firing()
            logger.info("manually start done....")
            sleep(5)
            self.stop_firing()
            return

        start_http_server(self._metrics_port)
        logger.info(f"Prometheus metrics on :{self._metrics_port}/metrics")

        threading.Thread(target=self._poll_loop, name="blnet-poller", daemon=True).start()
        sdnotify.notify("READY=1")
        self._polled.wait(timeout=POLL_RETRIES * (POLL_RETRY_DELAY + 60))

        next_run = monotonic()
        while True:
            mode = self.operating_mode
            try:
                result = self.check_measurements()
                if mode == "firewood":
                    self._handle_firewood(result)
                elif mode == "pellets":
                    self._handle_pellets(result)
                metrics.set_heizung_an(self._heizung_an())
            except Exception:
                logger.exception("error in control loop, switching off")
                try:
                    self.stop_firing()
                except Exception:
                    logger.exception("stop_firing failed")

            # only prove liveness while the poller keeps finishing attempts
            if monotonic() - self._last_attempt < WATCHDOG_MAX_SILENCE:
                sdnotify.notify("WATCHDOG=1")

            next_run += POLL_INTERVAL
            delay = next_run - monotonic()
            if delay < 0:
                next_run = monotonic()
                delay = 0
            sleep(delay)


if __name__ == "__main__":
    from heizung.config import load_config, setup_gpio

    _config = load_config()
    _, _gpio = setup_gpio()
    fc = FiringControl(_config, _gpio)
    fc.run()
