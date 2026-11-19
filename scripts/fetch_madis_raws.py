"""Fetch measured fuel-stick moisture (RAWS 10-hr sticks and other mesonet fuel sensors) with
co-located weather from the NOAA MADIS public archive (LDAD mesonet netCDF, 2001-present).

Each hourly file is ~20-30 MB and covers every US mesonet; keeping them is impractical, so for
each file we stream it, keep only records with a valid fuelMoisture value (plus the weather
measured at the same station and time) and write a small parquet to
data/raw/madis_raws/extracted/<YYYY>/<YYYYMMDD_HH>.parquet. The source file can be re-downloaded
from the archive URL recorded in each row.

Usage: python fetch_madis_raws.py --hours 21 --start 2001-01-01 --end 2026-11-18 --workers 6
"""
from __future__ import annotations

import argparse
import gzip
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, timedelta

import netCDF4
import numpy as np
import pandas as pd

from common import download, raw_dir, session

SOURCE_ID = "madis_raws"
BASE = "https://madis-data.ncep.noaa.gov/madisPublic1/data/archive/{y}/{m}/{d}/LDAD/mesonet/netCDF/{y}{m}{d}_{h}00.gz"

STR_VARS = ["stationId", "stationName", "dataProvider", "stationType", "homeWFO"]
NUM_VARS = ["latitude", "longitude", "elevation", "observationTime", "fuelMoisture", "fuelTemperature",
            "temperature", "dewpoint", "relHumidity", "windSpeed", "windDir", "windGust",
            "precipAccum", "timeSinceLastPcp", "solarRadiation", "soilMoisture", "soilMoisturePercent",
            "soilTemperature", "restrictedDataLevel"]


def _arr(ds, v, idx):
    if v not in ds.variables:
        return np.full(len(idx), np.nan)
    a = ds[v][:]  # full read of a 1-D numeric var is fast
    a = np.ma.filled(a.astype("float64"), np.nan)[idx]
    a[(a <= -9999) | (a > 1e30)] = np.nan
    return a


def extract(day: date, hour: int, out_root) -> tuple[str, int]:
    y, m, d, h = f"{day:%Y}", f"{day:%m}", f"{day:%d}", f"{hour:02d}"
    out = out_root / y / f"{y}{m}{d}_{h}.parquet"
    if out.exists():
        return str(out), -1
    url = BASE.format(y=y, m=m, d=d, h=h)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = session().get(url, timeout=180)
        r.raise_for_status()
    except Exception as e:  # missing hour in archive
        if getattr(getattr(e, "response", None), "status_code", None) == 404:
            pd.DataFrame().to_parquet(out)
        return f"{url} ERR {e}", 0
    ds = netCDF4.Dataset("mem", memory=gzip.decompress(r.content))
    if "fuelMoisture" not in ds.variables:
        pd.DataFrame().to_parquet(out)
        return url, 0
    fm = np.ma.filled(ds["fuelMoisture"][:].astype("float64"), np.nan)
    idx = np.where(np.isfinite(fm) & (fm > -9999) & (fm < 1e30))[0]
    rec = {}
    lo, hi = (int(idx.min()), int(idx.max()) + 1) if len(idx) else (0, 0)
    for v in STR_VARS:
        if v in ds.variables:
            block = ds[v][lo:hi]  # contiguous slice covering only the fuel-moisture rows
            rec[v] = netCDF4.chartostring(block, encoding="latin-1")[idx - lo]
    for v in NUM_VARS:
        rec[v] = _arr(ds, v, idx)
    ds.close()
    df = pd.DataFrame(rec)
    df["archive_url"] = url
    df.to_parquet(out, index=False)
    return url, len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", default="21")
    ap.add_argument("--start", default="2001-01-01")
    ap.add_argument("--end", default=str(date.today() - timedelta(days=2)))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--reverse", action="store_true", help="newest first")
    a = ap.parse_args()
    out_root = raw_dir(SOURCE_ID) / "extracted"
    out_root.mkdir(parents=True, exist_ok=True)
    s, e = date.fromisoformat(a.start), date.fromisoformat(a.end)
    days = [s + timedelta(n) for n in range((e - s).days + 1)]
    if a.reverse:
        days = days[::-1]
    jobs = [(dd, int(h)) for dd in days for h in a.hours.split(",")]
    done = total = 0
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(extract, dd, h, out_root) for dd, h in jobs]
        for f in as_completed(futs):
            try:
                msg, n = f.result()
            except Exception as err:
                msg, n = f"ERR {err}", 0
            done += 1
            total += max(n, 0)
            if done % 50 == 0 or "ERR" in msg:
                print(f"{done}/{len(jobs)} rows_this_run={total:,} last={msg}", flush=True)
    print("finished", done, total)


if __name__ == "__main__":
    main()
