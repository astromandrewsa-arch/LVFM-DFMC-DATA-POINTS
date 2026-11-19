"""Normalize MADIS fuel-stick extracts (see fetch_madis_raws.py) to the observation schema.

- One row per (station, observation time). When the same station/time arrives from several
  providers (e.g. RAWS and MesoWest), the RAWS copy is kept and the other providers are listed in
  notes.
- fuel_type '10hr' / method 'fuel_stick': RAWS fuel moisture sensors are 10-hr (1/2 in) dowel
  sticks (Campbell CS505/CS506 or the older weighed-stick systems).
- The weather measured at the same station and time is written to
  covariates_by_source/madis_raws/<year>.parquet keyed by observation_id
  (cov_source = 'station_colocated').
Output is partitioned by year to keep every file under GitHub's 100 MB limit.

Usage: python normalize_madis_raws.py [--years 2024,2025]
"""
import argparse
import glob

import numpy as np
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "madis_raws"
PROVIDER_RANK = {"RAWS": 0, "MesoWest": 1, "HADS": 2}
K = 273.15


def normalize_year(year: str) -> int:
    files = sorted(glob.glob(str(raw_dir(SOURCE_ID) / "extracted" / year / "*.parquet")))
    parts = [pd.read_parquet(f) for f in files]
    parts = [p for p in parts if len(p)]
    if not parts:
        return 0
    df = pd.concat(parts, ignore_index=True)
    df["stationId"] = df["stationId"].astype(str).str.strip()
    df["dataProvider"] = df["dataProvider"].astype(str).str.strip()
    df = df[np.isfinite(df["observationTime"])]
    df["rank"] = df["dataProvider"].map(PROVIDER_RANK).fillna(9)
    others = (df.groupby(["stationId", "observationTime"])["dataProvider"]
                .agg(lambda s: ",".join(sorted(set(s)))))
    df = df.sort_values("rank").drop_duplicates(["stationId", "observationTime"], keep="first")
    df = df.join(others.rename("providers"), on=["stationId", "observationTime"])
    ts = pd.to_datetime(df["observationTime"], unit="s", utc=True)

    out = pd.DataFrame({
        "source_record_id": df["stationId"] + "@" + ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": ts.dt.date,
        "time": ts.dt.strftime("%H:%M"),
        "timezone": "UTC",
        "lat": df["latitude"].round(5),
        "lon": df["longitude"].round(5),
        "location_precision_m": 100.0,
        "country": "USA",
        "site_name": df["stationName"].astype(str).str.strip() + " [" + df["stationId"] + "]",
        "fuel_class": "dead",
        "fuel_type": "10hr",
        "species": pd.NA,
        "moisture_pct": df["fuelMoisture"],
        "method": "fuel_stick",
        "measured": True,
        "notes": ("provider=" + df["dataProvider"] + "; providers=" + df["providers"]
                  + "; stationType=" + df["stationType"].astype(str).str.strip()
                  + "; src=" + df["archive_url"].str.rsplit("/", n=1).str[-1]),
    })
    # MADIS rows come from US mesonets but a few stations sit outside the US (Canada, Mexico, Pacific).
    lat, lon = out["lat"], out["lon"]
    in_us = (((lat > 24) & (lat < 50) & (lon > -125) & (lon < -66)) | ((lat > 51) & (lon < -129))
             | ((lat > 18) & (lat < 23) & (lon > -161) & (lon < -154)) | ((lat > 17) & (lat < 19) & (lon > -68) & (lon < -64)))
    out.loc[~in_us, "country"] = pd.NA
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID, part=year)

    cov = pd.DataFrame({
        "observation_id": out["observation_id"].values,
        "cov_source": "station_colocated(MADIS)",
        "obs_temp_c": (df["temperature"] - K).values,
        "obs_dewpoint_c": (df["dewpoint"] - K).values,
        "obs_rh_pct": df["relHumidity"].values,
        "obs_wind_ms": df["windSpeed"].values,
        "obs_wind_dir_deg": df["windDir"].values,
        "obs_gust_ms": df["windGust"].values,
        "obs_precip_accum_mm": df["precipAccum"].values,
        "obs_solar_wm2": df["solarRadiation"].values,
        "obs_fuel_temp_c": (df["fuelTemperature"] - K).values,
        "obs_soil_moisture_pct": df["soilMoisturePercent"].values,
        "obs_soil_temp_c": (df["soilTemperature"] - K).values,
        "elevation_m": df["elevation"].values,
    })
    d = NORM / "covariates_by_source" / SOURCE_ID
    d.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(d / f"{year}.parquet", index=False, compression="zstd")
    return len(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="")
    a = ap.parse_args()
    years = a.years.split(",") if a.years else sorted(
        p.rsplit("/", 1)[-1] for p in glob.glob(str(raw_dir(SOURCE_ID) / "extracted" / "[12]*")))
    for y in years:
        print(y, normalize_year(y))
