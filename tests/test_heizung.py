import datetime
import unittest
from unittest.mock import patch

import requests

from heizung.control import FiringControl, get_time_difference_from_now

PELLETS_CONFIG = {
    "api_url": "http://api.invalid",
    "ip": "127.0.0.1",
    "operating_mode": "pellets",
    "logger": "False",
    "relay_pin": 23,
    "measurements_url": None,
}
FIREWOOD_CONFIG = {**PELLETS_CONFIG, "operating_mode": "firewood"}


class StopLoop(Exception):
    pass


class TestGetTimeDifference(unittest.TestCase):
    def test_returns_elapsed_minutes(self):
        timestamp = datetime.datetime.now() - datetime.timedelta(minutes=17, seconds=50)
        self.assertEqual(get_time_difference_from_now(timestamp), 17)


class TestCheckMeasurements(unittest.TestCase):
    def _control(self, operating_mode="pellets"):
        return FiringControl({**PELLETS_CONFIG, "operating_mode": operating_mode})

    def _fake_fetch(self, control, mapping):
        def _fetch():
            control.measurements[mapping["timestamp"]] = {
                "field_list": {},
                "mapping": mapping,
                "api_data": {"foo": "bar"},
            }
            return {}, mapping, {"foo": "bar"}

        return _fetch

    def test_returns_on_for_low_storage_temps(self):
        control = self._control()
        now = datetime.datetime.now()
        mapping = {
            "timestamp": now,
            "speicher_1_kopf": 40,
            "speicher_2_kopf": 50,
            "speicher_3_kopf": 35,
            "speicher_4_mitte": 30,
            "speicher_5_boden": 28,
            "solar_strahlung": 100,
        }
        with (
            patch.object(
                control,
                "get_current_measurements_from_blnet",
                side_effect=self._fake_fetch(control, mapping),
            ),
            patch.object(control, "transfer_data") as transfer_data,
        ):
            result = control.check_measurements()

        self.assertEqual(result, "ON")
        transfer_data.assert_called_once()

    def test_returns_off_for_hot_bottom_storage(self):
        control = self._control()
        now = datetime.datetime.now()
        mapping = {
            "timestamp": now,
            "speicher_1_kopf": 35,
            "speicher_2_kopf": 35,
            "speicher_3_kopf": 35,
            "speicher_4_mitte": 35,
            "speicher_5_boden": 73,
            "solar_strahlung": 120,
        }
        with (
            patch.object(
                control,
                "get_current_measurements_from_blnet",
                side_effect=self._fake_fetch(control, mapping),
            ),
            patch.object(control, "transfer_data"),
        ):
            result = control.check_measurements()

        self.assertEqual(result, "OFF")

    def test_solar_override_switches_off(self):
        control = self._control()
        now = datetime.datetime.now()
        mapping = {
            "timestamp": now,
            "speicher_1_kopf": 40,
            "speicher_2_kopf": 50,
            "speicher_3_kopf": 35,
            "speicher_4_mitte": 30,
            "speicher_5_boden": 28,
            "solar_strahlung": 800,
        }
        with (
            patch.object(
                control,
                "get_current_measurements_from_blnet",
                side_effect=self._fake_fetch(control, mapping),
            ),
            patch.object(control, "transfer_data"),
        ):
            result = control.check_measurements()

        self.assertEqual(result, "OFF")

    def test_returns_dash_for_neutral_recent_values(self):
        control = self._control()
        now = datetime.datetime.now()
        mapping = {
            "timestamp": now,
            "speicher_1_kopf": 55,
            "speicher_2_kopf": 70,
            "speicher_3_kopf": 45,
            "speicher_4_mitte": 40,
            "speicher_5_boden": 40,
            "solar_strahlung": 200,
        }
        with (
            patch.object(
                control,
                "get_current_measurements_from_blnet",
                side_effect=self._fake_fetch(control, mapping),
            ),
            patch.object(control, "transfer_data"),
        ):
            result = control.check_measurements()

        self.assertEqual(result, "-")

    def test_returns_off_after_10_failed_attempts(self):
        control = self._control()
        with (
            patch.object(
                control,
                "get_current_measurements_from_blnet",
                side_effect=RuntimeError("BLNET down"),
            ),
            patch("heizung.control.sleep") as sleep_mock,
            patch.object(control, "transfer_data") as transfer_data,
        ):
            result = control.check_measurements()

        self.assertEqual(result, "OFF")
        self.assertEqual(sleep_mock.call_count, 9)
        transfer_data.assert_not_called()


class TestTransferData(unittest.TestCase):
    def test_handles_timeout_without_raising(self):
        control = FiringControl(PELLETS_CONFIG)
        with (
            patch("heizung.control.requests.post", side_effect=requests.exceptions.Timeout),
            patch.object(control, "_log") as log_mock,
        ):
            control.transfer_data({"x": 1})

        log_mock.assert_called_with("ERROR: Request timed out")


class TestPushMeasurement(unittest.TestCase):
    def test_posts_payload_with_iso_timestamp_and_heizung_an(self):
        cfg = {**PELLETS_CONFIG, "measurements_url": "http://api.invalid"}
        control = FiringControl(cfg)
        import datetime as dt

        now = dt.datetime(2026, 3, 26, 12, 0, 0)
        mapping = {"timestamp": now, "aussentemperatur": 5.2}

        with patch("heizung.control.requests.post") as post_mock:
            control._push_measurement(mapping, heizung_an=1)

        post_mock.assert_called_once()
        _, kwargs = post_mock.call_args
        assert kwargs["json"]["timestamp"] == now.isoformat()
        assert kwargs["json"]["heizung_an"] == 1
        assert kwargs["json"]["aussentemperatur"] == 5.2
        assert "http://api.invalid/measurements" in post_mock.call_args[0][0]

    def test_skips_post_when_measurements_url_is_none(self):
        control = FiringControl(PELLETS_CONFIG)
        with patch("heizung.control.requests.post") as post_mock:
            control._push_measurement({"timestamp": None}, heizung_an=0)

        post_mock.assert_not_called()

    def test_logs_error_on_request_exception(self):
        cfg = {**PELLETS_CONFIG, "measurements_url": "http://api.invalid"}
        control = FiringControl(cfg)
        with (
            patch(
                "heizung.control.requests.post",
                side_effect=requests.exceptions.ConnectionError("down"),
            ),
            patch.object(control, "_log") as log_mock,
        ):
            control._push_measurement({"timestamp": None}, heizung_an=0)

        self.assertTrue(any("could not push" in str(c) for c in log_mock.call_args_list))


class TestFetchOperatingMode(unittest.TestCase):
    def test_returns_mode_from_api(self):
        cfg = {**PELLETS_CONFIG, "measurements_url": "http://api.invalid"}
        control = FiringControl(cfg)
        with patch("heizung.control.requests.get") as get_mock:
            get_mock.return_value.ok = True
            get_mock.return_value.json.return_value = {"operating_mode": "firewood"}
            self.assertEqual(control._fetch_operating_mode(), "firewood")

    def test_falls_back_to_config_when_api_unreachable(self):
        cfg = {**PELLETS_CONFIG, "measurements_url": "http://api.invalid"}
        control = FiringControl(cfg)
        with patch(
            "heizung.control.requests.get",
            side_effect=requests.exceptions.ConnectionError,
        ):
            self.assertEqual(control._fetch_operating_mode(), "pellets")

    def test_falls_back_to_config_when_no_url_configured(self):
        control = FiringControl(PELLETS_CONFIG)
        self.assertEqual(control._fetch_operating_mode(), "pellets")

    def test_limits_buffer_to_30_entries(self):
        control = FiringControl(PELLETS_CONFIG)
        base = datetime.datetime.now() - datetime.timedelta(minutes=40)
        for i in range(30):
            ts = base + datetime.timedelta(minutes=i)
            control.measurements[ts] = {"mapping": {"timestamp": ts}}

        newest = datetime.datetime.now()
        mapping = {"timestamp": newest}

        with patch(
            "heizung.control.get_messurements",
            return_value=([], mapping, {"date": "x"}),
        ):
            control.get_current_measurements_from_blnet()

        self.assertEqual(len(control.measurements), 30)
        self.assertIn(newest, control.measurements)
        self.assertNotIn(base, control.measurements)


class TestRun(unittest.TestCase):
    def test_firewood_starts_firing_when_result_on(self):
        control = FiringControl(FIREWOOD_CONFIG)
        with (
            patch.object(control, "check_measurements", return_value="ON"),
            patch.object(control, "start_firing") as start_firing,
            patch.object(control, "stop_firing") as stop_firing,
            patch("heizung.control.time", side_effect=[10.0, 11.0, 12.0]),
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
            patch("heizung.control.time", side_effect=[10.0, 11.0, 12.0, 13.0, 14.0, 15.0]),
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
