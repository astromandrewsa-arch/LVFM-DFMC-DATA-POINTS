"""Fetch gridMET daily (Abatzoglou 2013; 1/24 deg, CONUS, 1979-present) at every CONUS
observation site (sites.py).

Point queries against the THREDDS aggregations take minutes per variable per point, so instead
each yearly file https://www.northwestknowledge.net/metdata/data/<var>_<year>.nc (~130 MB) is
downloaded once, sampled at all site cells, and deleted. Extracts are written to
data/raw/gridmet/extracted/<var>_<year>.parquet (site_key, date, value) — git-ignored and
recreatable. fm100 / fm1000 are model outputs and are treated as covariates/estimates only.

License: gridMET is public domain / CC0 (University of Idaho / Climatology Lab).
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date

import netCDF4
import numpy as np
import pandas as pd

from common import NORM, download, raw_dir, session

SOURCE_ID = "gridmet"
VARS = ["pr", "tmmx", "tmmn", "rmax", "rmin", "vs", "th", "srad", "vpd", "fm100", "fm1000"]
URL = "https://www.northwestknowledge.net/metdata/data/{v}_{y}.nc"


def extract(v: str, y: int, sites: pd.DataFrame, root):
    out = root / "extracted" / f"{v}_{y}.parquet"
    if out.exists():
        return v, y, -1
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = root / f"{v}_{y}.nc"
    download(URL.format(v=v, y=y), tmp, sess=session(), timeout=900)
    try:
        ds = netCDF4.Dataset(tmp)
        lat = ds["lat"][:]
        lon = ds["lon"][:]
        tname = [d for d in ds.dimensions if d not in ("lat", "lon", "crs")][0]
        days = netCDF4.num2date(ds[tname][:], ds[tname].units, only_use_cftime_datetimes=False)
        var = [k for k in ds.variables if k not in ("lat", "lon", "crs", tname)][0]
        x = ds[var]
        dims = x.dimensions
        iy = np.abs(lat[None, :] - sites["lat"].values[:, None]).argmin(1)
        ix = np.abs(lon[None, :] - sites["lon"].values[:, None]).argmin(1)
        x.set_auto_maskandscale(False)
        arr = x[:]
        sf = float(getattr(x, "scale_factor", 1.0))
        off = float(getattr(x, "add_offset", 0.0))
        fill = getattr(x, "_FillValue", None)
        order = [dims.index(tname), dims.index("lat"), dims.index("lon")]
        arr = np.transpose(arr, order)
        vals = arr[:, iy, ix].astype("float64")  # (time, site)
        if fill is not None:
            vals[vals == fill] = np.nan
        vals = vals * sf + off
        units = getattr(x, "units", "")
        ds.close()
    finally:
        os.remove(tmp)
    df = pd.DataFrame(vals, columns=sites["site_key"].values)
    df["date"] = [pd.Timestamp(d.year, d.month, d.day) for d in days]
    df = df.melt(id_vars="date", var_name="site_key", value_name=v)
    df.attrs["units"] = units
    df.to_parquet(out, index=False, compression="zstd")
    return v, y, len(df)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--years", default=f"1979-{date.today().year}")
    a = ap.parse_args()
    y0, y1 = map(int, a.years.split("-"))
    sites = pd.read_parquet(NORM / "sites.parquet")
    sites = sites[sites.in_conus].reset_index(drop=True)
    root = raw_dir(SOURCE_ID)
    jobs = [(v, y) for y in range(y1, y0 - 1, -1) for v in VARS]
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {ex.submit(extract, v, y, sites, root): (v, y) for v, y in jobs}
        for f in as_completed(futs):
            try:
                print(*f.result(), flush=True)
            except Exception as e:
                print("ERR", futs[f], e, flush=True)
