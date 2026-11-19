"""Fetch NOAA GHCN-Daily station records used as nearest-station weather (PRCP, TMAX, TMIN,
TAVG, SNWD) for observation sites:
  - non-US sites: the 3 nearest GHCN-D stations within 75 km;
  - US sites: same, but only where no RAWS station lies within 40 km (RAWS from FEMS preferred);
  - all GHCN-D stations in Zimbabwe (pilot region), regardless of sites.
Per-station CSVs: https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/<ID>.csv
License: NOAA data are public domain; some non-US stations are shared under WMO Resolution 40
terms that may limit commercial redistribution (flagged in sources.csv).
"""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from common import NORM, RAW, download, raw_dir, session
from fetch_fems_raws_daily import haversine_km

SOURCE_ID = "ghcnd"
STATIONS = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
ACCESS = "https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/{id}.csv"


def load_stations(path):
    rows = []
    for line in open(path, encoding="latin-1"):
        rows.append((line[0:11], float(line[12:20]), float(line[21:30]), float(line[31:37]), line[41:71].strip()))
    return pd.DataFrame(rows, columns=["id", "lat", "lon", "elev", "name"])


def nearest(st, lat, lon, k=3, km=75):
    box = st[(st.lat.between(lat - 1, lat + 1)) & (st.lon.between(lon - 1.5, lon + 1.5))]
    if box.empty:
        return []
    d = haversine_km(lat, lon, box.lat.values, box.lon.values)
    o = np.argsort(d)[:k]
    return [box.id.values[i] for i in o if d[i] <= km]


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    download(STATIONS, d / "ghcnd-stations.txt")
    st = load_stations(d / "ghcnd-stations.txt")
    sites = pd.read_parquet(NORM / "sites.parquet")
    raws_p = RAW / "fems_raws_daily" / "stations.csv"
    raws = pd.read_csv(raws_p) if raws_p.exists() else pd.DataFrame(columns=["latitude", "longitude"])
    need = set(st.loc[st.id.str.startswith("ZI"), "id"])
    us = sites["country"].fillna("USA") == "USA"
    # collapse near-identical sites to 0.05 deg to bound the search
    s = sites.assign(rl=sites.lat.round(2), rn=sites.lon.round(2), us=us).drop_duplicates(["rl", "rn"])
    for r in s.itertuples():
        if r.us and len(raws):
            if (haversine_km(r.lat, r.lon, raws.latitude.values, raws.longitude.values) <= 40).any():
                continue
        need.update(nearest(st, r.lat, r.lon))
    print(len(need), "GHCN-D stations to fetch")
    (d / "access").mkdir(exist_ok=True)
    sess = session()

    def one(i):
        try:
            download(ACCESS.format(id=i), d / "access" / f"{i}.csv", sess=sess, timeout=600)
        except Exception as e:
            print("ERR", i, e)

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, sorted(need)))
    print("done")
