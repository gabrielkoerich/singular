import argparse
import json
from pathlib import Path
from typing import TypedDict

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

class Current(TypedDict):
    time: str
    temperature_2m: float
    relative_humidity_2m: int
    wind_speed_10m: float


class Forecast(TypedDict):
    current: Current


class Weather(TypedDict):
    city: str
    latitude: float
    longitude: float
    time: str
    temperature_c: float
    humidity_pct: int
    wind_speed_ms: float


def geocode(name: str) -> tuple[float, float]:
    resp = requests.get(GEOCODE_URL, params={"name": name, "count": 1}, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise SystemExit(f"city not found: {name}")

    return results[0]["latitude"], results[0]["longitude"]


def load_cities(path: str) -> dict[str, tuple[float, float]]:
    return {c["City"]: (c["Latitude"], c["Longitude"]) for c in json.loads(Path(path).read_text(encoding="utf-8"))}


def fetch(cities: list[str], known: dict[str, tuple[float, float]]) -> list[Weather]:
    coords = [known.get(city) or geocode(city) for city in cities]
    resp = requests.get(
        FORECAST_URL,
        params={
            "latitude": ",".join(str(lat) for lat, _ in coords),
            "longitude": ",".join(str(lon) for _, lon in coords),
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "wind_speed_unit": "ms",
        },
        timeout=10,
    )
    resp.raise_for_status()
    payload: Forecast | list[Forecast] = resp.json()
    # the API returns a list for many locations and a bare object for one
    data = [payload] if isinstance(payload, dict) else payload

    return [
        Weather(
            city=city,
            latitude=lat,
            longitude=lon,
            time=d["current"]["time"],
            temperature_c=d["current"]["temperature_2m"],
            humidity_pct=d["current"]["relative_humidity_2m"],
            wind_speed_ms=d["current"]["wind_speed_10m"],
        )
        for city, (lat, lon), d in zip(cities, coords, data, strict=True)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch current weather from Open-Meteo")
    parser.add_argument("--cities", default="", help="comma separated names, default: every city in --cities-file")
    parser.add_argument("--cities-file", default="cities.json")
    parser.add_argument("--output", default="data/raw.json")
    args = parser.parse_args()

    known = load_cities(args.cities_file)
    cities = [c.strip() for c in args.cities.split(",") if c.strip()] or list(known)
    rows = fetch(cities, known)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"fetched {len(rows)} cities -> {out}")


if __name__ == "__main__":
    main()
