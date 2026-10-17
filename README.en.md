# energy-dashboard-predial

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A local building energy consumption dashboard that reads a 90-day series at 15-minute intervals, compares each reading against the building's own baseline, estimates cost in two tariff bands, and generates an HTML report with per-hour charts — no cloud, no external API, no framework to install.

## Problem / Why it exists

In building automation, consumption almost always lives inside a closed telemetry system. In a new building or after a transfer, the practical question is "what changed this week relative to this building's normal pattern?". Answering that usually requires exporting data, learning the telemetry tool, or depending on the cloud.

This project serves the local automation side because the CSV never leaves the machine, the server listens only on 127.0.0.1, and the HTML report opens in the browser without internet. The value is in the open accounting of the method (docs/ shows the baseline calculation by hand) and in clearly declaring what the model does not cover.

## What it does

- CSV reading and validation (header ts,andar,kwh; finite and non-negative values; no duplicate timestamp and floor)
- Baseline per hour with component A (mean of the 4 readings at the same hour, same day of week, 7 days prior) and component B (mean of all readings at the same hour in the previous calendar month); L is the mean of the existing components
- Deviation detection with 50 percent threshold above baseline and minimum absolute margin of 0.15 kWh; alerts on the same floor separated by less than 24 hours form a single episode
- Cost estimation with two-band tariff (peak and off-peak) per weekday and hour, plus demand in kW and load factor as indicators
- Single-file offline HTML report with no CDN (pure canvas charts), plus terminal text summary
- Local server at http://127.0.0.1:8000 with routes /, /api/resumo and /saude, running in foreground until Ctrl+C

## Stack

- Python 3.10+; standard library only plus PyYAML (reading the tariff YAML)
- sqlite3 (in-memory database for the reading series)
- http.server (local server, blocking until Ctrl+C)
- Single-file HTML with inline CSS and JS and pure canvas charts (no CDN, no frontend framework)
- pytest and pytest-cov (development environment)
- Packaging with src/ layout, pyproject.toml and entry point energydash (pip install -e .)

## How it works

The pipeline is ler_csv -> SQLite in-memory -> baseline -> deviation detection -> cost -> deterministic JSON payload -> text or HTML.

1. serie.ler_csv validates header, types, finite and non-negative values, and prevents (timestamp, floor) duplicates.
2. linha_base builds two indexes (by weekday and hour; by month and hour) and answers in O(1) for each instant — component A (4 readings at same hour, same weekday, 7 days prior) and component B (all readings at same hour in previous month); L is the mean of existing components.
3. desvio alerts when kwh - L > max(0.50 * L, 0.15 kWh); alerts on the same floor separated by less than 24 hours merge into an episode from first to last alerted reading.
4. custo classifies each reading into peak or off-peak band of dados/tarifa.yaml and sums kwh times band price; demand is the highest kwh of an interval converted to kW and load factor is mean kW divided by demand.
5. api.montar_resumo rounds all numbers, making output deterministic (same series, same JSON). relatorio writes the single-file HTML (template with placeholder __DADOS__) or prints the text summary.

## How to run

You need Python 3.10+.

```powershell
# 1. Install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

# 2. Validate (tests)
python -m pytest tests/ -q
```

The repository reports 74 passing tests.

# 3. Run
python -m energydash resumo
```

Real example output with dados/serie-consumo.csv and dados/tarifa.yaml (fictitious tariff, illustrative only).

```
CONSUMPTION REPORT - energy-dashboard-predial
==============================================
Period: 2026-06-01 to 2026-08-29 (90 days)
Floors: 3 (floor-1, floor-2, floor-3)
Total: 14630.8 kWh
Estimated cost: BRL 10479.69 (peak: BRL 3067.15 | off-peak: BRL 7412.54)
Demand: 15.60 kW | Load factor: 0.43
Method: same hour last week + same month last month | Threshold: 50 percent above | minimum margin 0.15 kWh

Consumption by floor:
  floor-1: 9286.7 kWh | cost BRL 6648.60 | average 103.2 kWh/day
  floor-2: 2082.5 kWh | cost BRL 1509.97 | average 23.1 kWh/day
  floor-3: 3261.6 kWh | cost BRL 2321.11 | average 36.2 kWh/day

Detected deviations: 3
  1. floor-2 | 2026-06-26T20:00 to 2026-06-26T22:45 (2.8 h, 12 intervals) | peak 3.90 kWh (+1058 percent above baseline)
  2. floor-3 | 2026-07-26T22:00 to 2026-08-03T05:45 (175.8 h, 256 intervals) | peak 2.41 kWh (+1328 percent above baseline)
  3. floor-1 | 2026-08-17T00:00 to 2026-08-29T23:45 (311.8 h, 1246 intervals) | peak 3.52 kWh (+279 percent above baseline)
```

Without installing the package, `python -m energydash` works from the repo root because energydash.py is a shim that inserts src/ into sys.path and delegates to src/energydash. The shim is a file, not a directory, so coverage measures the src/ package.

Other commands

```powershell
python -m energydash exportar --saida exemplos\dashboard.html   # does not block; generates HTML artifact
python -m energydash servir --porta 8000                        # blocking; Ctrl+C ends
tools\abrir-dashboard.bat                                       # double click: serves at http://127.0.0.1:8000
```

`servir` stays in foreground until Ctrl+C and exposes /, /api/resumo and /saude. `exemplos/dashboard.html` opens with double click and works offline without CDN.

## Project structure

```
src/energydash/
  serie.py            CSV reading and validation; groupings by day, hour, floor
  consulta.py         in-memory SQLite database with table leitura(ts, andar, kwh)
  linha_base.py       baseline calculation - last week plus last month
  desvio.py           alert rule, minimum margin, episodes (24h window)
  custo.py            peak/off-peak tariff, demand and load factor
  relatorio.py        text summary and offline HTML (pure canvas, no CDN)
  api.py              aggregate JSON payload with deterministic output
  servidor.py         http.server on 127.0.0.1 with routes /, /api/resumo and /saude
  cli.py              resumo, exportar and servir commands
  templates/dash.html single panel template (placeholder __DADOS__)
energydash.py         root shim for python -m energydash (file, not directory)
dados/                serie-consumo.csv (25920 readings) and tarifa.yaml (fictitious)
docs/                 baseline method and how to read the consumption report
exemplos/             real terminal outputs and generated dashboard.html
tests/                74 tests
tools/                gerar_dados.py (deterministic, fixed seed) and abrir-dashboard.bat
```

## Trade-offs and decisions

- Sliding baseline (last week + last month) instead of fixed reference. It is simple, no configuration parameters, but absorbs persistent changes after about two weeks. A high regime starting on day D enters "last week" on D+7 and "last month" on D+30; L rises with consumption and the alert stops. That is why the persistent deviation (floor-1) was planted only in the last 13 days of the period (docs/metodo-de-linha-base.md).
- 24-hour alert merging window. A recurring deviation (e.g., air conditioning every night) does not become hundreds of lines; two alerts 20 hours apart become the same episode.
- Absolute margin of 0.15 kWh alongside the 50 percent threshold. Prevents alerts from noise in nearly empty hours (baseline around 0.04 kWh, where 50 percent is 0.02 kWh) without hiding real spikes.
- Bug fixed - the first version of component A included the current day t (mistaken 8-day window). Deviation 3 peak dropped from about 436 percent to 180 percent on floor-1 and weekends stopped flagging. The fix excluded the current day from window A. A baseline that includes the current point is self-referential and would never flag an isolated spike.
- Root shim as file, not directory. With a directory, pytest-cov would treat --cov=energydash as source folder, measure the shim (0 percent) and report "No data was collected".
- Deterministic output. gerar_dados.py uses random.Random(20260601) and standard library only; nothing uses datetime.now() in the output path. The same CSV always produces the same deviations and cost.

## Known limitations

- No sector breakdown. There is one meter per floor (floor-1, floor-2, floor-3); no division by room, circuit or equipment, so a spike cannot be assigned to a specific point.
- Fictitious tariff. dados/tarifa.yaml uses invented values (peak price BRL 0.9874, off-peak BRL 0.6432, peak on weekdays from 5 PM to 11 PM); estimated cost demonstrates the two-band model and does not predict a real bill.
- No demand charge or power factor. The cost model is kwh times band price; demand (kW) and load factor appear as indicators, not billed items.
- About two-week window. Persistent regime change disappears from the report once the baseline absorbs it; long-term monitoring would require a fixed reference.
- Local server only. Listens on 127.0.0.1; not for network exposure.
- No authentication. Local dashboard without access control.

## License

MIT. See [LICENSE](LICENSE).

## Author

Kelvin Oliveira
https://github.com/KelvinOliveiraCode
https://kelvinoliveiracode.github.io/portfolio/
