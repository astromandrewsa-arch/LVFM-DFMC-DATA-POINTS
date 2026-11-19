"""Normalize RDS-2015-0016 (Wright 2015): sagebrush consumption burns, fuel moisture.

'Fuel Moisture and Weather.csv' gives one value per burn site and fuel category (wide format);
'Site Variables.csv' gives burn date, ignition time, lat/long (decimal degrees, longitude stored
as a positive number -> negated to WGS84 west) and elevation (feet). Values are site-level
gravimetric fuel moisture (%) from samples collected before ignition; the per-sample data are not
published, so each row is a site mean -> notes 'aggregated_mean n=unknown'. Moisture basis is not
stated explicitly in the metadata ('Fuel moisture: ...', %) -> notes 'basis_unclear' (USFS FERA
convention is dry-weight basis). Soil moisture (fm_soil) is not a fuel and goes to covariates.
Grass live/dead status is not given -> fuel_class 'dead' with qa_flag 'live_dead_unspecified'.
'.' = missing (not imputed).
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_sagebrush_consumption"
COLS = {  # column -> fuel_class, fuel_type, label, qa
    "fm_fol": ("live", "shrub", "sagebrush foliage and twigs", None),
    "fm_gr": ("dead", "grass", "grass", "live_dead_unspecified"),
    "fm_1": ("dead", "1hr", "sagebrush dead 1-h", None),
    "fm_10": ("dead", "10hr", "sagebrush dead 10-h", None),
    "fm_100": ("dead", "100hr", "sagebrush dead 100-h", None),
    "fm_l100": ("live", "shrub", "sagebrush live 100-h stems", None),
    "fm_branch": ("live", "shrub", "sagebrush branch (live/dead not stated)", "live_dead_unspecified"),
}
SPP = {"ARTRTR": "Artemisia tridentata ssp. tridentata", "ARTRWY": "Artemisia tridentata ssp. wyomingensis",
       "ARTRVA": "Artemisia tridentata ssp. vaseyana", "ARAR8": "Artemisia arbuscula"}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    fm = pd.read_csv(find(d, "Fuel Moisture and Weather.csv"), encoding="latin-1", na_values=["."])
    site = pd.read_csv(find(d, "Site Variables.csv"), encoding="latin-1", na_values=["."])
    fm["siteid"] = fm["siteid"].str.strip()
    site["siteID"] = site["siteID"].str.strip()
    m = fm.merge(site, left_on="siteid", right_on="siteID", how="left", validate="1:1")
    assert m["lat"].notna().all()
    rows, covs = [], []
    for col, (fc, ft, label, qa) in COLS.items():
        v = pd.to_numeric(m[col], errors="coerce")
        sub = m[v.notna()]
        spp = sub["spp"].astype(str).str.strip()
        species = spp.map(SPP).fillna(spp) if ft != "grass" else pd.Series("grass (unspecified)", index=sub.index)
        rid = sub["siteid"] + "|" + col
        r = pd.DataFrame({
            "source_record_id": rid,
            "date": pd.to_datetime(sub["date"], format="%m/%d/%Y", errors="coerce"),
            "time": pd.NA, "timezone": "local",
            "lat": sub["lat"], "lon": -sub["long"].abs(), "location_precision_m": 100.0,
            "country": "USA", "site_name": sub["siteid"] + " (" + sub["state"].astype(str) + ")",
            "fuel_class": fc, "fuel_type": ft, "species": species,
            "moisture_pct": v[sub.index], "method": "oven_dry", "measured": True, "qa_flag": qa,
            "notes": ("aggregated_mean n=unknown; basis_unclear; category=" + label + "; src_col=" + col
                      + "; sampled before ignition; ignition_time=" + sub["time"].astype(str)
                      + "; burn_season=" + sub["season"].astype(str) + "; spp_code=" + spp),
        })
        r["observation_id"] = [make_obs_id(SOURCE_ID, x) for x in rid]
        rows.append(r)
        covs.append(pd.DataFrame({
            "observation_id": r["observation_id"], "cov_source": "source_measured(at ignition)",
            "obs_temp_c": pd.to_numeric(sub["temp_c"], errors="coerce"),
            "obs_rh_pct": pd.to_numeric(sub["rh"], errors="coerce"),
            "obs_wind_ms": pd.to_numeric(sub["ws_kph"], errors="coerce") / 3.6,
            "days_since_rain_gt2p5mm": pd.to_numeric(sub["dsr"], errors="coerce"),
            "soil_moisture_pct": pd.to_numeric(sub["fm_soil"], errors="coerce"),
            "elevation_m": pd.to_numeric(sub["elev"], errors="coerce") * 0.3048,
            "slope_deg": pd.to_numeric(sub["slope"], errors="coerce"),
            "aspect_deg": pd.to_numeric(sub["aspect"], errors="coerce"),
        }))
    out = pd.concat(rows, ignore_index=True)
    finalize(out, SOURCE_ID)
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    pd.concat(covs, ignore_index=True).to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
