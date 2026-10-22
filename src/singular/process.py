import argparse
from pathlib import Path

import pandas as pd

# 3600 s per hour / 1609.344 m per mile, a fixed definition
MS_TO_MPH = 2.236936


def process(df: pd.DataFrame, sort: str, ascending: bool, top: int) -> pd.DataFrame:
    df = df.assign(
        temperature_f=(df["temperature_c"] * 9 / 5 + 32).round(1),
        wind_speed_mph=(df["wind_speed_ms"] * MS_TO_MPH).round(1),
    )
    df = df.sort_values(sort, ascending=ascending, ignore_index=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df.head(top) if top else df


def main() -> None:
    parser = argparse.ArgumentParser(description="Add derived fields and rank cities")
    parser.add_argument("--input", default="data/raw.json")
    parser.add_argument("--output", default="data/processed.json")
    parser.add_argument("--sort", default="temperature_c", help="column to rank by")
    parser.add_argument("--ascending", action="store_true", help="lowest first, e.g. for humidity")
    parser.add_argument("--top", type=int, default=0, help="keep only the first N, 0 keeps all")
    args = parser.parse_args()

    df = process(pd.read_json(args.input), args.sort, args.ascending, args.top)
    print(df.to_string(index=False))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(out, orient="records", indent=2, force_ascii=False)


if __name__ == "__main__":
    main()
