"""Build data/normalized/sites.parquet: one row per unique observation location, with the grid
cells used by the covariate joins.

  site_key     rounded "lat,lon" (5 decimals) used to join observations to site-level covariates
  power_cell   NASA POWER MERRA-2 native cell (0.5 deg lat x 0.625 deg lon), "lat_lon" of center
  in_conus     inside the gridMET domain (CONUS, 49.4N to 25.07N, 124.77W to 67.06W)
  first_date / last_date  observation date range at the site (drives which years to fetch)
"""
import glob

import numpy as np
import pandas as pd

from common import BY_SOURCE, NORM


def site_key(lat, lon) -> pd.Series:
    return pd.Series(np.round(lat, 5)).astype(str) + "," + pd.Series(np.round(lon, 5)).astype(str)


def power_cell(lat, lon):
    plat = np.round(np.asarray(lat) / 0.5) * 0.5
    plon = np.round(np.asarray(lon) / 0.625) * 0.625
    return pd.Series(np.round(plat, 3)).astype(str) + "_" + pd.Series(np.round(plon, 4)).astype(str)


def build() -> pd.DataFrame:
    files = glob.glob(str(BY_SOURCE / "*.parquet")) + glob.glob(str(BY_SOURCE / "*" / "*.parquet"))
    parts = []
    for f in files:
        d = pd.read_parquet(f, columns=["source_id", "lat", "lon", "date", "country"])
        d = d.dropna(subset=["lat", "lon"])
        d["site_key"] = site_key(d["lat"].values, d["lon"].values).values
        parts.append(d.groupby("site_key").agg(lat=("lat", "first"), lon=("lon", "first"),
                                               first_date=("date", "min"), last_date=("date", "max"),
                                               n_obs=("date", "size"), country=("country", "first"),
                                               sources=("source_id", "first")).reset_index())
    s = pd.concat(parts)
    s = s.groupby("site_key").agg(lat=("lat", "first"), lon=("lon", "first"), first_date=("first_date", "min"),
                                  last_date=("last_date", "max"), n_obs=("n_obs", "sum"),
                                  country=("country", "first"),
                                  sources=("sources", lambda x: ",".join(sorted(set(x))))).reset_index()
    s = s[(s.lat.abs() <= 90) & (s.lon.abs() <= 180)]
    s["power_cell"] = power_cell(s["lat"].values, s["lon"].values).values
    s["in_conus"] = (s.lat <= 49.42) & (s.lat >= 25.06) & (s.lon >= -124.78) & (s.lon <= -67.05)
    s.to_parquet(NORM / "sites.parquet", index=False)
    print(len(s), "sites;", s.power_cell.nunique(), "POWER cells;", int(s.in_conus.sum()), "in CONUS")
    return s


if __name__ == "__main__":
    build()
