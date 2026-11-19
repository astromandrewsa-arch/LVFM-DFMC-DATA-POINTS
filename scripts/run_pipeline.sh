#!/usr/bin/env bash
# Rebuild everything downstream of the per-source normalized files, in dependency order.
# Fetch/normalize scripts for each source are run separately (scripts/fetch_*.py, normalize_*.py);
# long-running fetchers (MADIS, gridMET) are resumable and can be re-run at any time.
set -euo pipefail
cd "$(dirname "$0")"

python3 build_observations.py      # QA + cross-source de-duplication -> observations.parquet/, remote_sensing_estimates.parquet/
python3 sites.py                   # unique locations -> sites.parquet
python3 fetch_terrain.py           # DEM + WorldCover for new sites (incremental)
python3 fetch_nasa_power.py        # POWER cells for new sites (incremental)
python3 fetch_fems_raws_daily.py   # RAWS daily summaries near sites (incremental)
python3 fetch_ghcnd.py             # GHCN-Daily near sites (incremental)
python3 nearest_station.py         # station features + site -> station map
python3 join_weather.py            # covariates -> weather_join.parquet/
python3 build_catalog.py           # sources.csv, leads.csv, papers.csv
python3 report_stats.py > ../data/normalized/report_stats.md
