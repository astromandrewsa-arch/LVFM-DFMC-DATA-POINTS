"""Normalize the SPIF Catalonia LFMC database (lfmc.sqlite from spif-ctfc/LFMC v.1.0.0,
Zenodo 4694854) to the observation schema.

One row per sample (table lfmc). LFMC in the database is on a dry-weight basis
((FreshMass - DryMass) / DryMass * 100; verified to 1e-13 on all rows with both masses).
Samples with LFMC NULL (481; fresh or dry mass missing) are skipped, not imputed.
ManualOutlier / AdditiveOutlier flags (Gabriel et al. 2021) are carried into qa_flag.
Dates are stored as days since 1970-01-01. Sampling time is not recorded.

Coordinates come from the sites table (WGS84 decimal degrees, stored as text with decimal comma and a trailing NBSP). Exception: site 2 "Puig Cabirol"
(locality Montmell) carries the exact coordinates of site 10 "Montperdut" (Port de la Selva,
~180 km away) in the sqlite - a copy error. For it we use the Montmell coordinates published
for the same site in Globe-LFMC 2.0 (41.335147, 1.490989), noted in notes.
"""
import sqlite3

import pandas as pd

from common import finalize, make_obs_id, raw_dir

SOURCE_ID = "spif_catalonia"
FIX = {2: (41.335147, 1.490989, "coords_fixed: sqlite coords duplicate Montperdut; used "
           "Montmell coords for this site from Globe-LFMC 2.0")}

if __name__ == "__main__":
    con = sqlite3.connect(raw_dir(SOURCE_ID) / "lfmc.sqlite")
    q = """select l.*, ss.SamplingSiteCode, sp.SpeciesName, sp.SpeciesCAT,
                  s.SamplingSiteName, s.LocalityName, s.Longitude, s.Latitude
           from lfmc l join sites_species ss on l.SiteSpCode = ss.SiteSpCode
           join species sp on ss.SpeciesCode = sp.SpeciesCode
           join sites s on ss.SamplingSiteCode = s.SamplingSiteCode"""
    df = pd.read_sql(q, con)
    print(len(df), "samples in sqlite")
    df = df[df["LFMC"].notna()].copy()
    num = lambda s: pd.to_numeric(s.astype(str).str.replace("\xa0", "").str.strip().str.replace(",", "."), errors="coerce")
    df["lat"], df["lon"] = num(df["Latitude"]), num(df["Longitude"])
    df["fixnote"] = pd.NA
    for code, (la, lo, note) in FIX.items():
        m = df["SamplingSiteCode"] == code
        df.loc[m, "lat"], df.loc[m, "lon"], df.loc[m, "fixnote"] = la, lo, note

    qa = pd.Series(pd.NA, index=df.index, dtype="string")
    mo, ao = df["ManualOutlier"] == 1, df["AdditiveOutlier"] == 1
    qa[mo] = "src_manual_outlier"
    qa[ao & ~mo] = "src_additive_outlier"
    qa[ao & mo] = "src_manual_outlier;src_additive_outlier"

    fmt = lambda s: s.astype(object).where(s.notna(), "NA").astype(str)
    notes = ("dry_weight_basis; fresh_g=" + fmt(df["FreshMass"]) + "; dry_g=" + fmt(df["DryMass"])
             + "; locality=" + df["LocalityName"].str.strip() + "; species_cat=" + df["SpeciesCAT"]
             + "; sitesp=" + df["SiteSpCode"])
    notes = notes.where(df["fixnote"].isna(), notes + "; " + df["fixnote"].fillna(""))

    out = pd.DataFrame({
        "source_record_id": df["SampleCode"].astype(str),
        "date": pd.to_datetime(df["Date"], unit="D"),
        "time": pd.NA,
        "timezone": "Europe/Madrid",
        "lat": df["lat"], "lon": df["lon"], "location_precision_m": 100,
        "country": "Spain",
        "site_name": df["SamplingSiteName"].str.strip(),
        "fuel_class": "live",
        "fuel_type": df["SpeciesName"].map(lambda s: "tree_foliage" if s == "Pinus halepensis" else "shrub"),
        "species": df["SpeciesName"],
        "moisture_pct": df["LFMC"],
        "method": "oven_dry",
        "measured": True,
        "qa_flag": qa,
        "notes": notes,
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)
