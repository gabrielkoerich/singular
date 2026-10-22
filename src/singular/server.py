import io
import time
from functools import lru_cache

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response

from singular.chart import plot
from singular.export import export, to_table
from singular.fetch import fetch, load_cities
from singular.process import process

# Open-Meteo refreshes current conditions every 15 minutes
REFRESH_SECONDS = 900

app = FastAPI(title="Weather")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Weather</title>
<meta http-equiv="refresh" content="{refresh}">
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 960px; padding: 0 1rem; }}
img {{ max-width: 100%; }}
table {{ border-collapse: collapse; margin: 1rem 0; }}
th, td {{ padding: .3rem .8rem; border-bottom: 1px solid #ddd; text-align: left; }}
</style></head>
<body>
<h1>Current weather</h1>
<p>Observed {observed} UTC, the page refreshes every {minutes} minutes.</p>
<p><a href="/data.csv">Download CSV</a></p>
<img src="/chart.png?t={bucket}" alt="weather charts">
{table}
</body></html>"""


def bucket() -> int:
    return int(time.time() // REFRESH_SECONDS)


def current() -> pd.DataFrame:
    return _current(bucket())


# one fetch per window keeps the page, chart and CSV on the same data and inside the rate limit
@lru_cache(maxsize=1)
def _current(_bucket: int) -> pd.DataFrame:
    known = load_cities("cities.json")
    try:
        rows = fetch(list(known), known)
    except requests.RequestException as e:
        raise HTTPException(502, f"Open-Meteo request failed: {e}")

    return process(pd.DataFrame(rows), "temperature_c", False, 0)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    df = current()
    return PAGE.format(
        refresh=REFRESH_SECONDS,
        minutes=REFRESH_SECONDS // 60,
        observed=df["time"].iloc[0],
        bucket=bucket(),
        table=to_table(df).to_html(index=False, border=0),
    )


@app.get("/chart.png")
def chart() -> Response:
    buf = io.BytesIO()
    plot(to_table(current())).savefig(buf, format="png")
    return Response(buf.getvalue(), media_type="image/png")


@app.get("/data.csv")
def data() -> FileResponse:
    path = export(current())
    return FileResponse(path, media_type="text/csv", filename=path.name)
