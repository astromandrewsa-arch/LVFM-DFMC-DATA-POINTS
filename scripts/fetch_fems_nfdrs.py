"""Fetch NFDRS 2016 daily summaries (modeled 1/10/100/1000-hr dead, herbaceous and woody live fuel
moisture; daily minima for dead classes) for every RAWS station from USFS FEMS.
These are MODEL OUTPUTS (Nelson dead fuel moisture model + GSI live fuel model): they go to the
estimates table only, never to measured labels.
Endpoint (public): https://fems.fs2c.usda.gov/api/climatology/download-nfdr-daily-summary/
License: US Government work (public domain).
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd

from common import RAW, download, raw_dir, session

SOURCE_ID = "fems_nfdrs"
DL = ("https://fems.fs2c.usda.gov/api/climatology/download-nfdr-daily-summary/?dataset=observation"
      "&startDate=1990-01-01&endDate={end}&dataFormat=csv&stationIds={sid}&fuelModels=Y")

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID) / "daily"
    d.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(RAW / "fems_raws_daily" / "stations.csv")
    sess = session()
    end = str(date.today())

    def one(sid):
        try:
            download(DL.format(end=end, sid=sid), d / f"{sid}.csv", sess=sess, timeout=600)
        except Exception as e:
            print("ERR", sid, e)

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, st["station_id"].astype(int).tolist()))
    print("done")
