import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

COLUMNS = {
    "city": "City",
    "temperature_c": "Temperature (C)",
    "temperature_f": "Temperature (F)",
    "humidity_pct": "Humidity (%)",
    "wind_speed_ms": "Wind Speed (m/s)",
    "wind_speed_mph": "Wind Speed (mph)",
}

def to_table(df: pd.DataFrame) -> pd.DataFrame:
    return df[list(COLUMNS)].rename(columns=COLUMNS)


def export(df: pd.DataFrame, output: str | None = None) -> Path:
    out = Path(output or f"output/weather_data_{datetime.now():%Y%m%d_%H%M%S}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    to_table(df).to_csv(out, index=False)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Export processed weather data to CSV")
    parser.add_argument("--input", default="data/processed.json")
    parser.add_argument("--output", help="default: output/weather_data_<timestamp>.csv")
    args = parser.parse_args()

    df = pd.read_json(args.input)
    out = export(df, args.output)
    print(f"wrote {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
