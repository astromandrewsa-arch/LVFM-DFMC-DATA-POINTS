"""Normalize RDS-2015-0005 (Wade 2015): fuel moisture immediately before ignition in a young
loblolly pine plantation (Kraft study), Jones County, Georgia, March 1983.

FBSD_fuel_moisture.csv: one row per sample; MC% = (wet - dry) / dry * 100, oven 100 C to
constant weight (user guide). MC% is given as an integer, so it is recomputed from the weights
(dry basis). Fuel types (user guide): HERBS = 'primarily bluestems' (dormant-season standing
grass in March; live/dead not stated -> dead grass + qa live_dead_unspecified), hardwood L =
hardwood litter, LOJA = Lonicera japonica (live, semi-evergreen vine -> live 'other').
Location: metadata gives a single point (33.05, -83.63) for the plantation -> plots within
~1 km, location_approx. Two-digit years ('3/9/83') = 1983.
"""
import pandas as pd

from common import finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_ga_loblolly_rx"
FT = {"HERBS": ("dead", "grass", "primarily bluestems (Andropogon/Schizachyrium)", "live_dead_unspecified"),
      "hardwood L": ("dead", "litter", "hardwood litter", None),
      "LOJA": ("live", "other", "Lonicera japonica", None)}

if __name__ == "__main__":
    df = pd.read_csv(find(raw_dir(SOURCE_ID), "FBSD_fuel_moisture.csv"), encoding="latin-1", skiprows=1)
    df.columns = [c.strip() for c in df.columns]
    df["_row"] = range(len(df))
    df["Fuel Type"] = df["Fuel Type"].str.strip()
    m = df["Fuel Type"].map(FT)
    assert m.notna().all(), df.loc[m.isna(), "Fuel Type"].unique()
    w, dr = pd.to_numeric(df["wet weight"], errors="coerce"), pd.to_numeric(df["Dry weight"], errors="coerce")
    mp = (w - dr) / dr * 100
    t = pd.to_numeric(df["Time"], errors="coerce")
    out = pd.DataFrame({
        "source_record_id": df["Plot"].astype(str) + "|" + df["Fuel Type"] + "|" + df["Sample #"].astype(str) + "#" + df["_row"].astype(str),
        "date": pd.to_datetime(df["Date"], format="%m/%d/%y", errors="coerce"),
        "time": t.map(lambda v: pd.NA if pd.isna(v) else f"{int(v) // 100:02d}:{int(v) % 100:02d}"),
        "timezone": "America/New_York",
        "lat": 33.05, "lon": -83.63, "location_precision_m": 1000.0, "country": "USA",
        "site_name": "Kraft loblolly plantation plot " + df["Plot"].astype(str) + " (Jones Co., GA)",
        "fuel_class": m.str[0], "fuel_type": m.str[1], "species": m.str[2],
        "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": m.str[3],
        "notes": ("sampled immediately before ignition; dry basis recomputed from weights; src_MC%="
                  + df["MC%"].astype(str) + "; plot_type=" + df["Plot Type"].astype(str)
                  + "; location_approx (single study point in metadata)"),
    })
    out = out[out["moisture_pct"].notna() & out["date"].notna()]
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
