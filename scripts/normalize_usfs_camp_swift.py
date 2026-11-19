"""Normalize RDS-2018-0044 (Camp Swift Fire Experiment 2014, Bastrop Co., Texas): fuel moisture.

FuelSamples.gdb tables FuelMoisturePlot1 / FuelMoisturePlot3: individual pre-fire moisture
samples collected outside burn blocks 1 and 3 within 30 min of ignition on 15 Jan 2014 (Project
Overview: all research burns on January 15, 2014). MoistureContent = (net wet - net dry) / net
dry * 100 (verified against the weights) = dry basis. Soil samples are not fuel and are skipped.
Grass categories (bluestem upper/lower layer, threeawn, broomweed) are dormant-season
standing grass -> fuel_class dead (source labels only 'Live forb' as live; others not stated)
with qa_flag 'live_dead_inferred'. Exact sample locations are not known (metadata) -> centre of
the dataset bounding box (blocks span ~300 m), location_approx.
Requires pyogrio (reads the ESRI FileGDB tables with GDAL's OpenFileGDB driver).
"""
import pandas as pd
import pyogrio.raw

from common import finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_camp_swift"
LAT, LON = (30.24809 + 30.245352) / 2, (-97.272806 + -97.270924) / 2
CAT = {
    "Bluestem: upper layer": ("dead", "grass", "bluestem (unspecified; 'Bluestem' in source)", "live_dead_inferred"),
    "Bluestem: lower layer": ("dead", "grass", "bluestem (unspecified; 'Bluestem' in source)", "live_dead_inferred"),
    "Threeawn": ("dead", "grass", "Aristida sp. (threeawn)", "live_dead_inferred"),
    "Broomweed": ("dead", "herb", "broomweed (unspecified)", "live_dead_inferred"),
    "Live forb": ("live", "herb", "forbs (unspecified)", None),
}

if __name__ == "__main__":
    gdb = find(raw_dir(SOURCE_ID), "FuelSamples.gdb")
    frames = []
    for layer, block in [("FuelMoisturePlot1", 1), ("FuelMoisturePlot3", 3)]:
        meta, *_, fields = pyogrio.raw.read(gdb, layer=layer, read_geometry=False)
        t = pd.DataFrame({n: v for n, v in zip(meta["fields"], fields)})
        t.columns = [c.rstrip("_") for c in t.columns]
        t = t.rename(columns={"Sample_Number": "SampleNumber", "GrossWetWt_": "GrossWetWt_g",
                              "MoistureContent": "MC"})
        t["block"] = block
        t["_row"] = range(len(t))
        frames.append(t)
    df = pd.concat(frames, ignore_index=True)
    df = df[df["SMDuffVegSoil"].isin(CAT)].copy()
    c = df["SMDuffVegSoil"].map(CAT)
    mp = pd.to_numeric(df["MC"], errors="coerce")
    calc = (df["NetWetWt_g"] - df["NetDryWt_g"]) / df["NetDryWt_g"] * 100
    qa = c.str[3].astype("string")
    bad = (calc - mp).abs() > 1
    qa[bad] = qa[bad].fillna("") + ";src_pct_mismatch"
    out = pd.DataFrame({
        "source_record_id": "block" + df["block"].astype(str) + "|" + df["SMDuffVegSoil"] + "|" + df["SampleNumber"].astype(str),
        "date": "2014-01-15", "time": pd.NA, "timezone": "America/Chicago",
        "lat": LAT, "lon": LON, "location_precision_m": 300.0, "country": "USA",
        "site_name": "Camp Swift burn block " + df["block"].astype(str) + " (Bastrop Co., TX)",
        "fuel_class": c.str[0], "fuel_type": c.str[1], "species": c.str[2],
        "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": qa,
        "notes": ("gravimetric dry basis; collected outside burn block within 30 min of ignition; category="
                  + df["SMDuffVegSoil"] + "; location_approx (sample locations not recorded)"),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
