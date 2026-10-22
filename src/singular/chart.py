import argparse
from pathlib import Path

import pandas as pd
from matplotlib.figure import Figure

OUTPUT = Path("output")
METRICS = ["Temperature (C)", "Humidity (%)", "Wind Speed (m/s)"]


def latest_csv() -> Path:
    files = sorted(OUTPUT.glob("weather_data_*.csv"))
    if not files:
        raise FileNotFoundError("no CSV in output/, run `just run` first")

    return files[-1]


# Figure instead of pyplot, pyplot keeps global state that is not safe in a web server
def plot(df: pd.DataFrame) -> Figure:
    fig = Figure(figsize=(10, 3 * len(METRICS)))
    axes = fig.subplots(len(METRICS), 1, sharex=True)
    for ax, col in zip(axes, METRICS):
        ax.bar(df["City"], df[col], color="tab:blue")
        ax.bar_label(ax.containers[0], fontsize=8)
        ax.set_title(col)
        ax.margins(y=0.15)

    axes[-1].tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw bar charts from a weather CSV")
    parser.add_argument("--input", help="default: newest CSV in output/")
    parser.add_argument("--output", help="default: input path with .png")
    args = parser.parse_args()

    src = Path(args.input) if args.input else latest_csv()
    out = Path(args.output) if args.output else src.with_suffix(".png")
    plot(pd.read_csv(src)).savefig(out)
    print(f"chart -> {out}")


if __name__ == "__main__":
    main()
