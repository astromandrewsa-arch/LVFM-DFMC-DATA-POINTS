"""Normalize figshare 32594238 (Kane 2026, CC-BY-4.0): canopy foliar moisture along vertical
crown gradients of coast redwood, Douglas-fir and Sitka spruce, NW California (2024-2025).

Sheet 'FMC': one row per bagged foliage sample (tree x crown height class x foliage age).
FMC (%) = (WW - DW) / DW * 100 (dry basis; verified against WW/DW). lat/long are WGS84 per the
metadata sheet but longitudes are stored positive -> negated. 'Time' is a sampling window
(e.g. '1200-1420'): its start is used as time, the window is kept in notes. Crew initials are
not carried over. Sheet 'Morphology' (leaf mass area etc.) is not moisture and is not ingested.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "figshare_kane_canopy_fmc"
SPP = {"SESE": "Sequoia sempervirens", "PSME": "Pseudotsuga menziesii", "PISI": "Picea sitchensis"}

if __name__ == "__main__":
    f = next(raw_dir(SOURCE_ID).glob("*.xlsx"))
    df = pd.read_excel(f, sheet_name="FMC")
    df = df[pd.to_numeric(df["FMC"], errors="coerce").notna()].copy()
    df["_row"] = range(len(df))
    win = df["Time"].astype(str).str.strip()
    start = win.str.extract(r"^(\d{3,4})")[0]
    time = start.map(lambda s: pd.NA if pd.isna(s) else f"{int(s) // 100:02d}:{int(s) % 100:02d}")
    calc = (df["WW"] - df["DW"]) / df["DW"] * 100
    qa = pd.Series(pd.NA, index=df.index, dtype="string")
    qa[(calc - df["FMC"]).abs() > 1] = "src_pct_mismatch"
    age = df["FoliageAge"].map({"N": "new (<1 yr)", "O": "old (~2-4 yr)"})
    out = pd.DataFrame({
        "source_record_id": df["ID"].astype(str) + "|" + df["SamHtCat"].astype(str) + "|" + df["FoliageAge"].astype(str) + "#" + df["_row"].astype(str),
        "date": pd.to_datetime(df["Date"], errors="coerce"), "time": time, "timezone": "America/Los_Angeles",
        "lat": df["lat"], "lon": -df["long"].abs(), "location_precision_m": 10.0, "country": "USA",
        "site_name": "tree " + df["ID"].astype(str) + " (NW California)",
        "fuel_class": "live", "fuel_type": "tree_foliage", "species": df["SPP"].map(SPP),
        "moisture_pct": df["FMC"], "method": "oven_dry", "measured": True, "qa_flag": qa,
        "notes": ("foliar moisture, dry basis; foliage_age=" + age + "; crown_position=" + df["SamHtCat"].astype(str)
                  + "; sample_height_m=" + df["SamHt"].astype(str) + "; tree_height_m=" + df["Ht"].astype(str)
                  + "; time_window=" + win),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
    cov = pd.DataFrame({"observation_id": out["observation_id"], "cov_source": "source_measured(tree)",
                        "sample_height_m": pd.to_numeric(df["SamHt"], errors="coerce"),
                        "tree_height_m": pd.to_numeric(df["Ht"], errors="coerce"),
                        "crown_base_height_m": pd.to_numeric(df["CBH"], errors="coerce"),
                        "dbh_m": pd.to_numeric(df["DBH"], errors="coerce")})
    (NORM / "covariates_by_source").mkdir(parents=True, exist_ok=True)
    cov.to_parquet(NORM / "covariates_by_source" / f"{SOURCE_ID}.parquet", index=False)
