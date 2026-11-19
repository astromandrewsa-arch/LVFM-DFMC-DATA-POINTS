"""Fetch the US National Fuel Moisture Database (NFMD) field samples from USFS FEMS
(Fire Environment Mapping System), which now hosts the full NFMD history.

Public endpoints (no login), as used by the FEMS web app's "Download Data > Field Sample":
  sites:   POST https://fems.fs2c.usda.gov/fuelmodel/apis/graphql   getSites(returnAll:true)
  samples: GET  https://fems.fs2c.usda.gov/fuelmodel/sample/download?...&filterByCategory=All
           (filterByCategory must be "All"; an empty value returns no rows)
Samples are pulled month by month into data/raw/fems_nfmd/samples/<YYYY-MM>.csv.
License: US Government work (public domain); data contributed by federal/state/local agencies.
"""
import json
import time
from datetime import date

from common import download, raw_dir, session

SOURCE_ID = "fems_nfmd"
GQL = "https://fems.fs2c.usda.gov/fuelmodel/apis/graphql"
DL = ("https://fems.fs2c.usda.gov/fuelmodel/sample/download?returnAll=true&responseFormat=csv&siteId=All"
      "&sampleId=&startDate={s}T00:00:00.000Z&endDate={e}T00:00:00.000Z&filterByFuelId=&filterByStatus=Submitted"
      "&filterByCategory=All&filterBySubCategory=&filterByMethod=&sortBy=fuel_type&sortOrder=asc")
SITE_Q = """query { getSites(returnAll: true) { pageInfo { total_count } sites {
  siteId siteName siteStatus active latitude longitude elevation slope aspect stateName stateId
  groupName areaName jurisdiction timeZone timeZoneOffset remarks siteStartDate } } }"""


def months(y0=1970):
    t = date.today()
    y, m = y0, 1
    while (y, m) <= (t.year, t.month):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        yield date(y, m, 1), date(ny, nm, 1)
        y, m = ny, nm


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    sess = session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (compatible; pyrome-fuel-moisture-harvest/0.1)"
    r = sess.post(GQL, json={"query": SITE_Q}, timeout=300)
    r.raise_for_status()
    (d / "sites.json").write_text(json.dumps(r.json()))
    print("sites:", r.json()["data"]["getSites"]["pageInfo"]["total_count"])
    (d / "samples").mkdir(exist_ok=True)
    this_month = date.today().replace(day=1)
    for s, e in months():
        dest = d / "samples" / f"{s:%Y-%m}.csv"
        if dest.exists() and s < this_month:
            continue
        download(DL.format(s=s, e=e), dest, sess=sess, overwrite=True, timeout=600)
        n = sum(1 for _ in open(dest)) - 1
        if n:
            print(s, n, flush=True)
        time.sleep(0.5)
