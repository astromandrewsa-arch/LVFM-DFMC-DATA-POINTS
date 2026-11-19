"""Normalize RDS-2021-0070 (Barber et al. 2021): Mazama Meadows grassland fuel moisture, WA.

120 grass plots destructively sampled on 22 Sep 2020 (morning and afternoon UAV flights), each
split into 'Live' (live vegetation), 'Top' (non-live vegetation > 1 ft) and 'Bottom' (rest of the
non-live vegetation); a few bags are 'Mixed' / 'Bottom/Top'. Moisture is recomputed from weights
as ((wet gross - wet tare) - (dry gross - dry tare)) / (dry gross - dry tare) * 100 (dry basis,
matches the source 'Fuel Moisture' column); the source value is kept in notes.
Top/Bottom are the remaining (cured) grass after live material was separated -> fuel_class dead,
fuel_type grass. 'Mixed' bags (live + dead together) are kept as dead grass with qa_flag
mixed_live_dead. Plot 54 was excluded by the authors (absent). Plot polygons (EPSG:3857
GeoPackage) -> centroid converted to WGS84; plots are ~1 m, GNSS/imagery-located -> 5 m precision.
Collector initials and lab-processing notes are not carried over (personal initials).
"""
import math

import pandas as pd
import pyogrio.raw
from shapely import wkb

from common import finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_mazama_grass_uav"
R = 6378137.0


def merc_to_wgs(x, y):
    return math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2), math.degrees(x / R)


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    meta, _, geom, fields = pyogrio.raw.read(find(d, "plot_locations_simple.gpkg"))
    ids = dict(zip(meta["fields"], fields))["ID"]
    plots = {}
    for pid, g in zip(ids, geom):
        cen = wkb.loads(bytes(g)).centroid
        plots[int(pid)] = merc_to_wgs(cen.x, cen.y)

    df = pd.read_csv(find(d, "*FuelMoistureSamples.csv"), encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["_row"] = range(len(df))
    n = lambda c: pd.to_numeric(df[c], errors="coerce")
    wet = n("Wet Gross Weight") - n("Wet Container Weight")
    dry = n("Dry Gross Weight") - n("Dry Container Weight")
    mp = (wet - dry) / dry * 100
    ok = mp.notna() & (dry > 0)
    print(len(df), "rows;", int((~ok).sum()), "dropped (bad weights)")
    df, mp = df[ok].copy(), mp[ok]
    st = df["Sample Type"].str.strip()
    live = st.eq("Live")
    mixed = st.isin(["Mixed"])
    xy = df["Plot Number"].astype(int).map(plots)
    t = pd.to_numeric(df["Time Collected"], errors="coerce")
    notecol = [c for c in df.columns if c.startswith("Notes")][0]
    srcnote = df[notecol].fillna("").astype(str)
    qa = pd.Series(pd.NA, index=df.index, dtype="string")
    qa[mixed] = "mixed_live_dead"
    qa[srcnote.str.contains("Contains live material", case=False)] = "mixed_live_dead"
    qa[srcnote.str.contains("Not sure which plot|difficult to make out|labeled as bottom", case=False)] = "src_label_uncertain"
    out = pd.DataFrame({
        "source_record_id": "plot" + df["Plot Number"].astype(str) + "|" + st + "|" + df["Sample Period"] + "#" + df["_row"].astype(str),
        "date": pd.to_datetime(df["Date Collected"], format="%m/%d/%Y", errors="coerce"),
        "time": t.map(lambda v: pd.NA if pd.isna(v) else f"{int(v) // 100:02d}:{int(v) % 100:02d}"),
        "timezone": "America/Los_Angeles",
        "lat": xy.str[0], "lon": xy.str[1], "location_precision_m": 5.0, "country": "USA",
        "site_name": "Mazama Meadows site C plot " + df["Plot Number"].astype(str) + " (near Olympia, WA)",
        "fuel_class": live.map({True: "live", False: "dead"}), "fuel_type": "grass", "species": pd.NA,
        "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": qa,
        "notes": ("gravimetric dry basis from net weights; whole-plot destructive clip; stratum=" + st
                  + " (Top=non-live >1 ft, Bottom=rest of non-live)" + "; period=" + df["Sample Period"]
                  + "; src_fuel_moisture=" + df["Fuel Moisture"].astype(str)),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    print("no plot coords:", int(out["lat"].isna().sum()))
    finalize(out, SOURCE_ID)
