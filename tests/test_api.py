import sys

import pytest
from fastapi.testclient import TestClient

import heizung.config as config


@pytest.fixture
def api_module(monkeypatch):
    """Import heizung.api with load_config patched so no DNS/DB is touched."""
    cfg = {
        "db_url": "postgresql://test",
        "logger": "False",
        "operating_mode": "pellets",
    }
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    # force a fresh import so module-level load_config() runs with the patch
    sys.modules.pop("heizung.api", None)
    import heizung.api as api

    # never hit a real database
    monkeypatch.setattr(api.db, "init_db", lambda *a, **k: None)
    yield api
    sys.modules.pop("heizung.api", None)


@pytest.fixture
def client(api_module):
    return TestClient(api_module.app)


def test_create_measurement(api_module, client, monkeypatch):
    captured = {}
    monkeypatch.setattr(api_module.db, "insert", lambda url, data: captured.update(data))

    resp = client.post("/measurements", json={"timestamp": "2026-03-26T12:00:00"})
    assert resp.status_code == 201
    assert resp.json() == {"status": "ok"}
    assert "timestamp" in captured


def test_get_operating_mode(api_module, client, monkeypatch):
    monkeypatch.setattr(api_module.db, "get_setting", lambda url, key, default=None: "firewood")
    resp = client.get("/settings/operating-mode")
    assert resp.status_code == 200
    assert resp.json() == {"operating_mode": "firewood"}


def test_set_operating_mode(api_module, client, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        api_module.db, "upsert_setting", lambda url, key, value: saved.update({key: value})
    )
    resp = client.put("/settings/operating-mode", params={"mode": "firewood"})
    assert resp.status_code == 200
    assert resp.json() == {"operating_mode": "firewood"}
    assert saved == {"operating_mode": "firewood"}


def test_analog_chart_returns_rows(api_module, client, monkeypatch):
    monkeypatch.setattr(api_module.db, "query", lambda url, date, period: [[123, 1.0]])
    resp = client.get("/analogChart.php", params={"date": "2026-03-26"})
    assert resp.status_code == 200
    assert resp.json() == [[123, 1.0]]


def test_analog_chart_rejects_bad_period(api_module, client):
    resp = client.get("/analogChart.php", params={"date": "2026-03-26", "period": "month"})
    assert resp.status_code == 400


def test_db_url_raises_when_missing(monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda *a, **k: {"db_url": None})
    sys.modules.pop("heizung.api", None)
    import heizung.api as api

    with pytest.raises(RuntimeError):
        api._db_url()
    sys.modules.pop("heizung.api", None)

