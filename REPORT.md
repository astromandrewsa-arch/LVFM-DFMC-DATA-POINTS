# Fuel moisture data harvest — running report

Pyrome Technologies. Goal: every publicly obtainable measured fuel moisture observation, each
paired with weather. Layout and rules follow the project brief (normalized Parquet in
`data/normalized/`, catalogs in `data/catalog/`, one fetch/normalize script per source in
`scripts/`).

## 1. Plan (written 2026-11-19)

### Order of work
| # | Source | Kind | Est. measured records | Access | Credential |
|---|--------|------|----------------------|--------|------------|
| 1 | Globe-LFMC 2.0 (Yebra et al. 2024) | LFMC, 15 countries | ~294k | Figshare, CC0 | none |
| 2 | RAWS / mesonet fuel sticks via NOAA MADIS public archive | 10-hr stick, hourly, ~2,000 US stations, 2001– | millions (sampled 2 h/day → ~10M) | HTTPS archive | none |
| 3 | US NFMD (now in USFS FEMS) | live + dead (1/10/100/1000-hr, duff, litter) | ~500k–1M samples | FEMS GraphQL / CSV | none (works anonymously with `filterByCategory=All`) |
| 4 | FEMS NFDRS outputs (1/10/100/1000-hr modeled FM per RAWS) | *estimate* | — | FEMS CSV, public | none |
| 5 | gridMET (fm100, fm1000 + weather) | covariates / estimates | — | THREDDS NCSS, public | none |
| 6 | NASA POWER daily (MERRA-2/CERES) | global covariates | — | REST, public | none |
| 7 | ERA5-Land | global covariates | — | CDS API | **CDS key needed** |
| 8 | Synoptic (MesoWest) | RAWS fuel sticks, real time | — | REST | **token needed; free tier is non-commercial** |
| 9 | Copernicus EWDS fire danger (FWI, FFMC/DMC/DC), GEFF | *estimate* | — | CDS/EWDS API | **CDS/EWDS key needed** |
| 10 | Australian AFMS + field LFMC | LFMC | ~10k? | TBD | TBD |
| 11 | Tier 2 national networks, Tier 3 literature/repositories, Tier 4 snowball | mixed | TBD | discovery agents → `data/catalog/leads*.csv` | — |

### Credentials needed (none are set in this environment)
- **Copernicus CDS / EWDS** (`CDSAPI_URL`, `CDSAPI_KEY`): ERA5-Land point time series, CEMS fire danger
  reanalysis, GEFF. Free account at https://cds.climate.copernicus.eu.
- **NASA Earthdata** (`EARTHDATA_USERNAME`, `EARTHDATA_TOKEN`): ORNL DAAC downloads (e.g. SAFARI 2000), MODIS/VIIRS NDVI.
- **Synoptic Data** (`SYNOPTIC_TOKEN`): only needed if MADIS coverage proves incomplete. The open
  tier's terms restrict commercial use, so a commercial license would be needed for training use.
- ~~USFS FEMS login~~ — not needed: the public sample download works when `filterByCategory=All`.
- **Dryad API token** (`DRYAD_TOKEN`): Dryad file downloads now return 401 without one (Kruger
  fire-spread data, chaparral 32-yr LFMC, moisture-meter study, savanna grass flammability, FLAMITS).

Workarounds in use: MADIS public archive in place of Synoptic for measured RAWS fuel sticks;
NASA POWER + gridMET in place of ERA5-Land until a CDS key is provided.

## 2. Progress log
(see entries below, newest last)
