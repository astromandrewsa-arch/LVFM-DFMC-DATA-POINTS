"""Normalize RDS-2016-0023 (Gallacher et al. 2016; JFSP 11-1-4-19): monthly live foliage moisture
of 10 wildland fuel species, 2012-2014.

PhysicalProperties_LiveFoliage_v2.csv has one row per measured fuel element ('Run'), but
'Moisture content' (proportion of dry mass; Computrac Max1000 analyser at 95 C) is a single
value per species x site x date x foliage age that is repeated on every run. Rows are therefore
collapsed to one observation per distinct (species, site, date, foliage age, MC) and MC is
converted proportion -> percent (x100). Each value is one analyser measurement of a composite
sample (min 1 g), not a mean of runs. 'Date' is the date of measurement at BYU (samples were
bagged on site and transported; collection was shortly before) -> notes.
Site coordinates are given in the metadata (Location attribute domain); collection was from
the same plants each month at 'easily accessible locations' near those points -> 1 km precision.
Species mapped from source common names (Eastwood's manzanita = Arctostaphylos glandulosa,
hoaryleaf ceanothus = Ceanothus crassifolius, etc.); common name kept in notes.
"""
import pandas as pd

from common import finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_live_foliage_props"
SITES = {"DuckPond": (30.6717, -86.6329, "FL", "America/Chicago"),
         "Lubrecht": (46.896, -113.440, "MT", "America/Denver"),
         "BlueMountain": (46.834, -114.115, "MT", "America/Denver"),
         "RockCanyon": (40.265, -111.630, "UT", "America/Denver"),
         "NorthMountain": (33.844, -116.880, "CA", "America/Los_Angeles")}
SPECIES = {"Douglas-fir": ("Pseudotsuga menziesii", "tree_foliage"),
           "Lodgepole pine": ("Pinus contorta", "tree_foliage"),
           "Sand pine": ("Pinus clausa", "tree_foliage"),
           "Gambel oak": ("Quercus gambelii", "shrub"),
           "Eastwood's manzanita": ("Arctostaphylos glandulosa", "shrub"),
           "Hoaryleaf ceanothus": ("Ceanothus crassifolius", "shrub"),
           "Chamise": ("Adenostoma fasciculatum", "shrub"),
           "Big sagebrush": ("Artemisia tridentata", "shrub"),
           "Fetterbush": ("Lyonia lucida", "shrub"),
           "Gallberry": ("Ilex glabra", "shrub")}

if __name__ == "__main__":
    df = pd.read_csv(find(raw_dir(SOURCE_ID), "PhysicalProperties_LiveFoliage_v2.csv"), encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["Common name"] = df["Common name"].str.strip()
    df["Location"] = df["Location"].str.strip()
    df = df[pd.to_numeric(df["Moisture content"], errors="coerce").notna()]
    keys = ["Common name", "Location", "Date", "Foliage Age", "Moisture content"]
    g = (df.groupby(keys, dropna=False)
           .agg(n_runs=("Run", "size"), rwc=("Relative water content", "first"))
           .reset_index())
    print(len(df), "element rows ->", len(g), "distinct moisture measurements")
    sp = g["Common name"].map(SPECIES)
    assert sp.notna().all(), g.loc[sp.isna(), "Common name"].unique()
    site = g["Location"].map(SITES)
    age = g["Foliage Age"].map(lambda a: "" if pd.isna(a) else f"; foliage_age_code={int(a)}")
    rid = (g["Common name"] + "|" + g["Location"] + "|" + g["Date"].astype(str) + "|"
           + g["Foliage Age"].astype(str))
    out = pd.DataFrame({
        "source_record_id": rid,
        "date": pd.to_datetime(g["Date"], format="%m/%d/%Y", errors="coerce"),
        "time": pd.NA, "timezone": site.str[3],
        "lat": site.str[0], "lon": site.str[1], "location_precision_m": 1000.0, "country": "USA",
        "site_name": g["Location"] + " (" + site.str[2] + ")",
        "fuel_class": "live", "fuel_type": sp.str[1], "species": sp.str[0],
        "moisture_pct": pd.to_numeric(g["Moisture content"]) * 100, "method": "oven_dry", "measured": True,
        "notes": ("moisture analyser (Computrac Max1000, 95 C), dry basis, converted from proportion x100; "
                  "date = lab measurement date (samples bagged and transported, collected shortly before); "
                  "common_name=" + g["Common name"] + age + "; relative_water_content="
                  + g["rwc"].astype(str) + "; n_element_rows_sharing_value=" + g["n_runs"].astype(str)),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in rid]
    finalize(out, SOURCE_ID)
