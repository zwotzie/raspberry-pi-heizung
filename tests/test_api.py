from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

import heizung.config

load_config = heizung.config.load_config
with patch.object(heizung.config, "load_config", return_value={}):
    from heizung import api

api.load_config = load_config


@pytest.mark.parametrize(
    ("period", "expected_start", "expected_end"),
    [
        ("day", 0, 1),
        ("week", -6, 1),
    ],
)
def test_chart_queries_range_ending_on_selected_date(period, expected_start, expected_end):
    selected_date = datetime.fromisoformat("2026-03-26").astimezone()
    response = Mock()
    response.json.return_value = {"status": "success", "data": {"result": []}}

    with (
        patch.object(api, "_prometheus_url", return_value="http://prometheus"),
        patch.object(api.requests, "get", return_value=response) as get,
    ):
        assert api.chart("2026-03-26", period) == []

    params = get.call_args.kwargs["params"]
    assert params["start"] == (selected_date + timedelta(days=expected_start)).timestamp()
    assert params["end"] == (selected_date + timedelta(days=expected_end)).timestamp()


def test_chart_queries_trailing_24_hours_for_today():
    now = datetime(2026, 10, 5, 8, 0).astimezone()

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz is None else now.astimezone(tz)

    response = Mock()
    response.json.return_value = {"status": "success", "data": {"result": []}}

    with (
        patch.object(api, "datetime", FrozenDateTime),
        patch.object(api, "_prometheus_url", return_value="http://prometheus"),
        patch.object(api.requests, "get", return_value=response) as get,
    ):
        assert api.chart(now.date().isoformat(), "day") == []

    params = get.call_args.kwargs["params"]
    assert params["start"] == (now - timedelta(hours=24)).timestamp()
    assert params["end"] == now.timestamp()
