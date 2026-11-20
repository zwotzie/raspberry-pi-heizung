"""Tests for the in-memory push buffer (delayed delivery to VictoriaMetrics)."""

import logging
import threading
from unittest.mock import Mock, patch

import pytest
import requests

from heizung import weather
from heizung.pushbuffer import DEFAULT_MAX_PAYLOADS, PushBuffer, parse_push_buffer_max


def _ok(status=204):
    return Mock(status_code=status, text="")


def test_successful_submit_posts_immediately():
    buf = PushBuffer("http://vm.lan:8428/")
    with patch("heizung.pushbuffer.requests.post", return_value=_ok()) as post:
        buf.submit("a 1 1000\n")

    post.assert_called_once()
    assert post.call_args.args[0] == "http://vm.lan:8428/api/v1/import/prometheus"
    assert post.call_args.kwargs["data"] == b"a 1 1000\n"
    assert len(buf) == 0


def test_connection_error_buffers_and_later_delivers_in_order(caplog):
    buf = PushBuffer("http://vm")
    with (
        caplog.at_level(logging.INFO, logger="heizung"),
        patch(
            "heizung.pushbuffer.requests.post",
            side_effect=requests.ConnectionError("Failed to resolve 'vm'"),
        ),
    ):
        buf.submit("a 1 1000\n")
        buf.submit("a 2 2000\n")
    assert len(buf) == 2
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1  # only the transition into failure is logged
    assert not any(r.exc_info for r in caplog.records)

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post", return_value=_ok()
    ) as post:
        buf.submit("a 3 3000\n")

    post.assert_called_once()
    assert post.call_args.kwargs["data"] == b"a 1 1000\na 2 2000\na 3 3000\n"
    assert len(buf) == 0
    # the freshly submitted payload is not "redelivered"
    assert any(
        "recovered" in r.getMessage() and "delivered 2 buffered" in r.getMessage()
        for r in caplog.records
    )


def test_server_error_keeps_payload():
    buf = PushBuffer("http://vm")
    with patch("heizung.pushbuffer.requests.post", return_value=Mock(status_code=503, text="busy")):
        buf.submit("a 1 1000\n")
    assert len(buf) == 1


def test_client_error_drops_batch():
    buf = PushBuffer("http://vm")
    with patch("heizung.pushbuffer.requests.post", return_value=Mock(status_code=400, text="bad")):
        buf.submit("broken\n")
    assert len(buf) == 0


def test_backlog_is_sent_in_batches():
    buf = PushBuffer("http://vm", batch_size=2)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        for i in range(4):
            buf.submit(f"a {i} {i}\n")
    with patch("heizung.pushbuffer.requests.post", return_value=_ok()) as post:
        buf.submit("a 4 4\n")

    assert [c.kwargs["data"] for c in post.call_args_list] == [
        b"a 0 0\na 1 1\n",
        b"a 2 2\na 3 3\n",
        b"a 4 4\n",
    ]
    assert len(buf) == 0


def test_partial_recovery_keeps_rest():
    buf = PushBuffer("http://vm", batch_size=1)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        buf.submit("a 0 0\n")
        buf.submit("a 1 1\n")
    with patch(
        "heizung.pushbuffer.requests.post",
        side_effect=[_ok(), requests.Timeout()],
    ):
        buf.submit("a 2 2\n")
    assert list(buf._queue) == ["a 1 1\n", "a 2 2\n"]


def test_overflow_drops_oldest():
    buf = PushBuffer("http://vm", max_payloads=3)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        for i in range(5):
            buf.submit(f"a {i} {i}\n")
    assert list(buf._queue) == ["a 2 2\n", "a 3 3\n", "a 4 4\n"]


def test_empty_payload_is_ignored():
    buf = PushBuffer("http://vm")
    with patch("heizung.pushbuffer.requests.post") as post:
        buf.submit("")
    post.assert_not_called()
    assert len(buf) == 0


def test_unexpected_error_never_raises():
    buf = PushBuffer("http://vm")
    with patch("heizung.pushbuffer.requests.post", side_effect=ValueError("boom")):
        buf.submit("a 1 1\n")
    assert len(buf) == 1


def test_weather_loop_submits_to_buffer():
    stop = Mock()
    stop.is_set.side_effect = [False, True]
    config = {
        "push_url": "http://vm:8428",
        "open_meteo_latitude": 1.0,
        "open_meteo_longitude": 2.0,
        "open_meteo_job": "weather",
        "open_meteo_instance": "om",
    }
    buf = Mock()
    with (
        patch.object(weather, "fetch_forecast", return_value={}),
        patch.object(weather, "push_forecast") as push,
    ):
        weather._weather_loop(config, stop, buf)

    push.assert_not_called()
    buf.submit.assert_called_once()
    payload = buf.submit.call_args.args[0]
    assert 'weather_up{job="weather",instance="om"} 1' in payload


def test_rate_limited_payload_is_retried(caplog):
    """A 429 means "slow down", not "discard" — the payload must survive."""
    buf = PushBuffer("http://vm")
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post",
        return_value=Mock(status_code=429, text="slow down"),
    ):
        buf.submit("a 1 1000\n")

    assert len(buf) == 1
    assert [r for r in caplog.records if r.levelno == logging.ERROR] == []


def test_request_timeout_is_retried():
    buf = PushBuffer("http://vm")
    with patch("heizung.pushbuffer.requests.post", return_value=Mock(status_code=408, text="")):
        buf.submit("a 1 1000\n")

    assert len(buf) == 1


def test_overflow_drops_are_reported_on_recovery(caplog):
    buf = PushBuffer("http://vm", max_payloads=2)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        for i in range(4):
            buf.submit(f"a {i} {i}\n")

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post", return_value=_ok()
    ):
        buf.submit("a 4 4\n")

    assert len(buf) == 0
    assert any(
        "recovered" in r.getMessage() and "3 dropped" in r.getMessage()
        for r in caplog.records
    )


def test_rejection_drain_does_not_claim_recovery(caplog):
    """If everything was rejected, the target did not recover."""
    buf = PushBuffer("http://vm", batch_size=1)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        buf.submit("a 0 0\n")

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post",
        return_value=Mock(status_code=400, text="bad"),
    ):
        buf.submit("a 1 1\n")

    assert len(buf) == 0
    messages = [r.getMessage() for r in caplog.records]
    assert not any("recovered" in m for m in messages)
    assert any("still rejecting" in m and "2" in m for m in messages)


def test_client_error_is_logged_once(caplog):
    """A permanent 4xx must be visible once, not every poll cycle."""
    buf = PushBuffer("http://vm")
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post",
        return_value=Mock(status_code=404, text="not found"),
    ):
        buf.submit("a 1 1\n")
        buf.submit("a 2 2\n")

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert "404" in errors[0].getMessage()


def test_flush_is_capped_per_submit():
    """One submit must not occupy the poll thread for the whole backlog."""
    buf = PushBuffer("http://vm", batch_size=1, max_batches_per_flush=2)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        for i in range(3):
            buf.submit(f"a {i} {i}\n")

    with patch("heizung.pushbuffer.requests.post", return_value=_ok()) as post:
        buf.submit("a 3 3\n")

    assert post.call_count == 2
    assert list(buf._queue) == ["a 2 2\n", "a 3 3\n"]


def test_len_does_not_block_while_post_is_in_flight():
    """The lock must not be held during HTTP, or the poll loop stalls."""
    buf = PushBuffer("http://vm")
    started = threading.Event()
    release = threading.Event()

    def slow_post(*args, **kwargs):
        started.set()
        release.wait(timeout=5)
        return _ok()

    worker = threading.Thread(target=buf.submit, args=("a 1 1\n",))
    try:
        with patch("heizung.pushbuffer.requests.post", side_effect=slow_post):
            worker.start()
            assert started.wait(timeout=5)

            reader = threading.Thread(target=len, args=(buf,))
            reader.start()
            reader.join(timeout=1)
            assert not reader.is_alive(), "len() blocked while a POST was in flight"
    finally:
        release.set()
        worker.join(timeout=5)

    assert len(buf) == 0


def test_discard_refuses_when_head_changed_by_overflow():
    """Only delete what we actually posted: overflow may have moved the head."""
    buf = PushBuffer("http://vm", batch_size=2, max_payloads=4)
    buf._queue.extend(["A\n", "B\n", "C\n", "D\n"])
    batch = buf._next_batch()
    buf._queue.append("E\n")  # overflows: drops A
    buf._queue.append("F\n")  # overflows: drops B

    assert buf._discard(batch) is False
    assert list(buf._queue) == ["C\n", "D\n", "E\n", "F\n"]


def test_second_submitter_does_not_delete_payloads_it_did_not_post():
    """A concurrent flush must never remove a queue head that changed."""
    buf = PushBuffer("http://vm", batch_size=1)
    started = threading.Event()
    release = threading.Event()
    posted = []
    first = True

    def blocked_post(*args, **kwargs):
        nonlocal first
        posted.append(kwargs["data"])
        if first:
            first = False
            started.set()
            release.wait(timeout=5)
        return _ok()

    with patch("heizung.pushbuffer.requests.post", side_effect=blocked_post):
        worker = threading.Thread(target=buf.submit, args=("a 1 1\n",))
        worker.start()
        assert started.wait(timeout=5)
        # the head is taken by the in-flight flush; a second submit runs a
        # flush of its own and must not make the first one delete its payload
        buf.submit("a 2 2\n")
        release.set()
        worker.join(timeout=5)

    assert len(buf) == 0
    assert b"a 1 1\n" in b"".join(posted)
    assert b"a 2 2\n" in b"".join(posted)


def test_rejections_before_an_outage_are_not_counted_as_dropped(caplog):
    """Steady-state rejections must not leak into the next recovery line."""
    buf = PushBuffer("http://vm", batch_size=1)
    with patch(
        "heizung.pushbuffer.requests.post",
        return_value=Mock(status_code=400, text="bad"),
    ):
        buf.submit("a 0 0\n")  # rejected while healthy

    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        buf.submit("a 1 1\n")  # outage starts

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post", return_value=_ok()
    ):
        buf.submit("a 2 2\n")

    recovered = [r.getMessage() for r in caplog.records if "recovered" in r.getMessage()]
    assert len(recovered) == 1
    assert "dropped" not in recovered[0]


def test_mixed_flush_delivers_and_reports_recovery(caplog):
    """Delivered backlog + rejected fresh payload must not claim "still rejecting"."""
    buf = PushBuffer("http://vm", batch_size=1)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        buf.submit("a 0 0\n")

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post",
        side_effect=[_ok(), Mock(status_code=400, text="bad")],
    ):
        buf.submit("a 1 1\n")

    messages = [r.getMessage() for r in caplog.records]
    assert not any("still rejecting" in m for m in messages)
    assert any("recovered" in m and "delivered 1 buffered" in m for m in messages)


def test_counters_reset_between_outages(caplog):
    """A second outage must not inherit counts from the first one."""
    buf = PushBuffer("http://vm", batch_size=1)
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        buf.submit("a 0 0\n")
    with patch(
        "heizung.pushbuffer.requests.post",
        return_value=Mock(status_code=400, text="bad"),
    ):
        buf.submit("a 1 1\n")  # episode 1 ends after two rejections

    caplog.clear()
    with patch("heizung.pushbuffer.requests.post", side_effect=requests.ConnectionError()):
        buf.submit("a 2 2\n")  # episode 2 outage
    with caplog.at_level(logging.INFO, logger="heizung"), patch(
        "heizung.pushbuffer.requests.post", return_value=_ok()
    ):
        buf.submit("a 3 3\n")

    recovered = [r.getMessage() for r in caplog.records if "recovered" in r.getMessage()]
    assert len(recovered) == 1
    assert "delivered 1 buffered" in recovered[0]
    assert "dropped" not in recovered[0]


def test_parse_push_buffer_max_accepts_integral_values():
    assert parse_push_buffer_max(5) == 5
    assert parse_push_buffer_max("5") == 5
    assert parse_push_buffer_max(1440.0) == 1440
    assert parse_push_buffer_max(None) == DEFAULT_MAX_PAYLOADS
    for bad in (-1, "abc", 1.5, True):
        with pytest.raises(ValueError, match="push_buffer_max"):
            parse_push_buffer_max(bad)

