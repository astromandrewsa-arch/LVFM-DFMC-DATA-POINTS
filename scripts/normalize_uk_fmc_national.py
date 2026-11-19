"""Normalize the UKFDRS sampled fuel moisture database (EIDC 9334118f, OGL-UK-3.0).

Three files -> one source (they are three separate studies with no shared samples):
  uk_wide  (5,851 rows, 44 sites, 2021-02-24..2023-06-05)
  nym      (North York Moors landscape study, 1,124 rows, 5 days in 2021)
  wm       (West Midlands among-sampler study, 1,089 rows, Lickey Hills 2022-03-28; 17 samplers
            each sampling the same plots - replicate measurements, kept one row per sample)
FMC is gravimetric on a dry-weight basis ((W-D)/(D-T)*100, 48 h at 80 C). One row per sample.
UK-wide rows with Outlier_removed == "Y" (6) are kept with qa_flag src_outlier_removed.
Time_collected is to the nearest hour, local clock time (Europe/London, GMT/BST).

Covariates -> data/normalized/covariates_by_source/uk_fmc_national.parquet:
  uk_wide: in-situ air temperature/RH/wind at sampling, site elevation/slope/aspect, plus the
  ERA5-Land/E-OBS columns that the figshare copy (26363941, identical rows) carries.
  nym: 5 h mean micrometeorology from figshare 25041644 met_fmc_landscape.csv, joined on
  lat/lon/date/FMC (94% of rows match).
"""
import numpy as np
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "uk_fmc_national"

# Fuel_type -> (fuel_class, fuel_type, component)
FUEL = {
    "Heather live canopy": ("live", "shrub", "canopy"),
    "Heather live stem": ("live", "shrub", "stem"),
    "Heather dead canopy": ("dead", "fine_dead", "dead heather canopy"),
    "Heather dead stem": ("dead", "fine_dead", "dead heather stem"),
    "Gorse live canopy": ("live", "shrub", "canopy"),
    "Gorse live stem": ("live", "shrub", "stem"),
    "Gorse dead canopy": ("dead", "fine_dead", "dead gorse canopy"),
    "Gorse dead stem": ("dead", "fine_dead", "dead gorse stem"),
    "Bracken live leaves": ("live", "herb", "fronds"),
    "Bracken live stem": ("live", "herb", "stem"),
    "Bracken dead leaves": ("dead", "dead_foliage", "dead fronds"),
    "Bracken dead stem": ("dead", "fine_dead", "dead stem"),
    "Moor grass live": ("live", "grass", "live grass"),
    "Moor grass dead": ("dead", "grass", "dead grass"),
    "Twigs": ("dead", "1hr", "twigs <5 mm, suspended"),
    "Litter": ("dead", "litter", "top 2 cm litter"),
    "Moss": ("live", "moss", "top 2 cm live moss"),
    "Organic layer": ("dead", "duff", "organic layer, top 5 cm below litter"),
}


def hhmm(v):
    v = pd.to_numeric(v, errors="coerce")
    return v.map(lambda x: f"{int(x) // 100:02d}:{int(x) % 100:02d}" if pd.notna(x) else pd.NA)


def base(df, study, site_col, extra_notes):
    ft = df["Fuel_type"].map(FUEL)
    assert ft.notna().all(), set(df.loc[ft.isna(), "Fuel_type"])
    sp = df["Species_name"].astype("string")
    notes = ("study=" + study + "; dry_weight_basis; fuel_component=" + ft.map(lambda x: x[2])
             + "; src_fuel_type=" + df["Fuel_type"] + extra_notes)
    return pd.DataFrame({
        "date": pd.to_datetime(df["Date"], format="%d/%m/%Y"),
        "time": hhmm(df["Time_collected"]) if "Time_collected" in df else pd.NA,
        "timezone": "Europe/London",
        "lat": df["Latitude"], "lon": df["Longitude"], "location_precision_m": 30,
        "country": "United Kingdom",
        "site_name": df[site_col].astype(str).str.strip(),
        "fuel_class": ft.map(lambda x: x[0]),
        "fuel_type": ft.map(lambda x: x[1]),
        "species": sp,
        "moisture_pct": df["FMC_%"],
        "method": "oven_dry",
        "measured": True,
        "notes": notes,
    })


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    e = d / "eidc" / "data"
    uk = pd.read_csv(e / "ukfdrs_fuel_moisture_uk_wide.csv")
    nym = pd.read_csv(e / "ukfdrs_fuel_moisture_north_york_moors.csv")
    wm = pd.read_csv(e / "ukfdrs_fuel_moisture_west_midlands.csv")
    fs = pd.read_csv(d / "figshare_26363941_UK_dataset.csv")
    # figshare copy must be row-identical to the EIDC file for the covariate join by position
    for c in ["Date", "Site", "Fuel_type", "FMC_%", "Latitude", "Longitude"]:
        assert (fs[c].astype(str).values == uk[c].astype(str).values).all(), c

    a = base(uk, "uk_wide", "Site", "; climate_region=" + uk["Climate_region_of_UK"].astype(str)
             + "; lcm=" + uk["LCM_land_cover"].astype(str))
    a["source_record_id"] = "uk_wide|" + uk.index.astype(str)
    a["qa_flag"] = np.where(uk["Outlier_removed"].eq("Y"), "src_outlier_removed", None)

    b = base(nym, "north_york_moors_2021", "Site_name",
             "; canopy_age=" + nym["Heather_canopy_age"].astype(str) + "; soil=" + nym["Soil_texture"].astype(str)
             + "; hillslope=" + nym["Hillslope_position"].astype(str) + "; aspect=" + nym["Aspect"].astype(str))
    b["source_record_id"] = "nym|" + nym.index.astype(str)

    c = base(wm, "west_midlands_among_sampler_2022", "Site_name",
             "; sampler=" + wm["Sampler"].astype(str) + " (17 samplers sampled same plots; replicate)")
    c["source_record_id"] = "wm|" + wm.index.astype(str)

    out = pd.concat([a, b, c], ignore_index=True)
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)

    # ---- covariates
    K = 273.15
    n = lambda s: pd.to_numeric(s, errors="coerce")
    cu = pd.DataFrame({
        "observation_id": out["observation_id"].iloc[: len(uk)].values,
        "cov_source": "uk_fmc_national: in-situ at sampling (Kestrel) + ERA5-Land/E-OBS from figshare 26363941",
        "air_temp_c": n(uk["Air_temperature_C"]).values,
        "rh_pct": n(uk["Relative_humidity_%"]).values,
        "wind_ms": n(uk["Wind_speed_m/s"]).values,
        "elevation_m": n(uk["Elevation"]).values,
        "slope_deg": n(uk["Slope"]).values,
        "aspect_deg": n(uk["Aspect"]).values,
        "eobs_tmean_c": n(fs["EOBS_air_temperature_24h_mean_C"]).values,
        "eobs_precip_1d_mm": n(fs["EOBS_24h_precipitation_mm/day"]).values,
        "days_since_precip": n(fs["No_days_since_precipitation"]).values,
        "tmean_c": (n(fs["2m_air_temperature_24h_mean_K"]) - K).values,
        "tmax_c": (n(fs["2m_air_temperature_24h_max_K"]) - K).values,
        "dewpoint_mean_c": (n(fs["2m_dewpoint_temperature_24h_mean_K"]) - K).values,
        "wind_mean_ms": n(fs["10m_wind_speed_24h_mean_m/s"]).values,
        "vapor_pressure_hpa": n(fs["Vapour_pressure_24h_mean_hPa"]).values,
        "rh_06_pct": n(fs["2m_relative_humidity_6h_%"]).values,
        "rh_09_pct": n(fs["2m_relative_humidity_9h_%"]).values,
        "rh_12_pct": n(fs["2m_relative_humidity_12h_%"]).values,
        "rh_15_pct": n(fs["2m_relative_humidity_15h_%"]).values,
        "precip_1d_mm": n(fs["Precipitation_24h_sum_mm/day"]).values,
        "precip_3d_mm": n(fs["Precipitation_sum_3_days_before_mm/day"]).values,
        "precip_7d_mm": n(fs["Precipitation_sum_1_week_before_mm/day"]).values,
        "precip_28d_mm": n(fs["Precipitation_sum_4_weeks_before_mm/day"]).values,
        "precip_84d_mm": n(fs["Precipitation_sum_12_weeks_before_mm/day"]).values,
        "landcover_igbp": fs["IGBP_land_cover"].astype("string").values,
    })
    m = pd.read_csv(d / "figshare_25041644_met_fmc_landscape.csv")
    key = lambda la, lo, dt, v: list(zip(la.round(5), lo.round(5), dt, v.round(4)))
    m["k"] = key(m["dd_lat"], m["dd_lon"], m["date"], m["fmc_perc"])
    m = m.drop_duplicates("k")
    nk = pd.DataFrame({"observation_id": out["observation_id"].iloc[len(uk): len(uk) + len(nym)].values,
                       "k": key(nym["Latitude"], nym["Longitude"],
                                pd.to_datetime(nym["Date"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d"),
                                nym["FMC_%"])})
    nk = nk.merge(m[["k", "temp", "rh", "dp", "ws", "vpd"]], on="k", how="inner")
    cn = pd.DataFrame({
        "observation_id": nk["observation_id"],
        "cov_source": "uk_fmc_national: NYM micromet station 5 h mean (figshare 25041644; ws units as given, assumed m/s)",
        "air_temp_c": nk["temp"], "rh_pct": nk["rh"], "dewpoint_mean_c": nk["dp"],
        "wind_ms": nk["ws"], "vpd_kpa": nk["vpd"],
    })
    cov = pd.concat([cu, cn], ignore_index=True)
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov), "(nym matched", len(cn), "of", len(nym), ")")
