"""Normalize NFMD field samples from FEMS (fetch_fems_nfmd.py) to the observation schema.

- Coordinates, elevation, slope, aspect come from the FEMS site table (sites.json); NFMD sites
  are sampling areas, so location_precision_m = 500.
- Sample timestamps are stored as local midnight rendered in US Central time (all values are
  05:00Z or 06:00Z), so the sampling date is the America/Chicago calendar date; time is unknown.
- Category Dead -> fuel_class dead (1-/10-/100-/1000-Hour, Duff, Litter, other dead fuels);
  Tree/Shrub/Grass/Forb -> live, with Fuel Type as the species/common name.
Values are oven-dry gravimetric moisture (% dry weight), sample averages over sub-samples.
"""
import glob
import json

import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "fems_nfmd"
DEAD_MAP = {"1-hour": "1hr", "10-hour": "10hr", "100-hour": "100hr", "1000-hour": "1000hr",
            "duff": "duff", "litter": "litter"}
LIVE_MAP = {"tree": "tree_foliage", "shrub": "shrub", "grass": "grass", "forb": "herb"}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    sites = pd.DataFrame(json.loads((d / "sites.json").read_text())["data"]["getSites"]["sites"])
    sites = sites.rename(columns={"siteId": "SiteId"})
    files = sorted(glob.glob(str(d / "samples" / "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
    df.columns = ["sample_id", "datetime", "site_name", "SiteId", "fuel_type_raw", "category",
                  "sub_category", "method_raw", "value", "status"]
    df = df.drop_duplicates("sample_id")
    print(len(df), "samples")
    df["SiteId"] = pd.to_numeric(df["SiteId"], errors="coerce")
    df = df.merge(sites, on="SiteId", how="left")
    ts = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    print("UTC hours:", ts.dt.hour.value_counts().head(5).to_dict())
    local_date = ts.dt.tz_convert("America/Chicago").dt.date

    cat = df["category"].str.strip().str.lower()
    ftr = df["fuel_type_raw"].str.strip()
    fuel_class = cat.map(lambda c: "dead" if c == "dead" else ("live" if c in LIVE_MAP else pd.NA))
    fuel_type = ftr.str.lower().map(DEAD_MAP)
    fuel_type = fuel_type.where(fuel_class != "dead", fuel_type.fillna("dead_other"))
    fuel_type = fuel_type.where(fuel_class != "live", cat.map(LIVE_MAP))
    species = ftr.where(fuel_class == "live", ftr.where(~ftr.str.lower().isin(DEAD_MAP)))

    notes = ("category=" + df["category"].fillna("") + "; state=" + df["stateName"].fillna("")
             + "; gacc_area=" + df["areaName"].fillna("") + "; group=" + df["groupName"].fillna("")
             + "; site_elev_ft=" + df["elevation"].astype(str) + "; status=" + df["status"].fillna(""))
    sub = df["sub_category"].fillna("")
    notes = notes.where(sub == "", notes + "; sub_category=" + sub)
    meth = df["method_raw"].fillna("")
    notes = notes.where(meth == "", notes + "; method=" + meth)

    out = pd.DataFrame({
        "source_record_id": df["sample_id"],
        "date": local_date,
        "time": pd.NA,
        "timezone": df["timeZone"],
        "lat": df["latitude"],
        "lon": df["longitude"],
        "location_precision_m": 500.0,
        "country": "USA",
        "site_name": df["site_name"].astype(str) + " [FEMS " + df["SiteId"].astype("Int64").astype(str) + "]",
        "fuel_class": fuel_class,
        "fuel_type": fuel_type,
        "species": species,
        "moisture_pct": pd.to_numeric(df["value"], errors="coerce"),
        "method": "oven_dry",
        "measured": True,
        "notes": notes,
    })
    out.loc[out["lat"].isna(), "qa_flag"] = "site_not_found"
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)

    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "fems_site_metadata",
        "elevation_m": pd.to_numeric(df["elevation"], errors="coerce") * 0.3048,
        "slope_pct": pd.to_numeric(df["slope"], errors="coerce"),
        "aspect": df["aspect"].astype("string"),
    })
    (NORM / "covariates_by_source").mkdir(exist_ok=True)
    cov.to_parquet(NORM / "covariates_by_source" / f"{SOURCE_ID}.parquet", index=False)
