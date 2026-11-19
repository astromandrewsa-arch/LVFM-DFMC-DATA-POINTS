"""Normalize RDS-2015-0019 (Wright 2015): pine flatwoods consumption burns (FL/GA).

FuelMoisture_and_FireWeather.csv: one value per site and category = mean of n = 5-10 samples
collected shortly before ignition, oven 100 C >= 48 h, gravimetric -> notes 'aggregated_mean
n=5-10'. Basis not written out (USFS FERA convention: dry weight) -> 'basis_unclear'.
Per Methods, 4 of 17 units used one sample set for several sites (identical values repeat).
Composite columns fm_sh, fm_palm, fm_p_sh are averages of other columns and are not ingested;
fm_s (soil) goes to covariates. Grass live/dead status not stated -> fuel_class dead + qa flag.
Site_Info.csv: lat/long decimal degrees (longitude stored positive -> negated), elevation feet.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_flatwoods_consumption"
COLS = {
    "fm_pst": ("live", "shrub", "live saw palmetto stem (rachis)", "Serenoa repens", None),
    "fm_plf": ("live", "shrub", "live saw palmetto leaf (frond)", "Serenoa repens", None),
    "fm_shst": ("live", "shrub", "live woody shrub stem", "woody shrubs (unspecified)", None),
    "fm_shlf": ("live", "shrub", "live woody shrub leaf", "woody shrubs (unspecified)", None),
    "fm_dpalm": ("dead", "dead_foliage", "dead palmetto leaves and rachis", "Serenoa repens", None),
    "fm_g": ("dead", "grass", "grass", "grass (unspecified)", "live_dead_unspecified"),
    "fm_li": ("dead", "litter", "pine needle litter", "Pinus spp. litter", None),
    "fm_10": ("dead", "10hr", "dead down woody 0.6-2.5 cm", None, None),
}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    fm = pd.read_csv(find(d, "FuelMoisture_and_FireWeather.csv"), encoding="latin-1", na_values=["."])
    site = pd.read_csv(find(d, "Site_Info.csv"), encoding="latin-1", na_values=["."])
    m = fm.merge(site, on="site_id", how="left", validate="1:1")
    assert m["lat"].notna().all()
    rows, covs = [], []
    for col, (fc, ft, label, sp, qa) in COLS.items():
        v = pd.to_numeric(m[col], errors="coerce")
        sub = m[v.notna()]
        rid = sub["site_id"] + "|" + col
        r = pd.DataFrame({
            "source_record_id": rid,
            "date": pd.to_datetime(sub["date"], format="%m/%d/%Y", errors="coerce"),
            "time": pd.NA, "timezone": "local",
            "lat": sub["lat"], "lon": -sub["long"].abs(), "location_precision_m": 100.0,
            "country": "USA", "site_name": sub["site_id"] + " " + sub["loc"].astype(str) + " (" + sub["st"].astype(str) + ")",
            "fuel_class": fc, "fuel_type": ft, "species": sp,
            "moisture_pct": v[sub.index], "method": "oven_dry", "measured": True, "qa_flag": qa,
            "notes": ("aggregated_mean n=5-10; basis_unclear; category=" + label + "; src_col=" + col
                      + "; sampled shortly before ignition; ignition_time=" + sub["time"].astype(str)
                      + "; burn_season=" + sub["sea"].astype(str)),
        })
        r["observation_id"] = [make_obs_id(SOURCE_ID, x) for x in rid]
        rows.append(r)
        covs.append(pd.DataFrame({
            "observation_id": r["observation_id"], "cov_source": "source_measured(at ignition)",
            "obs_temp_c": pd.to_numeric(sub["temp_c"], errors="coerce"),
            "obs_rh_pct": pd.to_numeric(sub["rh"], errors="coerce"),
            "obs_wind_ms": pd.to_numeric(sub["ws_kph"], errors="coerce") / 3.6,
            "days_since_rain": pd.to_numeric(sub["dsr"], errors="coerce"),
            "kbdi": pd.to_numeric(sub["kbdi"], errors="coerce"),
            "soil_moisture_pct": pd.to_numeric(sub["fm_s"], errors="coerce"),
            "elevation_m": pd.to_numeric(sub["el"], errors="coerce") * 0.3048,
        }))
    out = pd.concat(rows, ignore_index=True)
    cov = pd.concat(covs, ignore_index=True)
    # A343N/A343S: 'Unit burned when FERA crew not present' - no date, so values are not
    # attributable to a sampling day -> dropped.
    keep = out["date"].notna()
    print("dropping undated rows:", int((~keep).sum()))
    out, cov = out[keep], cov[keep.values]
    finalize(out, SOURCE_ID)
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
