# Windows has no sh, so recipes run in PowerShell there
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# cities is a comma separated list, empty uses every city in cities.json
fetch cities="":
    uv run weather-fetch {{ if cities == "" { "" } else { "--cities " + quote(cities) } }}

process sort="temperature_c" top="0" *flags:
    uv run weather-process --sort {{ sort }} --top {{ top }} {{ flags }}

# pass --output <path> for a fixed name, default is output/weather_data_<timestamp>.csv
save *flags:
    uv run weather-export {{ flags }}

# default input is the newest CSV in output/, writes a .png next to it
chart *flags:
    uv run weather-chart {{ flags }}

# example: just run "Tokyo,London,Berlin" humidity_pct 5 --ascending
run cities="" sort="temperature_c" top="0" *flags: (fetch cities) (process sort top flags) save chart

# open http://localhost:{{port}}
serve port="8000":
    uv run uvicorn singular.server:app --port {{ port }}

test:
    uv run pytest -q

typecheck:
    uv run basedpyright

check: test typecheck
