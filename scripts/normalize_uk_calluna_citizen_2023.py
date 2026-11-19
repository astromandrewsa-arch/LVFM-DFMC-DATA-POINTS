"""Normalize EIDC 64d340d7 Calluna vulgaris citizen-science FMC survey (UK, 15 Apr-20 May 2023,
OGL-UK-3.0). 830 samples of live heather (c. 10 plants along a 20 m transect, combined).
FMC_1 (n=700, dried 80 C 48 h) and FMC_2 (n=130, dried 50 C to constant weight, samples also
used for micro-calorimetry) are both % of dry mass; exactly one is filled per sample, so one
row per sample. Date missing for 14 samples (kept, date NULL -> bad_date in QA), time missing
for 19. Time is local clock time (BST). Coordinates are volunteer-provided GPS, checked by the
authors against imagery. Canopy height -> notes; calorimetry metrics are not ingested.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "uk_calluna_citizen_2023"

if __name__ == "__main__":
    f = raw_dir(SOURCE_ID) / "eidc" / "data" / "calluna_fuel_moisture_survey.csv"
    df = pd.read_csv(f, encoding="latin1")
    assert (df["FMC_1"].notna() ^ df["FMC_2"].notna()).all()
    which = df["FMC_1"].notna().map({True: "FMC_1 (80C 48h)", False: "FMC_2 (50C to const. wt; calorimetry sample)"})
    fmt = lambda s: s.astype(object).where(s.notna(), "NA").astype(str)
    out = pd.DataFrame({
        "source_record_id": "row" + df.index.astype(str),
        "date": pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce"),
        "time": df["Time"].astype("string").str.slice(0, 5),
        "timezone": "Europe/London",
        "lat": df["Latitude"], "lon": df["Longitude"], "location_precision_m": 20,
        "country": "United Kingdom",
        "site_name": "citizen_transect_" + df.index.astype(str),
        "fuel_class": "live",
        "fuel_type": "shrub",
        "species": "Calluna vulgaris",
        "moisture_pct": df["FMC_1"].fillna(df["FMC_2"]),
        "method": "oven_dry",
        "measured": True,
        "notes": ("dry_weight_basis; " + which + "; canopy_height_cm=" + fmt(df["Height_(cm)"])
                  + "; composite of ~10 plants on 20 m transect; volunteer-collected"),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
