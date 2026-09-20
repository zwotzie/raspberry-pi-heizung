import datetime
import unittest
from unittest.mock import Mock, patch

from heizung.ta import fieldlists


class TestFieldlists(unittest.TestCase):
    def test_get_measurements_maps_known_values(self):
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

            mapping = fieldlists.get_messurements("127.0.0.1", reset=True)

        bld_cls.assert_called_once_with("127.0.0.1", reset=True)
        self.assertEqual(mapping["timestamp"], now)
        self.assertEqual(mapping["aussentemperatur"], 12.3)
        self.assertEqual(mapping["speicher_1_kopf"], 70.1)
        self.assertEqual(mapping["d_solar_ladepumpe"], 1)
        self.assertEqual(mapping["d_heizung_pumpe"], 0)
        self.assertEqual(mapping["heizung_pumpe_drehzahl"], 44)
        self.assertNotIn("99", mapping)

    def test_get_measurements_keeps_known_fields_only(self):
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

            mapping = fieldlists.get_messurements("192.0.2.1")

        self.assertEqual(mapping["aussentemperatur"], 8.8)
        self.assertEqual(mapping["timestamp"], now)


if __name__ == "__main__":
    unittest.main()
