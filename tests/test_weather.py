"""Tests for Open-Meteo fetching, parsing and delivery to VictoriaMetrics."""

from unittest.mock import Mock, patch

import pytest

from heizung import weather

SAMPLE_PAYLOAD = {
    "current": {
        "time": 1_700_000_000,
        "temperature_2m": 7.5,
        "apparent_temperature": 6.0,
        "precipitation": 0.2,
        "cloud_cover": 35,
        "shortwave_radiation": 120.0,
    },
    "hourly": {
        "time": [1_700_000_000, 1_700_003_600],
        "temperature_2m": [7.0, 8.0],
        "apparent_temperature": [6.0, 7.0],
        "precipitation": [0.1, 0.0],
        "cloud_cover": [30, 20],
        "shortwave_radiation": [110.0, 150.0],
    },
    "daily": {
        "time": [1_699_996_800],
        "sunshine_duration": [14400],
        "temperature_2m_max": [10.0],
        "temperature_2m_min": [4.0],
    },
}


def test_build_samples_includes_current_hourly_daily():
    samples = weather.build_forecast_samples(SAMPLE_PAYLOAD)

    names = {name for name, _, _ in samples}
    assert "current_temperature_2m" in names
    assert "sunshine_duration" in names
    assert "temperature_2m_max" in names


def test_build_samples_uses_current_value_when_available():
    samples = weather.build_forecast_samples(SAMPLE_PAYLOAD)

    current = [
        value for name, ts, value in samples
        if name == "current_temperature_2m" and ts == 1_700_000_000_000
    ]
    # Current conditions overwrite the hourly point for the same timestamp.
    assert current == [7.5]


def test_build_samples_converts_unix_seconds_to_milliseconds():
    samples = weather.build_forecast_samples(SAMPLE_PAYLOAD)

    assert any(ts == 1_700_000_000_000 for _, ts, _ in samples)


def test_render_push_payload_mixes_timestamps():
    samples = [("current_temperature_2m", 1_700_000_000_000, 7.5)]
    payload = weather.render_weather_push_payload(samples, job="open-meteo", instance="i1")

    assert 'current_temperature_2m{job="open-meteo",instance="i1"} 7.5 1700000000000' in payload.splitlines()


def test_push_posts_to_import_api():
    samples = [("open_meteo_temperature_2m", 1_700_000_000_000, 7.5)]
    resp = Mock(status_code=204, text="")
    with patch.object(weather.requests, "post", return_value=resp) as post:
        weather.push_forecast("http://vm.lan:8428/", samples, job="open-meteo", instance="i1")

    args, kwargs = post.call_args
    assert args[0] == "http://vm.lan:8428/api/v1/import/prometheus"
    assert b"1700000000000" in kwargs["data"]


def test_push_raises_on_error_status():
    samples = [("open_meteo_temperature_2m", 1_700_000_000_000, 7.5)]
    resp = Mock(status_code=500, text="boom")
    with (
        patch.object(weather.requests, "post", return_value=resp),
        pytest.raises(RuntimeError, match="HTTP 500"),
    ):
        weather.push_forecast("http://vm.lan:8428", samples)


def test_build_samples_ignores_missing_arrays():
    assert weather.build_forecast_samples({"error": True}) == []


# aliases for convenience
weather.build_samples = weather.build_forecast_samples
weather.forecast_to_samples = weather.build_forecast_samples
weather.parse_forecast = weather.build_forecast_samples
weather.push_weather = weather.push_forecast
weather.fetch_weather = weather.fetch_forecast
weather.push = weather.push_forecast


def test_fetch_forecast_builds_request():
    response = Mock()
    response.json.return_value = SAMPLE_PAYLOAD
    response.raise_for_status.return_value = None

    config = {
        "open_meteo_latitude": 52.5,
        "open_meteo_longitude": 13.4,
        "open_meteo_timezone": "Europe/Berlin",
        "open_meteo_forecast_days": 2,
        "open_meteo_hourly": "temperature_2m",
        "open_meteo_daily": "sunshine_duration",
    }

    with patch.object(weather.requests, "get", return_value=response) as get:
        payload = weather.fetch_forecast(config, timeout=7)

    assert payload == SAMPLE_PAYLOAD
    params = get.call_args.kwargs["params"]
    assert params["latitude"] == 52.5
    assert params["longitude"] == 13.4
    assert params["timeformat"] == "unixtime"
    assert get.call_args.kwargs["timeout"] == 7


def test_weather_loop_passes_errors_through(caplog):
    stop = Mock()
    stop.is_set.side_effect = [False, True]
    stop.wait = Mock()

    config = {
        "push_url": "http://vm:8428",
        "open_meteo_latitude": 1.0,
        "open_meteo_longitude": 2.0,
        "open_meteo_job": "open-meteo",
        "open_meteo_instance": "job1",
        "open_meteo_poll_seconds": 60,
    }

    with (
        patch.object(weather, "fetch_forecast", side_effect=RuntimeError("boom")),
        patch.object(weather, "push_forecast") as push,
    ):
        weather._weather_loop(config, stop)

    push.assert_not_called()
    assert True
