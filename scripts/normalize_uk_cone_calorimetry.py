"""Normalize EIDC 45af9c3d cone-calorimetry dataset (UKFDRS, Great Britain 2021-2023, OGL-UK-3.0)
to one row per fuel moisture sample.

The CSV has one row per cone test; each sample had two calorimetry subsamples (Replicate A/B)
and ONE moisture subsample, so the FMC value is repeated on the A and B rows. Samples are
reconstructed as an A row plus the following B row (keys Date/Site/Fuel_type/Species/Status are
identical within every pair). If A and B carry different FMC values (4 samples) both values are
kept as separate rows and flagged. Fuel_moisture_% and Duff_moisture_% are % of dry mass
(dried at 40-50 C to constant weight); duff (under litter samples) becomes its own row.
Shrub/grass/bracken samples are the top ~15 cm of canopy / whole above-ground plant. Litter
"species" is the dominant overstorey species. Sampling time is not given.
Site coordinates come from Table 1 of the supporting documentation (0.01 deg, ~1 km).
Kestrel weather at sampling (temp, RH, wind) -> covariates file.
"""
import numpy as np
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "uk_cone_calorimetry"
SITES = {  # Table 1, supporting_documentation_ukfdrs_cone_calorimetry.docx (lat N, lon E)
    "Scootmore": ("Scootmore Forest", 57.43, -3.39), "Danby_W": ("Danby West", 54.41, -0.92),
    "Danby_E": ("Danby East", 54.41, -0.90), "Goathland": ("Goathland Moor East", 54.37, -0.68),
    "Wykeham": ("Wykeham Forest", 54.28, -0.58), "Marsden": ("Marsden Moor", 53.55, -1.92),
    "Hope_Bog": ("Hope Woodlands (Bog)", 53.44, -1.84), "Hope_Heath": ("Hope Woodlands (Heath)", 53.42, -1.85),
    "Hope_AG": ("Hope Woodlands (Acid Grassland)", 53.41, -1.85),
    "STANTA_Heath": ("Stanford Training Area (Heath)", 52.54, 0.76),
    "STANTA_AG": ("Stanford Training Area (Acid Grassland)", 52.51, 0.74),
    "Thetford": ("Thetford Forest", 52.45, 0.66), "Talybont": ("Talybont Forest", 51.89, -3.32),
    "Holnicote_AG": ("Holnicote (Acid Grassland)", 51.18, -3.60),
    "Holnicote_Heath": ("Holnicote (Heath)", 51.17, -3.61), "Alice_Holt": ("Alice Holt Forest", 51.17, -0.84),
    "Thursley_Forest": ("Thursley Common (Forest)", 51.16, -0.72),
    "Thursley_Heath": ("Thursley Common (Heath)", 51.16, -0.71), "Hardown": ("Hardown Hill", 50.74, -2.84),
    "Duddle": ("Duddle Heath", 50.73, -2.37), "Woodbury": ("Woodbury Common", 50.68, -3.36),
    "Haldon": ("Haldon Forest Park", 50.65, -3.58),
}
VEG = {  # (species, status) -> fuel_type
    ("Molinia caerulea", "Live"): "grass", ("Molinia caerulea", "Dead"): "grass",
    ("Pteridium aquilinum", "Live"): "herb", ("Pteridium aquilinum", "Dead"): "dead_foliage",
}

if __name__ == "__main__":
    f = raw_dir(SOURCE_ID) / "eidc" / "data" / "icone_data_for_ukfdrs.csv"
    co = pd.read_csv(f)
    co["sid"] = (co["Replicate"] == "A").cumsum()
    keys = ["Date", "Site", "Fuel_type", "Species", "Status"]
    assert (co.groupby("sid")[keys].nunique(dropna=False) <= 1).all().all()
    co["date"] = pd.to_datetime(co["Date"].str.replace(".", "", regex=False), format="%d %b %Y")
    nvals = co.groupby("sid")["Fuel_moisture_%"].transform("nunique")

    # fuel rows: unique (sample, FMC) pairs
    fu = co.dropna(subset=["Fuel_moisture_%"]).drop_duplicates(["sid", "Fuel_moisture_%"]).copy()
    fu["kind"] = "fuel"
    fu["val"] = fu["Fuel_moisture_%"]
    du = co.dropna(subset=["Duff_moisture_%"]).drop_duplicates(["sid", "Duff_moisture_%"]).copy()
    du["kind"] = "duff"
    du["val"] = du["Duff_moisture_%"]
    s = pd.concat([fu, du], ignore_index=True)

    litter = s["Fuel_type"].eq("Litter")
    live = s["Status"].eq("Live")
    fclass = np.where(s["kind"].eq("duff") | litter | s["Status"].eq("Dead"), "dead", "live")
    ftype = []
    for k, lt, sp, st in zip(s["kind"], litter, s["Species"], s["Status"]):
        if k == "duff":
            ftype.append("duff")
        elif lt:
            ftype.append("litter")
        else:
            ftype.append(VEG.get((sp, st), "shrub" if st == "Live" else "fine_dead"))
    site = s["Site"].map(SITES)
    assert site.notna().all(), set(s.loc[site.isna(), "Site"])
    multi = s["sid"].map(co.groupby("sid")["Fuel_moisture_%"].nunique()) > 1
    qa = np.where(multi & s["kind"].eq("fuel"), "src_fmc_differs_between_replicate_rows", None)
    comp = np.where(s["kind"].eq("duff"), "duff beneath litter sample (litter overstorey: " + s["Species"] + ")",
                    np.where(litter, "litter (species = dominant overstorey)",
                             "standing vegetation, top ~15 cm canopy / whole plant; status=" + s["Status"].astype(str)))
    out = pd.DataFrame({
        "source_record_id": "sample" + s["sid"].astype(str) + "|" + s["kind"] + "|" + s["val"].astype(str),
        "date": s["date"], "time": pd.NA, "timezone": "Europe/London",
        "lat": site.map(lambda x: x[1]), "lon": site.map(lambda x: x[2]), "location_precision_m": 1000,
        "country": "United Kingdom",
        "site_name": site.map(lambda x: x[0]),
        "fuel_class": fclass, "fuel_type": ftype,
        "species": s["Species"].where(s["kind"].eq("fuel") & ~litter),
        "moisture_pct": s["val"], "method": "oven_dry", "measured": True, "qa_flag": qa,
        "notes": "dry_weight_basis; " + pd.Series(comp, index=s.index) + "; site_code=" + s["Site"]
                 + "; cone_ignited_first_replicate=" + s["Ignition"].astype(str),
    })
    out.loc[litter & s["kind"].eq("fuel"), "notes"] += "; overstorey=" + s.loc[litter, "Species"]
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)

    n = lambda c: pd.to_numeric(s[c], errors="coerce")
    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "uk_cone_calorimetry: Kestrel fire weather meter at sampling (as provided)",
        "air_temp_c": n("Temp_°C"), "rh_pct": n("RH_%"), "wind_ms": n("Wind_speed_m/s"),
    })
    cov = cov.dropna(subset=["air_temp_c", "rh_pct", "wind_ms"], how="all")
    (NORM / "covariates_by_source").mkdir(parents=True, exist_ok=True)
    cov.to_parquet(NORM / "covariates_by_source" / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
