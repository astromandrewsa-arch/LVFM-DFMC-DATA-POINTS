"""Normalize Globe-LFMC 2.0 'LFMC data' sheet to the observation schema.

Also writes the covariates the dataset ships with (ERA5-derived precipitation, RH, temperature,
vapor pressure, wind, dew point; elevation, slope, IGBP land cover) to
data/normalized/covariates_by_source/globe_lfmc2.parquet, keyed by observation_id, so
join_weather.py can use them as "source-provided" covariates.
The 'Contact' sheet (personal contact details) is deliberately not read.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "globe_lfmc2"

if __name__ == "__main__":
    src = raw_dir(SOURCE_ID) / "Globe-LFMC-2.0_final.xlsx"
    df = pd.read_excel(src, sheet_name="LFMC data", engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    print(len(df), "raw rows")

    t = df["Sampling time (24h format)"]
    time_str = t.map(lambda v: v.strftime("%H:%M") if hasattr(v, "strftime") else (str(v) if pd.notna(v) else pd.NA))
    date = pd.to_datetime(df["Sampling date (YYYYMMDD)"].astype(str).str[:10].str.replace("-", ""),
                          format="%Y%m%d", errors="coerce")

    notes = ("protocol=" + df["Protocol"].astype(str)
             + "; functional_type=" + df["Species functional type"].astype(str)
             + "; sample=" + df["Individual sample or mean value"].astype(str)
             + "; leaves=" + df["Old or new leaves"].astype(str)
             + "; state=" + df["State/Region"].astype(str)
             + "; contact=" + df["Contact"].astype(str)
             + "; ref=" + df["Reference"].astype(str).str.slice(0, 200))
    extra = df["Extra information/Quality Flag"].astype("string")
    notes = notes.where(extra.isna(), notes + "; src_flag=" + extra)

    ft = df["Species functional type"].astype(str).str.lower()
    fuel_type = pd.Series("live_foliage", index=df.index)
    fuel_type[ft.str.contains("grass")] = "grass"
    fuel_type[ft.str.contains("forb|herb")] = "herb"
    fuel_type[ft.str.contains("shrub")] = "shrub"
    fuel_type[ft.str.contains("tree")] = "tree_foliage"

    out = pd.DataFrame({
        "source_record_id": df["Sorting ID"].astype(str),
        "date": date,
        "time": time_str,
        "timezone": "local",
        "lat": df["Latitude (WGS84, EPSG:4326)"],
        "lon": df["Longitude (WGS84, EPSG:4326)"],
        "country": df["Country"].astype(str).str.strip(),
        "site_name": df["Site name"].astype(str),
        "fuel_class": "live",
        "fuel_type": fuel_type,
        "species": df["Species collected"].astype(str).str.strip(),
        "moisture_pct": df["LFMC value (%)"],
        "method": "oven_dry",
        "measured": True,
        "qa_flag": df["Isolated data point"].astype(str).str.upper().map({"TRUE": "src_isolated_point"}),
        "notes": notes,
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)

    K = 273.15
    num = lambda c: pd.to_numeric(df[c], errors="coerce")
    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "globe_lfmc2_provided(ERA5-Land per Yebra et al. 2024)",
        "precip_1d_mm": num("Precipitation 24h sum (mm/day)"),
        "precip_3d_mm": num("Precipitation sum 3 days before (mm/day)"),
        "precip_7d_mm": num("Precipitation sum 1 week before (mm/day)"),
        "precip_28d_mm": num("Precipitation sum 4 weeks before (mm/day)"),
        "precip_84d_mm": num("Precipitation sum 12 weeks before (mm/day)"),
        "rh_06_pct": num("2m Relative Humidity at 06h (%)"),
        "rh_09_pct": num("2m Relative Humidity at 09h (%)"),
        "rh_12_pct": num("2m Relative Humidity at 12h (%)"),
        "rh_15_pct": num("2m Relative Humidity at 15h (%)"),
        "tmax_c": num("2m Air Temperature 24h max (K)") - K,
        "tmean_c": num("2m Air Temperature 24h mean (K)") - K,
        "vapor_pressure_hpa": num("Vapour Pressure 24h mean (hPa)"),
        "wind_mean_ms": num("10m Wind Speed 24h mean (m/s)"),
        "dewpoint_mean_c": num("2m Dewpoint Temperature 24h mean (K)") - K,
        "elevation_m": pd.to_numeric(df["Elevation (m.a.s.l)"], errors="coerce"),
        "slope_pct": pd.to_numeric(df["Slope (%)"], errors="coerce"),
        "slope_raw": df["Slope (%)"].astype("string"),
        "landcover_igbp": df["IGBP Land Cover"].astype("string"),
    })
    d = NORM / "covariates_by_source"
    d.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(d / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
