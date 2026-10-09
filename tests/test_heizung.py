import datetime
import unittest
from unittest.mock import patch

from heizung.control import FiringControl, get_time_difference_from_now

PELLETS_CONFIG = {
    "ip": "127.0.0.1",
    "operating_mode": "pellets",
    "relay_pin": 23,
    "metrics_port": 9100,
}
FIREWOOD_CONFIG = {**PELLETS_CONFIG, "operating_mode": "firewood"}


class StopLoop(Exception):
    pass


class TestGetTimeDifference(unittest.TestCase):
    def test_returns_elapsed_minutes(self):
        timestamp = datetime.datetime.now() - datetime.timedelta(minutes=17, seconds=50)
        self.assertEqual(get_time_difference_from_now(timestamp), 17)


def _mapping(**overrides):
    base = {
        "timestamp": datetime.datetime.now(),
        "speicher_1_kopf": 55,
        "speicher_2_kopf": 70,
        "speicher_3_kopf": 45,
        "speicher_4_mitte": 40,
        "speicher_5_boden": 40,
        "solar_strahlung": 200,
    }
    base.update(overrides)
    return base


class TestCheckMeasurements(unittest.TestCase):
    def _check(self, mapping=None, operating_mode="pellets"):
        control = FiringControl({**PELLETS_CONFIG, "operating_mode": operating_mode})
        if mapping is not None:
            control.measurements[mapping["timestamp"]] = mapping
        return control.check_measurements()

    def test_returns_on_for_low_storage_temps(self):
        m = _mapping(
            speicher_1_kopf=40,
            speicher_2_kopf=50,
            speicher_3_kopf=35,
            speicher_4_mitte=30,
            speicher_5_boden=28,
            solar_strahlung=100,
        )
        self.assertEqual(self._check(m), "ON")

    def test_returns_off_for_hot_bottom_storage(self):
        self.assertEqual(self._check(_mapping(speicher_5_boden=73)), "OFF")

    def test_solar_override_switches_off(self):
        m = _mapping(
            speicher_1_kopf=40,
            speicher_2_kopf=50,
            speicher_3_kopf=35,
            speicher_4_mitte=30,
            speicher_5_boden=28,
            solar_strahlung=800,
        )
        self.assertEqual(self._check(m), "OFF")

    def test_returns_dash_for_neutral_recent_values(self):
        self.assertEqual(self._check(_mapping()), "-")

    def test_returns_off_without_recent_data(self):
        old = _mapping(timestamp=datetime.datetime.now() - datetime.timedelta(minutes=45))
        self.assertEqual(self._check(old), "OFF")
        self.assertEqual(self._check(None), "OFF")


class TestPollOnce(unittest.TestCase):
    def test_retries_then_records_failure_metrics(self):
        control = FiringControl(PELLETS_CONFIG)
        with (
            patch.object(control, "get_current_measurements_from_blnet", side_effect=RuntimeError("down")) as fetch,
            patch.object(control._stop, "wait", return_value=False),
            patch("heizung.control.metrics.record_poll_failure") as failure,
            patch.object(control, "_publish_metrics") as publish,
        ):
            ok = control.poll_once()

        self.assertFalse(ok)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(failure.call_count, 3)
        publish.assert_not_called()
        self.assertTrue(control._polled.is_set())

    def test_success_publishes_metrics(self):
        control = FiringControl(PELLETS_CONFIG)
        mapping = _mapping()
        with (
            patch.object(control, "get_current_measurements_from_blnet", return_value=mapping),
            patch.object(control, "_publish_metrics") as publish,
        ):
            self.assertTrue(control.poll_once())
        publish.assert_called_once()


class TestPushModePollOnce(unittest.TestCase):
    """poll_once pushes the updated snapshot when push_url is configured."""

    def test_push_mode_success_pushes_with_job_and_instance(self):
        control = FiringControl(
            {**PELLETS_CONFIG, "push_url": "http://vm", "push_job": "h1", "push_instance": "i1"}
        )
        mapping = _mapping()
        with (
            patch.object(control, "get_current_measurements_from_blnet", return_value=mapping),
            patch("heizung.control.metrics.push") as push,
        ):
            self.assertTrue(control.poll_once())
        push.assert_called_once_with("http://vm", job="h1", instance="i1")

    def test_push_mode_failure_pushes_too(self):
        control = FiringControl({**PELLETS_CONFIG, "push_url": "http://vm"})
        with (
            patch.object(control, "get_current_measurements_from_blnet", side_effect=RuntimeError("down")),
            patch.object(control._stop, "wait", return_value=False),
            patch("heizung.control.metrics.push") as push,
        ):
            self.assertFalse(control.poll_once())
        push.assert_called_once()

    def test_scrape_mode_poll_does_not_push(self):
        control = FiringControl(PELLETS_CONFIG)
        mapping = _mapping()
        with (
            patch.object(control, "get_current_measurements_from_blnet", return_value=mapping),
            patch("heizung.control.metrics.push") as push,
        ):
            self.assertTrue(control.poll_once())
        push.assert_not_called()

    def test_push_failure_is_not_fatal(self):
        control = FiringControl({**PELLETS_CONFIG, "push_url": "http://vm"})
        mapping = _mapping()
        with (
            patch.object(control, "get_current_measurements_from_blnet", return_value=mapping),
            patch("heizung.control.metrics.push", side_effect=RuntimeError("vm down")),
        ):
            self.assertTrue(control.poll_once())


class TestRunPushMode(unittest.TestCase):
    def test_run_skips_http_server_in_push_mode(self):
        control = FiringControl({**PELLETS_CONFIG, "push_url": "http://vm"})
        with (
            patch.object(control, "check_measurements", return_value="OFF"),
            patch.object(control, "stop_firing"),
            patch("heizung.control.start_http_server") as http_server,
            patch.object(control, "_poll_loop"),
            patch.object(control._polled, "wait"),
            patch("heizung.control.sleep", side_effect=StopLoop),
            self.assertRaises(StopLoop),
        ):
            control.run()
        http_server.assert_not_called()


class TestMetricsCollector(unittest.TestCase):
    def setUp(self):
        from heizung import metrics

        self.metrics = metrics
        metrics._state.reset()

    def _samples(self):
        return {
            s.name: s.value
            for fam in self.metrics.HeizungCollector().collect()
            for s in fam.samples
        }

    def test_no_sensor_values_before_first_poll(self):
        samples = self._samples()
        self.assertEqual(samples["heizung_up"], 0)
        self.assertNotIn("aussentemperatur", samples)

    def test_fresh_data_is_exposed_without_invented_values(self):
        self.metrics.set_measurement({"aussentemperatur": 5.2, "d_heizung_pumpe": 1}, heizung_an=1)
        samples = self._samples()
        self.assertEqual(samples["heizung_up"], 1)
        self.assertEqual(samples["aussentemperatur"], 5.2)
        self.assertEqual(samples["heizung_an"], 1)
        self.assertNotIn("kessel_rl", samples)
        self.assertNotIn("d_kessel_ladepumpe", samples)

    def test_stale_data_is_omitted(self):
        self.metrics.set_measurement({"aussentemperatur": 5.2})
        with patch("heizung.metrics.time.time", return_value=self.metrics._state.fetched_at + 1000):
            samples = self._samples()
        self.assertEqual(samples["heizung_up"], 0)
        self.assertNotIn("aussentemperatur", samples)
        self.assertGreater(samples["heizung_data_age_seconds"], 900)

    def test_poll_failures_are_counted(self):
        self.metrics.record_poll_failure()
        self.assertEqual(self._samples()["heizung_poll_errors_total"], 1)


class TestPublishMetrics(unittest.TestCase):
    def test_publish_sets_measurement_and_operating_mode(self):
        control = FiringControl(PELLETS_CONFIG)
        control.firing_start = 1.0
        mapping = {"timestamp": datetime.datetime(2026, 3, 26, 12, 0, 0), "aussentemperatur": 5.2}
        with (
            patch("heizung.control.metrics.set_measurement") as set_m,
            patch("heizung.control.metrics.set_operating_mode") as set_mode,
        ):
            control._publish_metrics(mapping)

        set_mode.assert_called_once_with("pellets")
        set_m.assert_called_once_with(mapping, heizung_an=1, duration=None)


class TestBufferLimit(unittest.TestCase):
    def test_limits_buffer_to_30_entries(self):
        control = FiringControl(PELLETS_CONFIG)
        base = datetime.datetime.now() - datetime.timedelta(minutes=40)
        for i in range(30):
            ts = base + datetime.timedelta(minutes=i)
            control.measurements[ts] = {"timestamp": ts}

        newest = datetime.datetime.now()
        mapping = {"timestamp": newest}

        with patch(
            "heizung.control.get_messurements",
            return_value=mapping,
        ):
            control.get_current_measurements_from_blnet()

        self.assertEqual(len(control.measurements), 30)
        self.assertIn(newest, control.measurements)
        self.assertNotIn(base, control.measurements)


class TestRun(unittest.TestCase):
    def test_control_loop_survives_errors_and_switches_off(self):
        control = FiringControl(PELLETS_CONFIG)
        with (
            patch.object(control, "check_measurements", side_effect=KeyError("x")),
            patch.object(control, "stop_firing") as stop_firing,
            patch("heizung.control.start_http_server"),
            patch.object(control, "_poll_loop"),
            patch.object(control._polled, "wait"),
            patch("heizung.control.sleep", side_effect=StopLoop),
            self.assertRaises(StopLoop),
        ):
            control.run()

        stop_firing.assert_called_once()

    def test_firewood_starts_firing_when_result_on(self):
        control = FiringControl(FIREWOOD_CONFIG)
        with (
            patch.object(control, "check_measurements", return_value="ON"),
            patch.object(control, "start_firing") as start_firing,
            patch.object(control, "stop_firing") as stop_firing,
            patch("heizung.control.start_http_server"),
            patch.object(control, "_poll_loop"),
            patch.object(control._polled, "wait"),
            patch("heizung.control.time", side_effect=[11.0]),
            patch("heizung.control.sleep", side_effect=StopLoop),
            self.assertRaises(StopLoop),
        ):
            control.run()

        start_firing.assert_called_once()
        stop_firing.assert_not_called()
        self.assertEqual(control.firing_start, 11.0)

    def test_pellets_stops_and_resets_after_off(self):
        control = FiringControl(PELLETS_CONFIG)

        def stop_after_second_sleep(_):
            stop_after_second_sleep.calls += 1
            if stop_after_second_sleep.calls == 2:
                raise StopLoop

        stop_after_second_sleep.calls = 0

        with (
            patch.object(control, "check_measurements", side_effect=["ON", "OFF"]),
            patch.object(control, "start_firing") as start_firing,
            patch.object(control, "stop_firing") as stop_firing,
            patch("heizung.control.start_http_server"),
            patch.object(control, "_poll_loop"),
            patch.object(control._polled, "wait"),
            patch("heizung.control.time", side_effect=[11.0, 12.0, 13.0]),
            patch("heizung.control.sleep", side_effect=stop_after_second_sleep),
            self.assertRaises(StopLoop),
        ):
            control.run()

        start_firing.assert_called_once()
        stop_firing.assert_called_once()
        self.assertIsNone(control.firing_start)

    def test_manual_on_argument_triggers_start_sleep_and_stop(self):
        control = FiringControl(PELLETS_CONFIG)
        with (
            patch("heizung.control.sys.argv", ["heizung", "ON"]),
            patch.object(control, "start_firing") as start_firing,
            patch.object(control, "stop_firing") as stop_firing,
            patch("heizung.control.sleep") as sleep_mock,
        ):
            control.run()

        start_firing.assert_called_once()
        stop_firing.assert_called_once()
        sleep_mock.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
