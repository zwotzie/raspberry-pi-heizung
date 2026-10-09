"""Tests for the shared metric selection and the push mode payload/HTTP push."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from heizung import metrics


@pytest.fixture(autouse=True)
def _fresh_state():
    metrics._state.reset()
    yield
    metrics._state.reset()


def _families():
    return metrics._families()


def test_fresh_snapshot_exposes_sensors_and_health():
    metrics.set_measurement({"aussentemperatur": 5.2, "d_heizung_pumpe": 1}, heizung_an=1, duration=0.42)
    metrics.set_operating_mode("pellets")

    fams = {name: value for name, value, _ in _families()}
    assert fams["heizung_up"] == 1.0
    assert fams["aussentemperatur"] == 5.2
    assert fams["heizung_an"] == 1.0
    assert fams["d_heizung_pumpe"] == 1.0
    assert fams["heizung_poll_errors"] == 0.0
    assert "kessel_rl" not in fams

    assert fams["heizung_data_age_seconds"] >= 0.0
    assert "heizung_last_measurement_timestamp_seconds" in fams
    assert fams["heizung_poll_duration_seconds"] == 0.42


def test_stale_snapshot_omits_sensor_values():
    metrics.set_measurement({"aussentemperatur": 5.2})
    with patch("heizung.metrics.time.time", return_value=metrics._state.fetched_at + 1000):
        fams = {name: value for name, value, _ in _families()}

    assert fams["heizung_up"] == 0.0
    assert "aussentemperatur" not in fams
    assert fams["heizung_data_age_seconds"] > 900


def test_poll_failures_are_counted():
    metrics.record_poll_failure()
    metrics.record_poll_failure()
    fams = {name: value for name, value, _ in _families()}
    assert fams["heizung_poll_errors"] == 2.0


def test_operating_mode_labels_active_and_inactive():
    metrics.set_measurement({"aussentemperatur": 1.0})
    metrics.set_operating_mode("pellets")

    modes = {(labels.get("mode"), value) for name, value, labels in _families() if name == "heizung_operating_mode"}
    assert modes == {("pellets", 1.0), ("firewood", 0.0)}


def test_operating_mode_unset_is_all_inactive():
    metrics.set_measurement({"aussentemperatur": 1.0})
    modes = {(labels.get("mode"), value) for name, value, labels in _families() if name == "heizung_operating_mode"}
    assert modes == {("pellets", 0.0), ("firewood", 0.0)}


def test_render_push_payload_labels_and_format():
    metrics.set_measurement({"aussentemperatur": 5.25}, heizung_an=1)
    metrics.set_operating_mode("pellets")
    metrics.record_poll_failure()

    payload = metrics.render_push_payload(timestamp_ms=1700000000000)
    lines = payload.splitlines()

    assert payload.endswith("\n")
    assert all(line.endswith(" 1700000000000") for line in lines)

    def find(name: str) -> str:
        matches = [line for line in lines if line.startswith(name + "{") or line.startswith(name + " ")]
        assert matches, name
        return matches[0]

    assert find("heizung_up") == 'heizung_up{job="heizung",instance="heizung"} 1 1700000000000'
    assert find("aussentemperatur") == 'aussentemperatur{job="heizung",instance="heizung"} 5.25 1700000000000'
    assert find("heizung_poll_errors_total") == (
        'heizung_poll_errors_total{job="heizung",instance="heizung"} 1 1700000000000'
    )
    assert (
        'heizung_operating_mode{job="heizung",instance="heizung",mode="pellets"} 1 1700000000000' in lines
    )
    assert (
        'heizung_operating_mode{job="heizung",instance="heizung",mode="firewood"} 0 1700000000000' in lines
    )


def test_render_push_payload_respects_custom_labels_and_timestamp():
    metrics.record_poll_failure()
    payload = metrics.render_push_payload(job="h1", instance="i1", timestamp_ms=123)
    assert 'heizung_poll_errors_total{job="h1",instance="i1"} 1 123' in payload.splitlines()


def test_push_posts_to_import_api():
    metrics.record_poll_failure()
    now_ms = int(datetime.now().timestamp() * 1000)
    resp = Mock(status_code=200, text="")
    with patch.object(metrics.requests, "post", return_value=resp) as post:
        metrics.push("http://vm.lan:8428/", job="heizung", instance="heizung")

    args, kwargs = post.call_args
    assert args[0] == "http://vm.lan:8428/api/v1/import/prometheus"
    data = kwargs["data"]
    assert b'heizung_poll_errors_total{job="heizung",instance="heizung"} 1 ' in data
    # timestamp must be current (few seconds skew allowed)
    ts = int(data.decode().splitlines()[0].rsplit(" ", 1)[1])
    assert abs(ts - now_ms) < 5000


def test_push_raises_on_error_status():
    resp = Mock(status_code=500, text="boom")
    with (
        patch.object(metrics.requests, "post", return_value=resp),
        pytest.raises(RuntimeError, match="HTTP 500"),
    ):
        metrics.push("http://vm.lan:8428")


def test_push_accepts_204():
    resp = Mock(status_code=204, text="")
    with patch.object(metrics.requests, "post", return_value=resp):
        metrics.push("http://vm.lan:8428")
    # no exception
