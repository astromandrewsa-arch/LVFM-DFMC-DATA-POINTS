"""Normalize Cumberland Plain flux tower daily CS505 fuel moisture, 2013 (figshare 26014618, CC BY 4.0).

One row per day: daily MINIMUM of a Campbell CS505 fuel moisture sensor (10-h pine dowel) at the
Cumberland Plain (EucFACE / AU-Cum) flux tower, Richmond NSW -> fuel_class dead, fuel_type 10hr,
method sensor, measured. The file only holds the daily minimum (no sub-daily series), so this is
the full published resolution. Daily VPD (kPa), T (C), RH (%), Precip (mm) -> covariates
(aggregation of T/RH/VPD not stated in the file).
Coordinates: OzFlux AU-Cum tower (-33.6153, 150.7236).
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "cumberland_cs505"

if __name__ == "__main__":
    src = raw_dir(SOURCE_ID) / "2015.RescodeDiostal.AFM.CUP.csv"
    d = pd.read_csv(src, skiprows=[1])
    print(len(d), "days")
    date = pd.to_datetime(d["Year"].astype(int).astype(str), format="%Y") + pd.to_timedelta(d["DoY"] - 1, unit="D")
    m = d["CS505"].notna()
    d, date = d[m].reset_index(drop=True), date[m].reset_index(drop=True)
    out = pd.DataFrame({
        "source_record_id": "AU-Cum@" + date.dt.strftime("%Y-%m-%d"),
        "date": date, "time": pd.NA, "timezone": "Australia/Sydney",
        "lat": -33.6153, "lon": 150.7236, "location_precision_m": 50,
        "country": "Australia", "site_name": "Cumberland Plain flux tower (AU-Cum), Richmond NSW",
        "fuel_class": "dead", "fuel_type": "10hr", "species": "CS505 10-h fuel moisture sensor (pine dowel)",
        "moisture_pct": d["CS505"], "method": "sensor", "measured": True, "qa_flag": pd.NA,
        "notes": "daily_minimum of CS505 sensor; Resco de Dios et al. 2015 AFM 203:64-73",
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "source_provided(flux tower daily values; aggregation not stated)",
        "vpd_daily_kpa": d["VPD"], "air_temp_daily_c": d["T"], "rh_daily_pct": d["RH"], "precip_daily_mm": d["Precip"],
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
