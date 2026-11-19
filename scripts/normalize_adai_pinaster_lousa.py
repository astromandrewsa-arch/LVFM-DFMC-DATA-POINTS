"""Normalize Zenodo 13147079 (ADAI-CEIF, dead Pinus pinaster needle litter FMC, Lousa, Portugal,
2014-2023, CC-BY-4.0) to the observation schema.

Each row is a daily value = mean of four 5 g subsamples dried >= 24 h at 105 C, in % of dry
weight (column "Fuel moisture content in dry basis (%)") -> notes "aggregated_mean n=4".
Surface litter of dead P. pinaster needles under a P. pinaster / Eucalyptus globulus stand.
Site (Info sheet): Cha do Freixo, Lousa, 40.140282 N, -8.239693 E, 170 m, 30 % slope, south.
Sampled between 12:00 and 14:00 local standard time (UTC+0, no DST); exact time not given,
so time is left empty and the window is noted. Elevation/slope -> covariates file.
"""
import openpyxl
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "adai_pinaster_lousa"

if __name__ == "__main__":
    f = raw_dir(SOURCE_ID) / "FuelMoistureContent_data_availability.xlsx"
    wb = openpyxl.load_workbook(f, data_only=True, read_only=True)
    info = {r[0]: r[1] for r in wb["Info"].iter_rows(values_only=True) if r[0]}
    df = pd.read_excel(f, sheet_name="mf_data")
    df.columns = [c.strip() for c in df.columns]
    print(len(df), "rows")
    assert set(df["Fuel state"]) == {"Dead leaves"}, set(df["Fuel state"])
    out = pd.DataFrame({
        "source_record_id": df["ID"].astype(str),
        "date": pd.to_datetime(df["Sampling date"]),
        "time": pd.NA,
        "timezone": "UTC+0 (Portugal local standard time)",
        "lat": float(info["Latitude (º)"]), "lon": float(info["Longitude (º)"]),
        "location_precision_m": 100,
        "country": "Portugal",
        "site_name": f"{info['Sitename']}, {info['Municipality']}",
        "fuel_class": "dead",
        "fuel_type": "litter",
        "species": df["Specie"],
        "moisture_pct": df["Fuel moisture content in dry basis (%)"],
        "method": "oven_dry",
        "measured": True,
        "notes": ("aggregated_mean n=4 (4 x 5 g subsamples, 105 C >= 24 h); dry_weight_basis; "
                  "dead needle surface litter; sampled " + df["Sampling time (LST)"].astype(str) + " LST"),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)
    cov = pd.DataFrame({"observation_id": out["observation_id"],
                        "cov_source": "adai_pinaster_lousa: site metadata (Info sheet)",
                        "elevation_m": float(info["Elevation (m)"]), "slope_pct": float(info["Slope (%)"]),
                        "aspect": str(info["Exposition"])})
    (NORM / "covariates_by_source").mkdir(parents=True, exist_ok=True)
    cov.to_parquet(NORM / "covariates_by_source" / f"{SOURCE_ID}.parquet", index=False)
