"""Normalize figshare 24476446 "Calluna sampling data" (diurnal FMC, North York Moors 2022,
CC-BY-4.0). One row per sample. FMC is % of dry weight (UKFDRS gravimetric protocol).

Location: the file gives no coordinates; the only location information is the weather station
used (Blakey Ridge, North York Moors). Placed at Blakey Ridge (54.39 N, 0.95 W) with
location_precision_m = 3000 and "location_approx" in notes.
Sample codes are interpreted following the UKFDRS fuel constituents (heather live/dead canopy
and stem, moss, litter, organic layer); the code is kept in notes. Time = sampling hour, local
clock time (Europe/London). Some date-hour-code combinations have two samples (replicates);
both are kept. Blakey Ridge temperature/humidity -> covariates file.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "uk_calluna_diurnal"
CODES = {  # code -> (fuel_class, fuel_type, species, description)
    "ULC": ("live", "shrub", "Calluna vulgaris", "heather live canopy"),
    "LS": ("live", "shrub", "Calluna vulgaris", "heather live stem"),
    "UDC": ("dead", "fine_dead", "Calluna vulgaris", "heather dead canopy"),
    "DS": ("dead", "fine_dead", "Calluna vulgaris", "heather dead stem"),
    "M": ("live", "moss", None, "moss"),
    "L": ("dead", "litter", None, "litter"),
    "O": ("dead", "duff", None, "organic layer"),
}

if __name__ == "__main__":
    df = pd.read_csv(raw_dir(SOURCE_ID) / "Diurnal data.csv", encoding="utf-8-sig")
    df["rep"] = df.groupby(["Date", "Time", "Sample"]).cumcount() + 1
    c = df["Sample"].map(CODES)
    assert c.notna().all()
    out = pd.DataFrame({
        "source_record_id": df["Date"] + "|" + df["Time"].astype(str) + "|" + df["Sample"] + "|" + df["rep"].astype(str),
        "date": pd.to_datetime(df["Date"], format="%d/%m/%Y"),
        "time": df["Time"].map(lambda h: f"{int(h):02d}:00"),
        "timezone": "Europe/London",
        "lat": 54.39, "lon": -0.95, "location_precision_m": 3000,
        "country": "United Kingdom",
        "site_name": "Blakey Ridge area, North York Moors",
        "fuel_class": c.map(lambda x: x[0]),
        "fuel_type": c.map(lambda x: x[1]),
        "species": c.map(lambda x: x[2]),
        "moisture_pct": df["fmc"],
        "method": "oven_dry",
        "measured": True,
        "notes": ("dry_weight_basis; sample_code=" + df["Sample"] + " (interpreted: " + c.map(lambda x: x[3])
                  + "); replicate=" + df["rep"].astype(str)
                  + "; location_approx: no coords in source, placed at Blakey Ridge weather station area"),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)
    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "uk_calluna_diurnal: Blakey Ridge weather station at sampling hour (as provided)",
        "air_temp_c": df["BlakeyRidge_temp"], "rh_pct": df["BlakeyRidge_humidity"],
    })
    (NORM / "covariates_by_source").mkdir(parents=True, exist_ok=True)
    cov.to_parquet(NORM / "covariates_by_source" / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
