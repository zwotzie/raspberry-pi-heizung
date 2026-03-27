import unittest
from unittest.mock import Mock, patch

from heizung.ta.blnet_conn import WAIT_TIME, BLNETDirect


def _packet(*payload):
    checksum = sum(payload) % 256
    return bytes(payload + (checksum,))


class TestBLNETDirect(unittest.TestCase):
    def test_checksum_validates_payload_and_rejects_invalid_checksum(self):
        with patch.object(BLNETDirect, "_check_mode", return_value=True):
            conn = BLNETDirect("127.0.0.1")

        self.assertTrue(conn._checksum(_packet(1, 2, 3)))
        self.assertFalse(conn._checksum(bytes([1, 2, 3, 0])))

    def test_query_returns_short_response_without_waiting_for_full_length(self):
        with patch.object(BLNETDirect, "_check_mode", return_value=True):
            conn = BLNETDirect("127.0.0.1")

        conn._socket = Mock()
        conn._socket.send.return_value = 1
        conn._socket.recv.return_value = b"abc"

        result = conn._query(b"\x01", 50)

        self.assertEqual(result, b"abc")

    def test_query_raises_connection_error_when_command_is_not_fully_sent(self):
        with patch.object(BLNETDirect, "_check_mode", return_value=True):
            conn = BLNETDirect("127.0.0.1")

        conn._socket = Mock()
        conn._socket.send.return_value = 0

        with (
            patch.object(conn, "_disconnect") as disconnect_mock,
            self.assertRaises(ConnectionError),
        ):
            conn._query(b"\x01", 1)

        disconnect_mock.assert_called_once()

    def test_get_latest_returns_parsed_frame_after_wait_reply(self):
        with patch.object(BLNETDirect, "_check_mode", return_value=True):
            conn = BLNETDirect("127.0.0.1")

        conn._can_frames = 1
        conn._actual_size = 10
        wait_reply = _packet(WAIT_TIME, 2)
        data_reply = _packet(1, 10, 11)

        with (
            patch.object(conn, "_connect"),
            patch.object(conn, "_disconnect"),
            patch.object(conn, "_end_read") as end_read_mock,
            patch.object(conn, "get_count", return_value=1),
            patch.object(conn, "_query", side_effect=[wait_reply, data_reply]),
            patch.object(conn, "_split_latest", return_value={0: {"temp": 42}}) as split_mock,
            patch("heizung.ta.blnet_conn.sleep") as sleep_mock,
        ):
            result = conn.get_latest(max_retries=3)

        self.assertEqual(result[0], {"temp": 42})
        self.assertEqual(result["info"]["sleep"][0], [2])
        self.assertEqual(result["info"]["got"][0], 1)
        sleep_mock.assert_called_once_with(2)
        split_mock.assert_called_once_with(data_reply, 0)
        end_read_mock.assert_called_once_with(True)

    def test_get_latest_marks_frame_timeout_after_all_retries_are_wait_replies(self):
        with patch.object(BLNETDirect, "_check_mode", return_value=True):
            conn = BLNETDirect("127.0.0.1")

        conn._can_frames = 1
        conn._actual_size = 10
        wait_reply = _packet(WAIT_TIME, 1)

        with (
            patch.object(conn, "_connect"),
            patch.object(conn, "_disconnect"),
            patch.object(conn, "_end_read") as end_read_mock,
            patch.object(conn, "get_count", return_value=1),
            patch.object(conn, "_query", side_effect=[wait_reply, wait_reply, wait_reply]),
            patch.object(conn, "_split_latest") as split_mock,
            patch("heizung.ta.blnet_conn.sleep") as sleep_mock,
        ):
            result = conn.get_latest(max_retries=3)

        self.assertEqual(result[0], "timeout")
        self.assertEqual(result["info"]["sleep"][0], [1, 1, 1])
        self.assertNotIn(0, result["info"]["got"])
        self.assertEqual(sleep_mock.call_count, 3)
        split_mock.assert_not_called()
        end_read_mock.assert_called_once_with(True)

    def test_get_latest_raises_when_no_frames_are_available(self):
        with patch.object(BLNETDirect, "_check_mode", return_value=True):
            conn = BLNETDirect("127.0.0.1")

        conn._can_frames = 0
        conn._actual_size = 10

        with (
            patch.object(conn, "_connect"),
            patch.object(conn, "_end_read") as end_read_mock,
            patch.object(conn, "get_count", return_value=0),
            self.assertRaises(ConnectionError),
        ):
            conn.get_latest()

        end_read_mock.assert_called_once_with(True)
