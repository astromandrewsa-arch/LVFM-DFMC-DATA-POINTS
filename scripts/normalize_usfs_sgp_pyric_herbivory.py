"""Normalize RDS-2023-0025 (Starns et al. 2023): southern Great Plains pyric-herbivory fuels.

Veg_Fuel_Data.csv: one row per 0.25 m2 clip plot (5 plots x 8 transects per burn patch) at four
sites in OK/TX, Jun 2014 - Aug 2016. All standing vegetation in the plot was clipped, weighed wet
in a paper bag (PlotFuel, incl. 37 g bag), dried to stable weight (DryFuel, incl. bag);
FuelAdj = net dry mass.

Moisture basis: the source 'Moisture' column is wet-basis and its denominator includes the bag
((PlotFuel-DryFuel)/PlotFuel). We recompute dry-basis moisture from the weights:
    moisture_pct = (PlotFuel - DryFuel) / FuelAdj * 100
and keep the source value in notes. Plots with FuelAdj <= 0 or missing weights are dropped.
The clip is a mixed live + dead/dormant herbaceous (and some woody) sample, so rows are labelled
fuel_class 'live', fuel_type 'grass' with qa_flag 'mixed_live_dead' (cover % of grass/forb/shrub/
litter and live/dead dowel heights go to covariates so users can filter).

Dates: only collection year + month are given -> date set to the 15th, notes date_precision=month.
Locations: the dataset gives only site names and a bounding box (whose edges coincide with the
sites). Site coordinates are approximate centroids of each preserve/refuge -> location_approx,
location_precision_m 5-8 km.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_sgp_pyric_herbivory"
SITES = {  # approx centroid lat, lon, precision m, state, full name
    "TGPP": (36.84, -96.42, 8000, "OK", "Tallgrass Prairie Preserve"),
    "PACK": (35.90, -99.66, 6000, "OK", "Packsaddle Wildlife Management Area"),
    "ANWR": (28.24, -96.83, 8000, "TX", "Aransas National Wildlife Refuge"),
    "APCNWR": (29.67, -96.29, 5000, "TX", "Attwater Prairie-Chicken National Wildlife Refuge"),
}
MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    df = pd.read_csv(find(d, "Veg_Fuel_Data.csv"), encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["_row"] = range(len(df))
    n = lambda c: pd.to_numeric(df[c], errors="coerce")
    water = n("PlotFuel") - n("DryFuel")
    dry = n("FuelAdj")
    mp = water / dry * 100
    ok = mp.notna() & (dry > 0) & (water >= 0)
    print(len(df), "rows;", int((~ok).sum()), "dropped (missing/invalid weights)")
    df, mp = df[ok].copy(), mp[ok]

    site = df["Location"].str.strip()
    info = site.map(SITES)
    month = df["Collect Month"].str.strip().str.upper().map(MONTHS)
    date = pd.to_datetime(dict(year=df["Collect Year"], month=month, day=15), errors="coerce")
    notes = ("clip plot 0.25 m2, all vegetation; dry basis recomputed from weights "
             "(PlotFuel-DryFuel)/FuelAdj; src_moisture_wet_basis=" + n("Moisture")[df.index].round(2).astype(str)
             + "; date_precision=month (day set to 15); grazed=" + df["Grazed"].astype(str)
             + "; burn_season=" + df["Season"].astype(str) + "; burn_year=" + df["BurnYear"].astype(str)
             + "; months_since_fire=" + df["MSF"].astype(str) + "; unit=" + df["Unit"].astype(str)
             + "; location_approx (site centroid; no plot coordinates published)")
    # weights are recorded to 1 g, so small samples are very noisy
    qa = pd.Series("mixed_live_dead", index=df.index)
    qa[dry[df.index] < 10] += ";low_dry_mass_lt10g"
    qa[mp > 400] += ";implausible_high"
    qa[mp <= 0] += ";nonpositive_moisture"
    out = pd.DataFrame({
        "source_record_id": df["Sample"].astype(str) + "@" + df["Collect Year"].astype(str) + "-"
                            + df["Collect Month"].astype(str) + "#" + df["_row"].astype(str),
        "date": date, "time": pd.NA, "timezone": "America/Chicago",
        "lat": info.str[0], "lon": info.str[1], "location_precision_m": info.str[2],
        "country": "USA", "site_name": info.str[4] + " (" + info.str[3] + ") unit " + df["Unit"].astype(str),
        "fuel_class": "live", "fuel_type": "grass", "species": "mixed herbaceous (grass/forb/shrub clip)",
        "moisture_pct": mp, "method": "oven_dry", "measured": True,
        "qa_flag": qa, "notes": notes,
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)

    cov = pd.DataFrame({
        "observation_id": out["observation_id"].values, "cov_source": "source_measured(plot)",
        "biomass_kg_ha": n("Biomass")[df.index].values,
        "cover_grass_frac": n("Grass")[df.index].values, "cover_forb_frac": n("Forb")[df.index].values,
        "cover_shrub_frac": n("Shrub")[df.index].values, "cover_litter_frac": n("Litter")[df.index].values,
        "cover_bare_frac": n("Bare")[df.index].values,
        "herb_height_mean_cm": n("AvgHerb")[df.index].values, "herb_height_max_cm": n("TallHerb")[df.index].values,
        "live_dowel_contact_height_mean_units_unspecified": df[["MaxL1", "MaxL2", "MaxL3", "MaxL4"]].apply(pd.to_numeric, errors="coerce").mean(axis=1).values,
        "dead_dowel_contact_height_mean_units_unspecified": df[["MaxD1", "MaxD2", "MaxD3", "MaxD4"]].apply(pd.to_numeric, errors="coerce").mean(axis=1).values,
        "months_since_fire": n("MSF")[df.index].values,
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
