"""Fetch RAWS daily weather summaries (min/max temperature and RH, 24-h precipitation, max wind,
max solar radiation, VPD) from USFS FEMS for RAWS stations within MAX_KM of any observation
site. Used by join_weather.py as nearest-station weather for samples without co-located weather.

Public endpoints (no login):
  stations: POST https://fems.fs2c.usda.gov/api/climatology/graphql/  stationMetaData(returnAll:true)
  daily:    GET  https://fems.fs2c.usda.gov/api/climatology/download-wx-daily-summary/
            ?dataset=observation&startDate=..&endDate=..&dataFormat=csv&stationIds=<id>
License: US Government work (public domain).
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd

from common import NORM, download, raw_dir, session

SOURCE_ID = "fems_raws_daily"
GQL = "https://fems.fs2c.usda.gov/api/climatology/graphql/"
DL = ("https://fems.fs2c.usda.gov/api/climatology/download-wx-daily-summary/?dataset=observation"
      "&startDate=1960-01-01&endDate={end}&dataFormat=csv&stationIds={sid}")
Q = ("{ stationMetaData(returnAll: true) { _metadata { total_count } data { station_id fems_station_id "
     "wrcc_id state station_name latitude longitude elevation station_status } } }")
MAX_KM = 40


def haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * np.arcsin(np.sqrt(a))


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    sess = session()
    r = sess.post(GQL, json={"query": Q}, timeout=300)
    r.raise_for_status()
    st = pd.DataFrame(r.json()["data"]["stationMetaData"]["data"])
    st.to_csv(d / "stations.csv", index=False)
    sites = pd.read_parquet(NORM / "sites.parquet")
    sites = sites[sites["country"].fillna("USA").isin(["USA"])]
    need = set()
    for _, s in st.iterrows():
        dist = haversine_km(s.latitude, s.longitude, sites.lat.values, sites.lon.values)
        if (dist <= MAX_KM).any():
            need.add(int(s.station_id))
    print(len(st), "stations;", len(need), "within", MAX_KM, "km of a site")
    end = str(date.today())
    (d / "daily").mkdir(exist_ok=True)

    def one(sid):
        try:
            download(DL.format(end=end, sid=sid), d / "daily" / f"{sid}.csv", sess=sess, timeout=600)
        except Exception as e:
            print("ERR", sid, e)

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, sorted(need)))
    print("done")
