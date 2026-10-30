"""Offline tests for the collector. Both APIs are mocked - no network needed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src import collect, config, db, discover, openaq_client, openmeteo_client

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=config.IST)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Never really sleep in tests (rate limiting / backoff)."""
    monkeypatch.setattr(openaq_client.time, "sleep", lambda s: None)
    monkeypatch.setattr(openmeteo_client.time, "sleep", lambda s: None)


# ------------------------------------------------------------------ fakes
def openaq_hour(ts_ist: datetime, value: float | None) -> dict:
    utc = ts_ist.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"value": value, "period": {"datetimeFrom": {"utc": utc, "local": utc}}}


class FakeOpenAQ:
    """Returns 6 past hours plus 1 future hour for every sensor."""

    def __init__(self, broken_station_ids: tuple[int, ...] = ()):
        self.broken = broken_station_ids

    def get_hours(self, sensor_id, start, end):
        if sensor_id // 10 in self.broken:
            raise RuntimeError("simulated outage")
        hours = [NOW - timedelta(hours=h) for h in range(6, 0, -1)] + [NOW + timedelta(hours=2)]
        return [openaq_hour(ts, 80.0) for ts in hours]


def make_stations(n: int) -> list[dict]:
    return [{"id": i, "name": f"Station {i}", "lat": 28.6, "lon": 77.2,
             "sensors": {"pm25": i * 10 + 1, "pm10": i * 10 + 2},
             "units": {"pm25": "µg/m³", "pm10": "µg/m³"}} for i in range(1, n + 1)]


def fake_openmeteo_rows(past_days: int) -> list[dict]:
    rows = []
    for loc in config.FALLBACK_LOCATIONS:
        for h in range(5, -3, -1):  # 5 past hours ... 2 future hours
            rows.append({"station_id": loc["station_id"], "station": loc["station"],
                         "ts": NOW - timedelta(hours=h), "pm25": 90.0, "pm10": 150.0,
                         "no2": 30.0, "o3": 20.0, "source": "open-meteo"})
    return rows


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "aqi.db"


def sources_in(path) -> set[str]:
    return set(db.load_readings(path)["source"])


# ------------------------------------------------------------ cleaning
def test_clean_rows_drops_future_and_bad_values():
    rows = [
        {"station_id": "1", "station": "A", "ts": NOW - timedelta(hours=1),
         "pm25": -5, "pm10": 99999, "no2": 10, "o3": 5, "source": "openaq"},     # both PM invalid
        {"station_id": "1", "station": "A", "ts": NOW + timedelta(hours=1),
         "pm25": 50, "pm10": 80, "no2": 10, "o3": 5, "source": "openaq"},        # future
        {"station_id": "1", "station": "A", "ts": NOW - timedelta(hours=2),
         "pm25": 50, "pm10": None, "no2": -1, "o3": 5, "source": "openaq"},      # kept
    ]
    cleaned = collect.clean_rows(rows, NOW)
    assert len(cleaned) == 1
    assert cleaned[0]["no2"] is None
    assert cleaned[0]["ts"] == "2026-10-30T10:00:00+05:30"


# --------------------------------------------------------- run() logic
def test_openaq_path_no_fallback_and_no_future_hours(monkeypatch, tmp_db):
    monkeypatch.setenv(config.OPENAQ_KEY_ENV, "test-key")
    monkeypatch.setattr(collect, "OpenAQClient", lambda key: FakeOpenAQ())
    monkeypatch.setattr(collect, "ensure_stations", lambda client: make_stations(4))
    called = []
    monkeypatch.setattr(collect.openmeteo_client, "fetch_all", lambda d: called.append(d) or [])

    fetched = collect.run(hours=48, now=NOW, db_path=tmp_db)

    assert fetched == 4 * 6          # 6 past hours per station, future hour dropped
    assert called == []              # 4 stations >= 3, so no fallback
    df = db.load_readings(tmp_db)
    assert (df["ts"] <= NOW).all()
    assert sources_in(tmp_db) == {"openaq"}


def test_fallback_when_too_few_stations(monkeypatch, tmp_db):
    monkeypatch.setenv(config.OPENAQ_KEY_ENV, "test-key")
    monkeypatch.setattr(collect, "OpenAQClient", lambda key: FakeOpenAQ(broken_station_ids=(2, 3)))
    monkeypatch.setattr(collect, "ensure_stations", lambda client: make_stations(3))
    monkeypatch.setattr(collect.openmeteo_client, "fetch_all", fake_openmeteo_rows)

    collect.run(hours=48, now=NOW, db_path=tmp_db)

    # One station still worked (its rows are kept), the broken ones did not crash the run.
    assert sources_in(tmp_db) == {"openaq", "open-meteo"}


def test_fallback_when_key_missing(monkeypatch, tmp_db):
    monkeypatch.delenv(config.OPENAQ_KEY_ENV, raising=False)
    monkeypatch.setattr(collect.openmeteo_client, "fetch_all", fake_openmeteo_rows)

    fetched = collect.run(hours=48, now=NOW, db_path=tmp_db)

    assert fetched == len(config.FALLBACK_LOCATIONS) * 6   # future hours dropped
    assert sources_in(tmp_db) == {"open-meteo"}


def test_fallback_on_bad_key(monkeypatch, tmp_db):
    class BadKey(FakeOpenAQ):
        def get_hours(self, *args):
            raise openaq_client.OpenAQAuthError("401")

    monkeypatch.setenv(config.OPENAQ_KEY_ENV, "wrong")
    monkeypatch.setattr(collect, "OpenAQClient", lambda key: BadKey())
    monkeypatch.setattr(collect, "ensure_stations", lambda client: make_stations(5))
    monkeypatch.setattr(collect.openmeteo_client, "fetch_all", fake_openmeteo_rows)

    collect.run(hours=48, now=NOW, db_path=tmp_db)
    assert sources_in(tmp_db) == {"open-meteo"}


def test_rerun_creates_no_duplicates(monkeypatch, tmp_db):
    monkeypatch.delenv(config.OPENAQ_KEY_ENV, raising=False)
    monkeypatch.setattr(collect.openmeteo_client, "fetch_all", fake_openmeteo_rows)
    collect.run(hours=48, now=NOW, db_path=tmp_db)
    first = db.count_rows(tmp_db)
    collect.run(hours=48, now=NOW, db_path=tmp_db)
    assert db.count_rows(tmp_db) == first


def test_main_fails_when_no_data(monkeypatch, tmp_db):
    monkeypatch.delenv(config.OPENAQ_KEY_ENV, raising=False)
    monkeypatch.setattr(collect, "_load_env", lambda: None)
    monkeypatch.setattr(collect.openmeteo_client, "fetch_all", lambda d: [])
    monkeypatch.setattr(collect.config, "DB_PATH", tmp_db)
    monkeypatch.setattr(collect, "run", lambda hours: 0)
    assert collect.main() == 1


# ------------------------------------------------------- HTTP clients
class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None, headers: dict | None = None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers: dict = {}
        self.calls = 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return self.responses.pop(0)


def test_openaq_client_retries_after_429():
    ok = FakeResponse(200, {"results": [{"id": 1}]}, {"x-ratelimit-remaining": "50"})
    session = FakeSession([FakeResponse(429, headers={"x-ratelimit-reset": "1"}), ok])
    client = openaq_client.OpenAQClient("key", session=session)
    assert client.find_locations() == [{"id": 1}]
    assert session.calls == 2
    assert session.headers["X-API-Key"] == "key"


def test_openaq_client_bad_key_raises():
    client = openaq_client.OpenAQClient("bad", session=FakeSession([FakeResponse(401)]))
    with pytest.raises(openaq_client.OpenAQAuthError):
        client.find_locations()


def test_openaq_client_gives_up_after_3_retries():
    session = FakeSession([FakeResponse(503)] * 4)
    client = openaq_client.OpenAQClient("key", session=session)
    with pytest.raises(RuntimeError):
        client.find_locations()
    assert session.calls == 4   # first try + 3 retries


def test_parse_hours_converts_ppm_to_ugm3():
    parsed = openaq_client.parse_hours([openaq_hour(NOW, 0.05)], "no2", "ppm")
    assert parsed[NOW] == pytest.approx(0.05 * 1000 * 46.0055 / 24.45)


def test_openmeteo_parse_response():
    data = {"hourly": {"time": ["2026-10-30T10:00", "2026-10-30T11:00"],
                       "pm2_5": [50.0, None], "pm10": [90.0, 95.0],
                       "nitrogen_dioxide": [20.0, 21.0], "ozone": [10.0, 11.0]}}
    rows = openmeteo_client.parse_response(data, "om-ito", "ITO")
    assert rows[0]["ts"] == datetime(2026, 10, 30, 10, 0, tzinfo=config.IST)
    assert rows[1]["pm25"] is None and rows[1]["pm10"] == 95.0
    assert rows[0]["source"] == "open-meteo"


def test_rank_candidates_prefers_monitors_and_distance():
    def loc(i, lat, monitor):
        return {"id": i, "name": f"L{i}", "isMobile": False, "isMonitor": monitor,
                "coordinates": {"latitude": lat, "longitude": 77.2090},
                "sensors": [{"id": i * 10, "parameter": {"name": "pm25", "units": "µg/m³"}}]}
    ranked = discover.rank_candidates([loc(1, 28.70, True), loc(2, 28.62, True), loc(3, 28.6139, False)])
    assert [s["id"] for s in ranked] == [2, 1]   # low-cost sensor dropped, closest first
