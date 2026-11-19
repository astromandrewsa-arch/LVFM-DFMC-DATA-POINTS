"""Normalize FEMS NFDRS 2016 daily summaries (fuel model Y) into the ESTIMATES table
(data/normalized/estimates_by_source/fems_nfdrs/<year>.parquet; measured=False).
One row per station-day per fuel class: 1hr/10hr/100hr/1000hr (daily minimum, dead), herb and
woody (live). Rows with no value are dropped.
"""
import glob

import pandas as pd

from common import RAW, finalize, make_obs_id

SOURCE_ID = "fems_nfdrs"
COLS = {"1HrFM": ("dead", "1hr"), "10HrFM": ("dead", "10hr"), "100HrFM": ("dead", "100hr"),
        "1000HrFM": ("dead", "1000hr"), "HerbFM": ("live", "herb"), "WoodyFM": ("live", "shrub")}

def run_chunk(files, st, chunk_no):
    parts = []
    for f in files:
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        d = d.dropna(subset=list(COLS), how="all")
        if d.empty:
            continue
        long = d.melt(id_vars=["StationName", "ObservationTime", "StationId", "NFDRType"],
                      value_vars=list(COLS), var_name="var", value_name="moisture_pct").dropna(subset=["moisture_pct"])
        parts.append(long)
    if not parts:
        return
    df = pd.concat(parts, ignore_index=True)
    sid = df["StationId"].astype(int)
    df["fuel_class"] = df["var"].map(lambda v: COLS[v][0])
    df["fuel_type"] = df["var"].map(lambda v: COLS[v][1])
    out = pd.DataFrame({
        "source_record_id": sid.astype(str) + "@" + df["ObservationTime"].astype(str) + "@" + df["var"],
        "date": pd.to_datetime(df["ObservationTime"], errors="coerce"),
        "timezone": "local",
        "lat": sid.map(st["latitude"]), "lon": sid.map(st["longitude"]),
        "location_precision_m": 100.0, "country": "USA",
        "site_name": df["StationName"].astype(str) + " [RAWS " + sid.astype(str) + "]",
        "fuel_class": df["fuel_class"], "fuel_type": df["fuel_type"],
        "moisture_pct": df["moisture_pct"],
        "method": "other", "measured": False,
        "notes": "NFDRS2016 fuel model Y daily summary (dead classes = daily minimum); NFDRType=" + df["NFDRType"].astype(str),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    out["year"] = out["date"].dt.year
    for y, g in out.groupby("year"):
        finalize(g.drop(columns="year"), SOURCE_ID, estimates=True, part=f"{int(y)}_{chunk_no:03d}")


if __name__ == "__main__":
    st = pd.read_csv(RAW / "fems_raws_daily" / "stations.csv").set_index("station_id")
    files = sorted(glob.glob(str(RAW / SOURCE_ID / "daily" / "*.csv")))
    for i in range(0, len(files), 150):
        run_chunk(files[i:i + 150], st, i // 150)
