"""Assemble data/catalog/sources.csv, leads.csv and papers.csv.

sources.csv = CORE_SOURCES below + every data/catalog/sources_*_agent.csv, with record counts
refreshed from data/normalized/by_source/ where the source has been ingested.
leads.csv   = union of data/catalog/leads_*_agent.csv, normalized to url,type,status,notes (+ extras).
papers.csv  = union of data/catalog/papers_*_agent.csv.
"""
import glob
from datetime import date

import pandas as pd

from common import BY_SOURCE, CATALOG, EST_BY_SOURCE

COLS = ["source_id", "name", "url", "publisher", "license", "access_method", "records", "date_range",
        "countries", "citation", "retrieved_on", "status"]
TODAY = str(date.today())

CORE_SOURCES = [
    dict(source_id="globe_lfmc2", name="Globe-LFMC 2.0", url="https://doi.org/10.6084/m9.figshare.25413790",
         publisher="Yebra et al. / Springer Nature figshare", license="CC0-1.0",
         access_method="figshare ndownloader (xlsx)", countries="15 countries",
         citation="Yebra M. et al. (2024) Globe-LFMC 2.0, an enhanced and updated dataset for live fuel moisture content research. Scientific Data 11, 332.",
         status="ingested; compilation (overlaps NFMD, ONF, Catalonia) -> deduped against originals"),
    dict(source_id="fems_nfmd", name="US National Fuel Moisture Database (NFMD) field samples via USFS FEMS",
         url="https://fems.fs2c.usda.gov", publisher="USDA Forest Service / interagency contributors",
         license="US Government work, public domain (no restrictions stated)",
         access_method="FEMS public CSV download (fuelmodel/sample/download, filterByCategory=All) + GraphQL site table",
         countries="USA", citation="USDA Forest Service. National Fuel Moisture Database, Fire Environment Mapping System (FEMS).",
         status="ingested"),
    dict(source_id="madis_raws", name="RAWS and mesonet 10-hr fuel stick moisture via NOAA MADIS public archive",
         url="https://madis-data.ncep.noaa.gov/madisPublic1/data/archive/", publisher="NOAA MADIS (data from BLM/USFS RAWS, MesoWest, HADS)",
         license="MADIS public (unrestricted) tier; RAWS is US Government public domain. MesoWest-provided rows: provider terms unclear -> flagged in notes (provider=MesoWest)",
         access_method="HTTPS hourly LDAD mesonet netCDF; sampled at 12 and 21 UTC daily",
         countries="USA (+ few CAN/MEX)", citation="NOAA Meteorological Assimilation Data Ingest System (MADIS).",
         status="in progress (background fetch, newest first)"),
    dict(source_id="fems_nfdrs", name="FEMS NFDRS 2016 modeled 1/10/100/1000-hr and live fuel moisture per RAWS",
         url="https://fems.fs2c.usda.gov/api/climatology/download-nfdr", publisher="USDA Forest Service",
         license="US Government work, public domain", access_method="FEMS public CSV", countries="USA",
         citation="USDA Forest Service FEMS", status="lead; estimates only (not labels)"),
    dict(source_id="gridmet", name="gridMET daily meteorology and fm100/fm1000", url="https://www.climatologylab.org/gridmet.html",
         publisher="University of Idaho / Climatology Lab (Abatzoglou 2013)", license="CC0 / public domain",
         access_method="yearly netCDF, sampled at sites", countries="USA (CONUS)",
         citation="Abatzoglou J.T. (2013) Development of gridded surface meteorological data for ecological applications and modelling. Int. J. Climatol. 33:121-131.",
         status="covariates (in progress)"),
    dict(source_id="nasa_power", name="NASA POWER daily point data (MERRA-2, CERES)", url="https://power.larc.nasa.gov",
         publisher="NASA Langley Research Center", license="NASA open data, no restrictions (attribution requested)",
         access_method="REST API per 0.5x0.625 deg cell", countries="global",
         citation="NASA Langley Research Center POWER Project, funded through the NASA Earth Science Directorate Applied Science Program.",
         status="covariates (in progress)"),
    dict(source_id="copernicus_dem", name="Copernicus DEM GLO-30", url="https://registry.opendata.aws/copernicus-dem/",
         publisher="ESA / DLR / Airbus", license="Copernicus DEM licence: free incl. commercial, attribution required",
         access_method="AWS COG range reads", countries="global", citation="Copernicus DEM GLO-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA",
         status="covariates"),
    dict(source_id="esa_worldcover", name="ESA WorldCover 10 m 2021 v200", url="https://esa-worldcover.org",
         publisher="ESA", license="CC-BY-4.0", access_method="AWS COG range reads", countries="global",
         citation="Zanaga D. et al. (2022) ESA WorldCover 10 m 2021 v200. doi:10.5281/zenodo.7254221", status="covariates"),
    dict(source_id="era5_land", name="ERA5-Land hourly / timeseries", url="https://cds.climate.copernicus.eu",
         publisher="ECMWF / Copernicus C3S", license="Copernicus licence (commercial use allowed)",
         access_method="CDS API", countries="global", citation="Muñoz Sabater J. (2019) ERA5-Land hourly data from 1950 to present. C3S CDS.",
         status="blocked: needs CDS API key (CDSAPI_URL/CDSAPI_KEY)"),
    dict(source_id="cems_fire_danger", name="CEMS fire danger indices historical (FWI: FFMC/DMC/DC) and GEFF reanalysis",
         url="https://ewds.climate.copernicus.eu", publisher="ECMWF / Copernicus EMS", license="Copernicus licence",
         access_method="EWDS/CDS API", countries="global", citation="Vitolo C. et al. (2020) ERA5-based global meteorological wildfire danger maps. Sci Data 7:216.",
         status="blocked: needs CDS/EWDS key; estimates only"),
    dict(source_id="synoptic", name="Synoptic Data (MesoWest) API — RAWS fuel_moisture", url="https://synopticdata.com",
         publisher="Synoptic Data PBC", license="Open-access tier is non-commercial; commercial use needs a paid licence",
         access_method="REST API (token)", countries="USA+", citation="Synoptic Data PBC",
         status="not used: token missing and terms restrict commercial use; MADIS used instead"),
]


def counts():
    out = {}
    for f in glob.glob(str(BY_SOURCE / "*.parquet")):
        n = pd.read_parquet(f, columns=["date"])
        out[f.rsplit("/", 1)[-1][:-8]] = (len(n), n["date"].min(), n["date"].max())
    for d in glob.glob(str(BY_SOURCE / "*/")):
        sid = d.rstrip("/").rsplit("/", 1)[-1]
        parts = [pd.read_parquet(f, columns=["date"]) for f in glob.glob(d + "*.parquet")]
        if parts:
            n = pd.concat(parts)
            out[sid] = (len(n), n["date"].min(), n["date"].max())
    for f in glob.glob(str(EST_BY_SOURCE / "*.parquet")):
        n = pd.read_parquet(f, columns=["date"])
        out[f.rsplit("/", 1)[-1][:-8]] = (len(n), n["date"].min(), n["date"].max())
    return out


def main():
    core = pd.DataFrame(CORE_SOURCES)
    core["retrieved_on"] = TODAY
    agent = [pd.read_csv(f, dtype=str) for f in sorted(glob.glob(str(CATALOG / "sources_*_agent.csv")))]
    src = pd.concat([core] + agent, ignore_index=True)
    for c in COLS:
        if c not in src.columns:
            src[c] = pd.NA
    extra = [c for c in src.columns if c not in COLS]
    src = src[COLS + extra].drop_duplicates("source_id", keep="first")
    cnt = counts()
    for sid, (n, d0, d1) in cnt.items():
        m = src.source_id == sid
        src.loc[m, "records"] = n
        src.loc[m, "date_range"] = f"{d0}..{d1}"
    src.to_csv(CATALOG / "sources.csv", index=False)
    print(len(src), "sources")

    leads = []
    for f in sorted(glob.glob(str(CATALOG / "leads_*_agent.csv"))):
        d = pd.read_csv(f, dtype=str)
        d["found_by"] = f.rsplit("/", 1)[-1].replace("leads_", "").replace(".csv", "")
        leads.append(d)
    if leads:
        L = pd.concat(leads, ignore_index=True)
        if "type" not in L:
            L["type"] = pd.NA
        L["type"] = L["type"].fillna(L.get("fuel_class"))
        L["status"] = L.get("status", pd.Series(pd.NA, index=L.index))
        ingested_urls = " ".join(src["url"].dropna())
        L["status"] = L["status"].fillna("queued")
        L.loc[L["url"].fillna("").map(lambda u: bool(u) and u in ingested_urls), "status"] = "ingested"
        front = ["url", "type", "status", "notes"]
        L = L[front + [c for c in L.columns if c not in front]].drop_duplicates("url")
        L.to_csv(CATALOG / "leads.csv", index=False)
        print(len(L), "leads")
    papers = [pd.read_csv(f, dtype=str) for f in sorted(glob.glob(str(CATALOG / "papers_*_agent.csv")))]
    if papers:
        P = pd.concat(papers, ignore_index=True).drop_duplicates()
        P.to_csv(CATALOG / "papers.csv", index=False)
        print(len(P), "papers")


if __name__ == "__main__":
    main()
