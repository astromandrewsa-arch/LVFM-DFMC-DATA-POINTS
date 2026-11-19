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

## 2. Progress log (newest last)

### 2026-11-19 — Tier 1 pipeline proven
- **Globe-LFMC 2.0** (CC0): 293,796 LFMC rows, 15 countries, with ERA5-derived covariates kept as
  `src_*`. The personal-contact sheet in the source xlsx is never read.
- **NFMD via FEMS**: the public sample download works when `filterByCategory=All` (an empty value
  silently returns nothing). 382,778 samples 1977–2026 (287k live, 96k dead: 1/10/100/1000-hr,
  duff, litter). FEMS stores dates as local midnight in US Central time (05/06Z) — handled.
- **RAWS fuel sticks via NOAA MADIS** (public archive, no token): hourly netCDF streamed and reduced
  to fuel-moisture stations + co-located weather; sampled at 12 and 21 UTC. 13.6M readings so far
  (2017–2026 complete; 2001–2016 back-filling, newest first). Synoptic not used (token missing and
  its free tier forbids commercial use).
- **De-duplication**: Globe-LFMC renames species (Latin vs NFMD common names), so matching is
  one-to-one on location (~1 km), date, fuel class and value (±1 pt or 1 %), most original source
  kept. 226,578 Globe US rows → NFMD, 19,600 → ONF (matched on the INRA site means ONF rows carry),
  9,380 → Catalonia. Links in `data/normalized/duplicates.parquet`.
- **QA** (`scripts/qa.py`): flags only, nothing dropped. Organic fuels (duff/peat/moss/litter) get
  their own thresholds after real UK duff values >250 % were being flagged as implausible.

### 2026-11-19 — Tier 2/3 ingestion (4 discovery + 3 ingestion subagents)
- Discovery: 699 papers reviewed (`papers.csv`), 206 data leads (`leads.csv`), 15 Africa data
  requests (`requests_africa.csv`).
- Europe: ONF Réseau Hydrique (103,293 replicate rows), SPIF Catalonia (9,541), UK national FMC
  (8,064) + 3 further UK sets, ADAI Lousã (1,018), Saxony destructive + 10-h stick sensors (31,437).
- North America: CFS test-fire FMC 1931–61 (136,246; ~56k are indicator measurements, flagged),
  USFS Hawaii DFM (12,454), BC fire-skips (6,317), Southern Great Plains pyric herbivory (3,146),
  WFSI DoD burns (1,165), 10 more USFS RDS datasets, 2 figshare foliar sets.
- Africa / Australia / S. America: Kruger EBP plot fires (1,589, **undated** in the source),
  Nolan SE-Australia DFMC (3,148), Hobart (355), Cumberland CS505 (363), Annaburroo (3),
  Chaco curing (105, curing % only — no moisture).

### 2026-11-19 — Weather join
Every observation gets, where available: source-provided weather (`src_*`), NASA POWER daily
(`pw_*`, global, 1981+), gridMET (`gm_*`, CONUS, 1979+, incl. fm100/fm1000), nearest station
(`ns_*`: RAWS ≤40 km & ≤600 m elevation difference, else GHCN-Daily ≤75 km; distance and elevation
difference recorded), terrain (Copernicus GLO-30: elevation, slope, aspect) and ESA WorldCover.
Rolling precipitation 3/7/14/30-day, days since rain and VPD are derived for every weather set.
ERA5-Land is **not** attached yet (CDS key needed).
