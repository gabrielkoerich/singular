import json
from pathlib import Path

import pandas as pd
import pytest
import requests
from fastapi.testclient import TestClient

from singular import server
from singular.chart import plot
from singular.export import COLUMNS, export, to_table
from singular.fetch import GEOCODE_URL, Weather, fetch, load_cities
from singular.process import process

ROWS = [
    Weather(city="Oslo", latitude=59.9, longitude=10.7, time="2026-10-22T12:00",
            temperature_c=0.0, humidity_pct=80, wind_speed_ms=10.0),
    Weather(city="Lima", latitude=-12.0, longitude=-77.0, time="2026-10-22T12:00",
            temperature_c=100.0, humidity_pct=40, wind_speed_ms=1.0),
]


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload: object = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> object:
        return self.payload


def test_load_cities() -> None:
    cities = load_cities("cities.json")
    assert len(cities) == 10
    assert cities["Rio de Janeiro"] == (-22.9068, -43.1729)


def test_fetch_geocodes_unknown_city(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, params: dict[str, object], **_: object) -> FakeResponse:
        if url == GEOCODE_URL:
            return FakeResponse({"results": [{"latitude": 1.5, "longitude": 2.5}]})

        assert params["latitude"] == "1.5"
        # a single location comes back as a bare object, not a list
        return FakeResponse({"current": {"time": "t", "temperature_2m": 20.0,
                                         "relative_humidity_2m": 50, "wind_speed_10m": 3.0}})

    monkeypatch.setattr(requests, "get", fake_get)
    [row] = fetch(["Nowhere"], {})
    assert row == Weather(city="Nowhere", latitude=1.5, longitude=2.5, time="t",
                          temperature_c=20.0, humidity_pct=50, wind_speed_ms=3.0)


def test_process_converts_and_ranks() -> None:
    df = process(pd.DataFrame(ROWS), "temperature_c", False, 0)
    assert df["city"].tolist() == ["Lima", "Oslo"]
    assert df["rank"].tolist() == [1, 2]
    assert df["temperature_f"].tolist() == [212.0, 32.0]
    assert df["wind_speed_mph"].tolist() == [2.2, 22.4]


def test_process_ascending_top() -> None:
    df = process(pd.DataFrame(ROWS), "humidity_pct", True, 1)
    assert df["city"].tolist() == ["Lima"]


def test_export_writes_example_columns(tmp_path: Path) -> None:
    out = export(process(pd.DataFrame(ROWS), "temperature_c", False, 0), str(tmp_path / "w.csv"))
    assert pd.read_csv(out).columns.tolist() == list(COLUMNS.values())


def test_plot_has_one_axis_per_metric() -> None:
    df = to_table(process(pd.DataFrame(ROWS), "temperature_c", False, 0))
    assert len(plot(df).axes) == 3


def test_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[int] = []

    def fake_fetch(*_: object) -> list[Weather]:
        calls.append(1)
        return ROWS

    (tmp_path / "cities.json").write_text(json.dumps([{"City": "Oslo", "Latitude": 0, "Longitude": 0}]))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server, "fetch", fake_fetch)
    server._current.cache_clear()  # pyright: ignore[reportPrivateUsage]
    client = TestClient(server.app)

    page = client.get("/")
    assert page.status_code == 200
    assert "Lima" in page.text and 'http-equiv="refresh"' in page.text

    png = client.get("/chart.png")
    assert png.headers["content-type"] == "image/png"
    assert png.content.startswith(b"\x89PNG")

    client.get("/data.csv")
    csv = client.get("/data.csv")
    assert "attachment" in csv.headers["content-disposition"]
    assert csv.text.splitlines()[0] == ",".join(COLUMNS.values())
    assert len(list((tmp_path / "output").glob("weather_data_*.csv"))) == 1
    # the three routes share one fetch inside a refresh window
    assert len(calls) == 1
