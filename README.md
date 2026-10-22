# Singular Weather Data Exercise

Fetches current weather for a list of cities from the [Open-Meteo API](https://open-meteo.com/en/docs), saves it as a CSV with Fahrenheit and mph columns, and shows it as bar charts on a FastAPI web page.

## Install

Install [uv](https://docs.astral.sh/uv/), and [just](https://just.systems/) (optional if you want the short commands). 

On macOS:

```sh
brew install uv just
```

On Linux, or without Homebrew:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install rust-just
```

On Windows, in PowerShell, then open a new terminal so the commands are on the PATH:

```powershell
winget install astral-sh.uv Casey.Just
```

Then, in the project folder, install the dependencies. You do not need to install Python first: uv downloads Python 3.12 if it is missing.

```sh
uv sync
```

## Commands

| Command | What it does |
|---|---|
| `just` | Lists all commands |
| `just run` | Runs fetch, process, save and chart in one go. Takes the same arguments as the steps below, for example `just run "Tokyo,London" humidity_pct 5 --ascending` |
| `just fetch` | Fetches weather into `data/raw.json` for every city in `cities.json`. `just fetch "Tokyo,Lisbon"` picks cities, and a name missing from the file is looked up by the geocoding API |
| `just process` | Adds Fahrenheit, mph and a rank, prints the table and writes `data/processed.json`. `just process humidity_pct 3 --ascending` sorts by another column, keeps the top 3 and puts the lowest first |
| `just save` | Writes `output/weather_data_<timestamp>.csv`. `just save --output weather_data.csv` writes a fixed name |
| `just chart` | Draws temperature, humidity and wind bar charts from the newest CSV into a `.png` next to it |
| `just serve` | Starts the web server on http://localhost:8000, or another port with `just serve 9000` |
| `just test` | Runs the tests |
| `just typecheck` | Runs basedpyright |
| `just check` | Runs the tests and basedpyright |

## Without just

Each step is a script you can run with `uv run`, the same way in macOS, Linux and Windows PowerShell. Add `--help` to any of them to see its options.

```sh
uv run weather-fetch --cities "Tokyo,London"    # empty --cities uses cities.json
uv run weather-process --sort humidity_pct --top 5 --ascending
uv run weather-export                           # --output weather_data.csv for a fixed name
uv run weather-chart
uv run uvicorn singular.server:app --port 8000
uv run pytest
uv run basedpyright
```

## Output

`just run` prints a table of the cities ranked by the sort column, hottest first by default, and writes two files to `output/`:

- `weather_data_<timestamp>.csv` has one row per city in rank order.
- `weather_data_<timestamp>.png` has one bar chart each for temperature (°C), humidity and wind speed (m/s), with the value on each bar.

| CSV column | Meaning |
|---|---|
| `City` | City name from `cities.json` or from `--cities` |
| `Temperature (C)`, `Temperature (F)` | Air temperature 2 m above the ground |
| `Humidity (%)` | Relative humidity 2 m above the ground |
| `Wind Speed (m/s)`, `Wind Speed (mph)` | Wind speed 10 m above the ground |

The printed table also shows `rank`, the coordinates and `time`, the UTC quarter hour the values are valid for. The CSV leaves them out to match the exercise's example output.

Example run:

```
$ just run "New York,Tokyo,London"
uv run weather-fetch --cities 'New York,Tokyo,London'
fetched 3 cities -> data/raw.json
uv run weather-process --sort temperature_c --top 0
 rank     city  latitude  longitude             time  temperature_c  humidity_pct  wind_speed_ms  temperature_f  wind_speed_mph
    1 New York   40.7128   -74.0060 2026-10-22T17:15           17.4            28           6.99           63.3            15.6
    2   London   51.5074    -0.1278 2026-10-22T17:15           14.0            56           2.20           57.2             4.9
    3    Tokyo   35.6895   139.6917 2026-10-22T17:15           13.5            67           0.80           56.3             1.8
uv run weather-export
wrote 3 rows -> output/weather_data_20261022_142136.csv
uv run weather-chart
chart -> output/weather_data_20261022_142136.png
```

The lines that start with `uv run` are the commands just runs for each step. The CSV it wrote:

```csv
City,Temperature (C),Temperature (F),Humidity (%),Wind Speed (m/s),Wind Speed (mph)
New York,17.4,63.3,28,6.99,15.6
London,14.0,57.2,56,2.2,4.9
Tokyo,13.5,56.3,67,0.8,1.8
```

New York is the warmest and windiest of the three at that time, and Tokyo the most humid.

## Endpoints

| Route | Returns |
|---|---|
| `GET /` | Charts and table, reloads every 15 minutes |
| `GET /chart.png` | Bar charts as a PNG |
| `GET /data.csv` | A new timestamped CSV as a download |

The routes share one fetch per 15 minutes, which is how often Open-Meteo updates.

## Decisions

- uv manages Python and the dependencies, instead of pip with a `requirements.txt`. It creates a `.venv` used only by this project, so nothing gets installed into the system Python. `pyproject.toml` keeps runtime dependencies apart from dev tools (pytest, basedpyright), and `uv.lock` pins exact versions so every machine installs the same set. It also downloads the right Python and installs much faster than pip.
- Just is a command runner that gives each script a short command, and `just run` chains the steps. It is optional, since every step also runs with `uv run`. I chose it over a Makefile because make is missing on Windows and its recipes need tab indentation.
- The assignment describes one script. I split it into separate scripts that each do one job (fetch, process, export, chart), for separation of concerns. Each script runs and is tested alone, and the CLI passes data between them through files in `data/`. The API imports the same functions, so the CLI and the API share one implementation.
- One API request for all cities. One per city would use 10 times the rate limit.
- The API returns wind in m/s and `process.py` converts it to mph, because the API returns one unit per request.
- Charts use matplotlib's `Figure`, because `pyplot` keeps global state that is not safe in a server.
- CSV names carry a timestamp, so runs never overwrite each other. Clean `output/` by hand.
- No dotenv was needed, because the project has no secrets or API keys.
- basedpyright runs in `recommended` mode with `reportAny`, `reportUnusedCallResult` and `reportUnknownMemberType` off, since argparse, JSON and matplotlib stubs trip them.

## Limits

- Open-Meteo's free tier is non-commercial only, about 10,000 calls a day.
- City names in `cities.json` are case-sensitive. Other spellings go to the geocoding API.
