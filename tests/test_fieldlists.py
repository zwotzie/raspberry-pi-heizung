import datetime
import unittest
from unittest.mock import Mock, patch

from heizung.ta import fieldlists


class TestFieldlists(unittest.TestCase):
    def test_get_measurements_maps_known_values_and_builds_api_payload(self):
        now = datetime.datetime(2026, 3, 26, 12, 0, 0)
        latest = {
            0: {
                "analog": {1: 12.3, 2: 70.1, 99: 123},
                "digital": {3: 1, 6: 0, 99: 1},
                "speed": {3: 44, 4: None},
                "power": {1: None, 2: 2200},
                "energy": {1: 1500.5, 2: None},
            },
            "date": now,
        }

        with patch("heizung.ta.fieldlists.BLNETDirect") as bld_cls:
            bld = Mock()
            bld.get_latest.return_value = latest
            bld_cls.return_value = bld

            field_list, mapping, api_data = fieldlists.get_messurements("127.0.0.1", reset=True)

        bld_cls.assert_called_once_with("127.0.0.1", reset=True)
        self.assertEqual(mapping["timestamp"], now)
        self.assertEqual(mapping["aussentemperatur"], 12.3)
        self.assertEqual(mapping["speicher_1_kopf"], 70.1)
        self.assertEqual(mapping["d_solar_ladepumpe"], 1)
        self.assertEqual(mapping["d_heizung_pumpe"], 0)
        self.assertEqual(mapping["heizung_d"], 44)
        self.assertNotIn("99", mapping)

        self.assertEqual(len(field_list), len(fieldlists.fields))
        self.assertEqual(field_list[0], now)
        self.assertEqual(api_data["date"], f"{now}")
        self.assertEqual(api_data["analog1"], 12.3)
        self.assertEqual(api_data["digital3"], 1)
        self.assertEqual(api_data["speed4"], "NULL")
        self.assertEqual(api_data["power1"], "NULL")
        self.assertEqual(api_data["energy2"], "NULL")

    def test_get_measurements_sets_missing_fields_to_zero_in_field_list(self):
        now = datetime.datetime(2026, 3, 26, 12, 5, 0)
        latest = {
            0: {
                "analog": {1: 8.8},
                "digital": {},
                "speed": {},
                "power": {},
                "energy": {},
            },
            "date": now,
        }

        with patch("heizung.ta.fieldlists.BLNETDirect") as bld_cls:
            bld = Mock()
            bld.get_latest.return_value = latest
            bld_cls.return_value = bld

            field_list, mapping, api_data = fieldlists.get_messurements("192.0.2.1")

        idx_speicher_2 = fieldlists.fields.index("speicher_2_kopf")
        idx_heizung_d = fieldlists.fields.index("heizung_d")
        self.assertEqual(mapping["aussentemperatur"], 8.8)
        self.assertEqual(field_list[idx_speicher_2], 0)
        self.assertEqual(field_list[idx_heizung_d], 0)
        self.assertEqual(api_data["frame"], 1)

    def test_fields_example2_returns_payload_and_mapping_and_posts_data(self):
        fake_response = Mock()
        fake_response.text = "ok"
        fake_response.status_code = 200

        with patch.object(fieldlists.requests, "post", return_value=fake_response) as post_mock:
            field_list, mapping, api_data = fieldlists.fields_example2()

        self.assertEqual(len(field_list), len(fieldlists.fields))
        self.assertIn("timestamp", mapping)
        self.assertEqual(api_data["frame"], "frame1")
        self.assertIn("analog1", api_data)
        post_mock.assert_called_once()

    def test_transfer_data_helpers_post_payload_without_network_errors(self):
        fake_response = Mock()
        fake_response.text = "stored"
        fake_response.status_code = 201

        with patch.object(fieldlists.requests, "post", return_value=fake_response) as post_mock:
            fieldlists.transfer_data_ok()
            fieldlists.transfer_data()

        self.assertEqual(post_mock.call_count, 2)
        first_payload = post_mock.call_args_list[0].kwargs["json"]
        second_payload = post_mock.call_args_list[1].kwargs["json"]
        self.assertTrue(isinstance(first_payload, list) and first_payload)
        self.assertTrue(isinstance(second_payload, list) and second_payload)
