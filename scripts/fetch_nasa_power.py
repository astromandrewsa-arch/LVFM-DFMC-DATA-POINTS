"""Fetch NASA POWER daily point time series (1981-present) for every POWER cell that contains an
observation site (see sites.py). Raw CSVs go to data/raw/nasa_power/<cell>.csv (git-ignored).

NASA POWER: https://power.larc.nasa.gov  (MERRA-2 meteorology, CERES/GEWEX solar). Open data,
no restrictions; cite "NASA Langley Research Center POWER Project".
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import pandas as pd

from common import NORM, download, raw_dir, session

SOURCE_ID = "nasa_power"
PARAMS = "T2M,T2M_MAX,T2M_MIN,RH2M,T2MDEW,QV2M,PRECTOTCORR,WS2M,WS2M_MAX,WD2M,ALLSKY_SFC_SW_DWN,GWETTOP,GWETROOT,SNODP,PS"
URL = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters={p}&community=AG"
       "&longitude={lon}&latitude={lat}&start=19810101&end={end}&format=CSV&time-standard=LST")


def fetch(cell: str, out_dir, end: str, sess):
    lat, lon = cell.split("_")
    dest = out_dir / f"{cell}.csv"
    download(URL.format(p=PARAMS, lat=lat, lon=lon, end=end), dest, sess=sess, timeout=300)
    return cell


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    sites = pd.read_parquet(NORM / "sites.parquet")
    cells = sorted(sites["power_cell"].unique())
    out = raw_dir(SOURCE_ID)
    todo = [c for c in cells if not (out / f"{c}.csv").exists()]
    end = (date.today() - timedelta(days=10)).strftime("%Y%m%d")
    print(len(cells), "cells,", len(todo), "to fetch")
    sess = session()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(fetch, c, out, end, sess) for c in todo]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as e:
                print("ERR", e)
            if i % 100 == 0:
                print(i, "/", len(todo), flush=True)
    print("done")
