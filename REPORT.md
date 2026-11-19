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

## 3. Summary (2026-11-19, end of first session)

Full tables (by source, country, decade, weather coverage, licensing) are regenerated by
`scripts/run_pipeline.sh` into [`data/normalized/report_stats.md`](data/normalized/report_stats.md).

### Totals
| | rows | QA-clean (no hard flag, not a duplicate) |
|---|---:|---:|
| **All measured observations** | 14,143,310 | **13,717,078** |
| Dead fuel | | 13,266,710 (of which RAWS/mesonet 10-h sticks 12.98M) |
| Live fuel | | 450,368 |
| Excluding MADIS sticks | | 740,777 (290,409 dead, 450,368 live) |

- **Years:** 1932–2026. Live fuel is dense from the late 1990s; dead fuel from 2017 onward
  (MADIS), with the 1930s–1960s carried by the Canadian test-fire archive.
- **Countries (18):** USA 13.39M, Canada 141k, France 108k, Germany 31k, Spain 19k, UK 10k,
  Australia 7k, Italy 2.6k, Israel 2.2k, Portugal 1.1k, South Africa 950, Türkiye 689, Tunisia 449,
  China 264, Argentina 241, Senegal 96 (+ 2.7k mesonet rows just outside US borders).
- **Weather covariates:** 14,140,857 of 14,143,310 rows (100.0 %) have at least one weather set.
  NASA POWER covers every dated row from 1981 on; gridMET covers 93 % of US rows; nearest station
  covers 90 % of non-MADIS rows; MADIS rows carry their own co-located station weather.
  **ERA5-Land is not yet attached anywhere** (needs a CDS key).
- **Estimates (kept separate):** 90.8M NFDRS 2016 modeled dead/live fuel moisture rows at 2,088 RAWS
  (git-ignored, reproducible). No remote-sensing LFMC product sampled yet.

### Licensing breakdown (rows)
| License family | sources | rows |
|---|---:|---:|
| NOAA MADIS public tier (RAWS = US Gov public domain; MesoWest-provided rows unclear, flagged in notes) | 1 | 13,143,594 |
| US Government work / public domain (NFMD, USFS RDS) | 12 | 399,872 |
| CC0 | 2 | 293,799 |
| CC-BY-4.0 | 13 | 150,344 |
| Open Government Licence – Canada | 1 | 136,246 |
| OGL-UK-3.0 | 3 | 9,914 |
| MPL-2.0 / GPL (SPIF Catalonia — software licence on data; legal check advised) | 1 | 9,541 |
All allow commercial use with attribution. Excluded for licence reasons: Synoptic free tier
(non-commercial), Annaburroo full set (CC-BY-NC-ND), MLHub/Source Cooperative LFMC (CC-BY-NC-ND),
TU Dresden Cerrado (CC-BY-NC), six unlicensed GitHub repos (need owner permission).

### Gaps
- **Africa:** effectively none usable for a daily model. 950 South African fynbos LFMC + 96 Senegal
  grassland rows (via Globe-LFMC); 1,589 Kruger plot-fire grass moistures that are **undated** in
  the published file. **No Zimbabwe data at all.** No African country runs an open fuel-moisture or
  curing network. See `data/catalog/requests_africa.csv` for the 15 author/agency requests that
  would change this (SANParks dated EBP fire database, Gambiza/Forestry Commission Gwayi data,
  DR&SS Marondera/Matopos trials, Hoffa Zambia, Cardoso Kruger via Dryad token).
- **Grassland fuels:** grass rows are a small share (≈10k NFMD grass, 3.1k Southern Great Plains
  clip plots, 1.6k Kruger). Grass curing % exists only for Chaco (105 rows, no moisture).
- **Dead fuel outside the US** is thin (Canada historic, Germany sticks, UK, SE Australia).
- **MADIS 2001–2016** back-fill in progress (8,155 of 18,904 hour-files extracted).

### Top 10 leads not yet accessed
| # | Lead | Why not | What would unlock it |
|---|---|---|---|
| 1 | ERA5-Land point time series (covariates for every row) | needs Copernicus CDS key | `CDSAPI_URL` + `CDSAPI_KEY` |
| 2 | CEMS fire-danger reanalysis (FFMC/DMC/DC) and GEFF | needs CDS/EWDS key | same key |
| 3 | Kruger fire-spread dataset (Cardoso et al. 2022, Dryad, CC0, 1,131 fires) | Dryad downloads return 401 | `DRYAD_TOKEN` |
| 4 | SANParks Kruger Experimental Burn Plot fire database (956+ dated burns with grass moisture) | not published | request to SANParks Scientific Services |
| 5 | Serengeti grass fuel moisture (Duke 10.7924/r4r567, CC0) | bot protection, no file API | manual browser download |
| 6 | Gwayi, Zimbabwe fire behaviour (Gambiza 2005) — only Zimbabwe field data found | host returns 503 | retry `eprints.ru.ac.za/337/1/sajs_gambiza.pdf`, or ask author |
| 7 | CEIF-ADAI Portugal fine-fuel FMC 2000–2024 (2,525 records, CC-BY) | repository rejects our client | manual download of `ADAI_FMC_dataset_1.0.csv` |
| 8 | SAFARI-2000 burns (ORNL 752) and LBA-ECO Brazil fuel sticks (ORNL 1232) | NASA Earthdata login | Earthdata credentials |
| 9 | FLAMITS flammability traits (Dryad, 19,972 records incl. moisture, CC0) and Simpson savanna grass flammability (Dryad) | Dryad 401 | `DRYAD_TOKEN` |
| 10 | Pepperwood LFM and other unlicensed GitHub field datasets | no licence | owner permission |

### Still running when this session ended
- MADIS back-fill 2001–2016 (`fetch_madis_raws.py`, resumable; then `normalize_madis_raws.py` and
  `run_pipeline.sh`).
- gridMET top-up for 379 late-added US sites (`fetch_gridmet.py --topup 1`).
