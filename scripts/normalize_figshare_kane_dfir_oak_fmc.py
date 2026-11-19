"""Normalize figshare 20485665 (Kane, Kerhoulas & Goff 2022, CC-BY-4.0): Kneeland fuel moisture
project, Douglas-fir / Oregon white oak stands in NW California, May-Nov 2018.

1. 'Fuel Moisture Data.xlsx' sheet 'Data' (917 rows): seasonal samples of dead 1-h, 10-h, litter,
   fermentation and humus layers, live Douglas-fir new/old foliage, live oak foliage and live
   herbs, by stand condition (HE/T/I codes as in source) and plot. Moisture is computed here:
   (WetWtBag - BagWt - DryWt) / DryWt * 100. DryWt is a net weight (the companion oak sheet has
   dry weights below the bag weight, and source note values such as 69.90 reproduce exactly with
   this formula). Rows marked '*' ('*Wet wt taken with out bag') use WetWtBag as the net wet
   weight. Soil samples are skipped (not fuel).
2. 'OakPhysio&FMC.xlsx' sheet 'Sheet1': Oregon white oak foliar samples from the 25 Aug 2018
   physiology campaign (timestamped), (WB - Bag - Dry) / Dry * 100.
Location: no coordinates are published; the project is named 'Kneeland Fuel Moisture Project'
-> geocoded to Kneeland, Humboldt Co., CA (40.764, -123.928), location_precision_m 5000,
notes location_approx.
"""
import pandas as pd

from common import finalize, make_obs_id, raw_dir

SOURCE_ID = "figshare_kane_dfir_oak_fmc"
LAT, LON = 40.764, -123.928
TYPES = {  # Type -> fuel_class, fuel_type, species
    "DF1hr": ("dead", "1hr", "Pseudotsuga menziesii"), "DF10hr": ("dead", "10hr", "Pseudotsuga menziesii"),
    "DFLitter": ("dead", "litter", "Pseudotsuga menziesii"),
    "Oak1hr": ("dead", "1hr", "Quercus garryana"), "Oak10hr": ("dead", "10hr", "Quercus garryana"),
    "OakLitter": ("dead", "litter", "Quercus garryana"), "NewOakLitter": ("dead", "litter", "Quercus garryana"),
    "Ferm": ("dead", "duff", pd.NA), "Humus": ("dead", "duff", pd.NA),
    "DFLiveNew": ("live", "tree_foliage", "Pseudotsuga menziesii"),
    "DFLiveOld": ("live", "tree_foliage", "Pseudotsuga menziesii"),
    "OakLive": ("live", "tree_foliage", "Quercus garryana"), "LiveHerb": ("live", "herb", pd.NA),
}
LOC_NOTE = "; location_approx (geocoded 'Kneeland', no plot coordinates published)"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    df = pd.read_excel(d / "Fuel Moisture Data.xlsx", sheet_name="Data")
    df["_row"] = range(len(df))
    df["Type"] = df["Type"].astype(str).str.strip()
    df = df[df["Type"].isin(TYPES)].copy()
    note = df["Notes"].astype("string").str.strip().fillna("")
    star = note.str.startswith("*")
    wet = (df["WetWtBag"] - df["BagWt"]).where(~star, df["WetWtBag"])
    mp = (wet - df["DryWt"]) / df["DryWt"] * 100
    ok = mp.notna() & (df["DryWt"] > 0)
    df, mp, note, star = df[ok], mp[ok], note[ok], star[ok]
    t = df["Type"].map(TYPES)
    qa = pd.Series(pd.NA, index=df.index, dtype="string")
    qa[note.str.lower().isin(["bo", "wo"])] = "src_note_code_unexplained"
    qa[mp < 0] = "negative_moisture"
    a = pd.DataFrame({
        "source_record_id": "fmd#" + df["_row"].astype(str),
        "date": pd.to_datetime(df["Date"], errors="coerce"), "time": pd.NA, "timezone": "America/Los_Angeles",
        "lat": LAT, "lon": LON, "location_precision_m": 5000.0, "country": "USA",
        "site_name": "Kneeland plot " + df["Plot"].astype(str) + " condition " + df["Condition"].astype(str).str.strip() + " (Humboldt Co., CA)",
        "fuel_class": t.str[0], "fuel_type": t.str[1], "species": t.str[2],
        "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": qa,
        "notes": ("gravimetric dry basis computed from bag/wet/dry weights; type=" + df["Type"]
                  + "; sample_period=" + df["Sample_Period"].astype(str)
                  + "; stand_condition=" + df["Condition"].astype(str).str.strip()
                  + star.map({True: "; wet weight recorded without bag", False: ""})
                  + note.map(lambda s: f"; src_note={s}" if s else "") + LOC_NOTE),
    })
    a["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in a["source_record_id"]]

    o = pd.read_excel(d / "OakPhysio&FMC.xlsx", sheet_name="Sheet1")
    o["_row"] = range(len(o))
    omp = (o["WB"] - o["Bag"] - o["Dry"]) / o["Dry"] * 100
    o, omp = o[omp.notna()], omp[omp.notna()]
    ts = pd.to_datetime(o["Date/Time"], errors="coerce")
    b = pd.DataFrame({
        "source_record_id": "oakphysio#" + o["_row"].astype(str) + "|" + o["Plot_Tree"].astype(str),
        "date": ts.dt.normalize(), "time": ts.dt.strftime("%H:%M"), "timezone": "America/Los_Angeles",
        "lat": LAT, "lon": LON, "location_precision_m": 5000.0, "country": "USA",
        "site_name": "Kneeland plot " + o["Plot"].astype(str) + " (Humboldt Co., CA)",
        "fuel_class": "live", "fuel_type": "tree_foliage", "species": "Quercus garryana",
        "moisture_pct": omp, "method": "oven_dry", "measured": True,
        "notes": ("oak foliar moisture, dry basis from bag/wet/dry weights; physiology campaign; tree="
                  + o["Plot_Tree"].astype(str) + "; condition=" + o["Condition"].astype(str)
                  + "; treatment=" + o["Treatment"].astype(str) + LOC_NOTE),
    })
    b["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in b["source_record_id"]]
    out = pd.concat([a, b], ignore_index=True)
    print("fuel moisture data", len(a), "oak physio", len(b))
    finalize(out, SOURCE_ID)
