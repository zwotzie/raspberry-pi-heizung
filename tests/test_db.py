import datetime

import pytest

import heizung.db as db


class FakeCursor:
    def __init__(self, fetchall=None, fetchone=None):
        self._fetchall = fetchall if fetchall is not None else []
        self._fetchone = fetchone
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._fetchall

    def fetchone(self):
        return self._fetchone


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return self._cursor


@pytest.fixture
def patch_connect(monkeypatch):
    """Patch db._connect to return a FakeConn wrapping the given cursor."""

    def _apply(cursor):
        monkeypatch.setattr(db, "_connect", lambda url: FakeConn(cursor))
        return cursor

    return _apply


def test_init_db_executes_ddl(patch_connect):
    cur = patch_connect(FakeCursor())
    db.init_db("postgresql://test")
    assert cur.executed
    assert cur.executed[0][0] == db.DDL


def test_insert_happy_path_builds_row(patch_connect):
    cur = patch_connect(FakeCursor())
    ts = datetime.datetime(2026, 3, 26, 12, 0, 0)
    db.insert("postgresql://test", {"timestamp": ts, "aussentemperatur": 5.2, "heizung_an": 1})

    assert len(cur.executed) == 1
    sql, params = cur.executed[0]
    assert "INSERT INTO measurements" in sql
    assert params["aussentemperatur"] == 5.2
    assert params["heizung_an"] == 1
    # missing digital columns default to 0
    assert params["d_heizung_pumpe"] == 0
    # timezone added
    assert params["measured_at"].tzinfo is not None


def test_insert_skips_when_timestamp_missing(patch_connect):
    cur = patch_connect(FakeCursor())
    db.insert("postgresql://test", {"aussentemperatur": 1.0})
    assert cur.executed == []


def test_insert_parses_iso_string_timestamp(patch_connect):
    cur = patch_connect(FakeCursor())
    db.insert("postgresql://test", {"timestamp": "2026-03-26T12:00:00"})
    _, params = cur.executed[0]
    assert isinstance(params["measured_at"], datetime.datetime)


def test_insert_logs_on_db_error(monkeypatch, caplog):
    def boom(_url):
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "_connect", boom)
    ts = datetime.datetime(2026, 3, 26, 12, 0, 0, tzinfo=datetime.UTC)
    with caplog.at_level("ERROR"):
        db.insert("postgresql://test", {"timestamp": ts})
    assert any("db.insert failed" in r.message for r in caplog.records)


def test_query_converts_datetime_to_unix(patch_connect):
    ts = datetime.datetime(2026, 3, 26, 12, 0, 0, tzinfo=datetime.UTC)
    row = (ts, *([1.0] * len(db.DATA_COLUMNS)))
    patch_connect(FakeCursor(fetchall=[row]))

    result = db.query("postgresql://test", date="2026-03-26", period="day")
    assert result[0][0] == int(ts.timestamp())
    assert result[0][1] == 1.0


def test_query_week_period(patch_connect):
    cur = patch_connect(FakeCursor(fetchall=[]))
    db.query("postgresql://test", date="2026-03-26", period="week")
    _, params = cur.executed[0]
    assert (params["end"] - params["start"]).days == 7


def test_get_setting_returns_value(patch_connect):
    patch_connect(FakeCursor(fetchone=("firewood",)))
    assert db.get_setting("postgresql://test", "operating_mode") == "firewood"


def test_get_setting_returns_default_when_missing(patch_connect):
    patch_connect(FakeCursor(fetchone=None))
    assert db.get_setting("postgresql://test", "operating_mode", "pellets") == "pellets"


def test_upsert_setting_executes(patch_connect):
    cur = patch_connect(FakeCursor())
    db.upsert_setting("postgresql://test", "operating_mode", "firewood")
    sql, params = cur.executed[0]
    assert "INSERT INTO settings" in sql
    assert params == ("operating_mode", "firewood")

