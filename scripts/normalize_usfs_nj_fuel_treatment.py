"""Normalize RDS-2017-0061 (Gallagher et al. 2017): New Jersey Pine Barrens fuel treatment study,
pre-burn forest-floor fine fuel moisture (FMC.csv), 2014-2015.

Grab samples of fine fuels in the Om (forest floor litter) layer collected within an hour of
ignition, bagged airtight, weighed wet, oven-dried. FMC = (WET+BAG - BAG - DRY) / DRY * 100
(dry basis; verified). Plot coordinates via FMC.PLOT_ID -> PLOT.ID -> PLOT.PLOT_LOC_ID ->
PLOT_LOC (GPS, WGS84). Time is the census (sampling) time where given.
"""
import pandas as pd

from common import finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_nj_fuel_treatment"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    fmc = pd.read_csv(find(d, "FMC.csv"))
    plot = pd.read_csv(find(d, "PLOT.csv"))
    loc = pd.read_csv(find(d, "PLOT_LOC.csv"))
    site = pd.read_csv(find(d, "SITE.csv"))
    m = (fmc.merge(plot[["ID", "PLOT_LOC_ID", "BURN_DATE"]].rename(columns={"ID": "PLOT_ID"}), on="PLOT_ID", how="left")
            .merge(loc.rename(columns={"ID": "PLOT_LOC_ID"}), on="PLOT_LOC_ID", how="left")
            .merge(site.rename(columns={"ID": "SITE_ID", "SITE": "SITE_NAME", "LAT": "SLAT", "LONG": "SLON"}),
                   on="SITE_ID", how="left"))
    assert m["LAT"].notna().all()
    calc = (m["WET+BAG"] - m["BAG"] - m["DRY"]) / m["DRY"] * 100
    qa = ((calc - m["FMC"]).abs() > 1).map({True: "src_pct_mismatch", False: None})
    t = m["CENSUS_TIME"].astype("string")
    out = pd.DataFrame({
        "source_record_id": "FMC#" + m["ID"].astype(str),
        "date": pd.to_datetime(m["CENSUS_DATE"], format="%m/%d/%Y", errors="coerce"),
        "time": t.str.strip().str.zfill(5), "timezone": "America/New_York",
        "lat": m["LAT"], "lon": m["LONG"], "location_precision_m": 30.0, "country": "USA",
        "site_name": m["SITE_NAME"].str.strip() + " plot " + m["PLOT"].astype(str) + " (NJ Pine Barrens)",
        "fuel_class": "dead", "fuel_type": "litter", "species": pd.NA,
        "moisture_pct": m["FMC"], "method": "oven_dry", "measured": True, "qa_flag": qa,
        "notes": ("forest-floor (Om layer) fine fuel grab sample within 1 h of ignition; dry basis; burn_date="
                  + m["BURN_DATE"].astype(str) + "; sample=" + m["SAMP_NUM"].astype(str)),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
