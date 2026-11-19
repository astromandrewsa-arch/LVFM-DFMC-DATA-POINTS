"""Normalize Zenodo 12732295 (Kranz et al. 2024, Saxony, Germany, CC-BY-4.0).

Two kinds of rows, one source:
  1. FMC_insitu/*.csv - destructive (gravimetric) samples, 2022-04..2023-09, 4 sites:
     DFMC_1h (litter: dead leaves, needles, twigs < 0.6 cm) -> dead/1hr
     DFMC_10h (0.6-2.54 cm surface wood) -> dead/10hr, DFMC_100h (2.54-7.5 cm) -> dead/100hr
     beech/oak/spruce (leaves or needles + small twigs) -> live/tree_foliage; shrub -> live/shrub;
     grass -> live/grass. One row per sample. The readme gives "FMC [%]" without stating the
     basis; live values up to 485 % imply dry basis for live fuel, but it is not stated, so rows
     carry "basis_unclear (likely dry weight)".
  2. FWS_30min/*.csv - FMCSTICK, 10-h fuel moisture stick sensor at each fire weather station,
     30-min logger values, 2023-01..2023-12 -> dead/10hr, method fuel_stick, measured True.
     Co-measured station weather (TAIR, RH, WS, PREC, PBC, TFUEL, SWC) -> covariates file.

Timestamps: the source does not state the time zone. The FWI file uses 13:00 UTC, which
suggests UTC logger time, and in-situ sampling times look like local clock times; both are
recorded with timezone "unspecified" and a note. Coordinates from stations.csv (4 decimals).
"""
import glob

import numpy as np
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "saxony_fmc_sticks"
FUEL = {
    "DFMC_1h": ("dead", "1hr", None, "1-h: litter (dead leaves, needles, twigs <0.6 cm)"),
    "DFMC_10h": ("dead", "10hr", None, "10-h: surface wood 0.6-2.54 cm"),
    "DFMC_100h": ("dead", "100hr", None, "100-h: surface wood 2.54-7.5 cm"),
    "beech": ("live", "tree_foliage", "Fagus sylvatica", "leaves, small twigs"),
    "oak": ("live", "tree_foliage", "Quercus sp.", "leaves, small twigs"),
    "spruce": ("live", "tree_foliage", "Picea abies", "needles, small twigs"),
    "shrub": ("live", "shrub", None, "leaves, small twigs"),
    "grass": ("live", "grass", None, "leaves, grasses"),
}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID) / "extracted"
    st = pd.read_csv(d / "stations.csv", sep=";", encoding="latin1").set_index("site")

    rows = []
    for f in sorted(glob.glob(str(d / "FMC_insitu" / "*.csv"))):
        site = f.split("/")[-1].split("_")[0]
        x = pd.read_csv(f, index_col=0)
        x["site"] = site
        x["rid"] = x.index.astype(str)
        rows.append(x)
    ins = pd.concat(rows, ignore_index=True)
    fu = ins["fuel"].map(FUEL)
    assert fu.notna().all(), set(ins.loc[fu.isna(), "fuel"])
    a = pd.DataFrame({
        "source_record_id": "insitu|" + ins["site"] + "|" + ins["rid"],
        "date": pd.to_datetime(ins["date"]),
        "time": ins["time"].astype(str).str.slice(0, 5),
        "timezone": "unspecified",
        "lat": ins["site"].map(st["lat"]), "lon": ins["site"].map(st["lon"]),
        "location_precision_m": 100,
        "country": "Germany",
        "site_name": ins["site"] + " " + ins["site"].map(st["long_name"]),
        "fuel_class": fu.map(lambda v: v[0]),
        "fuel_type": fu.map(lambda v: v[1]),
        "species": fu.map(lambda v: v[2]),
        "moisture_pct": ins["FMC"],
        "method": "oven_dry",
        "measured": True,
        "notes": ("destructive sample; " + fu.map(lambda v: v[3]) + "; src_fuel=" + ins["fuel"]
                  + "; basis_unclear (likely dry weight); time zone not stated (likely local clock time)"),
    })

    rows, covs = [], []
    for f in sorted(glob.glob(str(d / "FWS_30min" / "*.csv"))):
        site = f.split("/")[-1].split("_")[0]
        x = pd.read_csv(f)
        x = x[x["FMCSTICK"].notna()].copy()
        dt = pd.to_datetime(x["datetime"])
        b = pd.DataFrame({
            "source_record_id": "stick|" + site + "|" + x["datetime"],
            "date": dt.dt.normalize(),
            "time": dt.dt.strftime("%H:%M"),
            "timezone": "unspecified",
            "lat": st.loc[site, "lat"], "lon": st.loc[site, "lon"], "location_precision_m": 100,
            "country": "Germany",
            "site_name": site + " " + st.loc[site, "long_name"],
            "fuel_class": "dead",
            "fuel_type": "10hr",
            "species": pd.NA,
            "moisture_pct": x["FMCSTICK"],
            "method": "fuel_stick",
            "measured": True,
            "notes": ("10-h fuel moisture stick sensor at fire weather station, 30-min logger value; "
                      "time zone not stated (likely UTC, readme FWI uses 13:00 UTC)"),
        })
        rows.append(b)
        g = lambda c: pd.to_numeric(x[c], errors="coerce").values if c in x else np.nan
        covs.append(pd.DataFrame({
            "source_record_id": b["source_record_id"].values,
            "cov_source": f"saxony_fmc_sticks: co-located fire weather station {site} (30-min)",
            "air_temp_c": g("TAIR"), "rh_pct": g("RH"), "wind_ms": g("WS"), "wind_dir_deg": g("WD"),
            "precip_30min_mm": g("PREC"), "throughfall_30min_mm": g("PBC"),
            "fuel_stick_temp_c": g("TFUEL"), "par_umol_m2_s": g("PAR"),
            "soil_water_1_pct": g("SWC1") * 100 if "SWC1" in x else np.nan,
            "soil_water_2_pct": g("SWC2") * 100 if "SWC2" in x else np.nan,
        }))
    out = pd.concat([a] + rows, ignore_index=True)
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)

    cov = pd.concat(covs, ignore_index=True)
    cov = cov.merge(out[["source_record_id", "observation_id"]], on="source_record_id").drop(columns="source_record_id")
    wx = [c for c in cov.columns if c not in ("observation_id", "cov_source")]
    cov = cov.dropna(subset=wx, how="all")
    cov = cov[["observation_id", "cov_source"] + wx]
    (NORM / "covariates_by_source").mkdir(parents=True, exist_ok=True)
    cov.to_parquet(NORM / "covariates_by_source" / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
