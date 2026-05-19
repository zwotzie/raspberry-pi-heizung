import struct
import unittest

from heizung.ta.blnet_parser import (
    TYPE_DIGITAL,
    TYPE_NONE,
    TYPE_RAS,
    TYPE_TEMP,
    TYPE_VOLUME,
    BLNETParser,
)


def _build_dataset(include_timestamp):
    analog = [
        TYPE_TEMP | 253,
        TYPE_TEMP | 0x8000 | 0x0FCE,
        TYPE_VOLUME | 3,
        TYPE_DIGITAL | 0x8000,
        TYPE_RAS | 100,
        TYPE_NONE | 77,
    ] + [0] * 10

    body = struct.pack("<16H", *analog)
    body += struct.pack(
        "<H4sBLHHLHH",
        0b0000000000001010,
        bytes([0x01, 0x80, 0x1F, 0x85]),
        1,
        1000,
        20,
        1,
        5120,
        30,
        2,
    )

    if not include_timestamp:
        return body

    return body + struct.pack("<BBBBBB", 1, 2, 3, 4, 5, 24)


class TestBLNETParser(unittest.TestCase):
    def test_to_dict_parses_values_and_timestamp_from_61_byte_dataset(self):
        parser = BLNETParser(_build_dataset(include_timestamp=True))
        result = parser.to_dict()

        self.assertEqual(result["date"].year, 2024)
        self.assertEqual(result["date"].month, 5)
        self.assertEqual(result["date"].day, 4)
        self.assertEqual(result["date"].hour, 3)
        self.assertEqual(result["date"].minute, 2)
        self.assertEqual(result["date"].second, 1)

        self.assertEqual(result["analog"][1], 25.3)
        self.assertEqual(result["analog"][2], -5.0)
        self.assertEqual(result["analog"][3], 12)
        self.assertEqual(result["analog"][4], 1)
        self.assertEqual(result["analog"][5], 10.0)
        self.assertEqual(result["analog"][6], 77.0)

        self.assertEqual(result["digital"][2], 1)
        self.assertEqual(result["digital"][4], 1)
        self.assertEqual(result["digital"][1], 0)

        self.assertEqual(result["speed"][1], 1)
        self.assertIsNone(result["speed"][2])
        self.assertEqual(result["speed"][3], 31)
        self.assertIsNone(result["speed"][4])

        self.assertIsNone(result["energy"][1])
        self.assertEqual(result["energy"][2], 2003.0)
        self.assertIsNone(result["power"][1])
        self.assertEqual(result["power"][2], 2.0)

    def test_to_dict_without_timestamp_keeps_date_absent(self):
        parser = BLNETParser(_build_dataset(include_timestamp=False))
        result = parser.to_dict()

        self.assertNotIn("date", result)
        self.assertIn("analog", result)
        self.assertIn("digital", result)
        self.assertIn("speed", result)
