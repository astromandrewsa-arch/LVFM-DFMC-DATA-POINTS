"""Normalize RDS-2024-0052 (Annaburroo Station, NT, Aug 1986; CC0) to the observation schema.

Data/fire_data.csv repeats the burn-block fuel moisture ('fmc', percent, "recorded in a location
close to the burn block") on every fire-line measurement time; one observation is written per
distinct (block, date, fmc) -> F19 (20 Aug 1986, Themeda) 5.8 %, C064 (18 Aug 1986, Eriachne cut
to 50 %) 6.2 % and 6.5 %. Grass was 95 % cured (ocular) -> fuel_class dead, fuel_type grass;
curing % goes to covariates/notes only. Moisture basis is not stated in the metadata (CSIRO
grassland work normally uses oven-dry basis) -> notes "basis_unclear".
Weather (temp, RH, 10-m wind) at the measurement times are averaged per observation.
Fuel load: F19 fuel_samples.csv (t/ha -> kg/m2) is averaged; for C064 the fuht/fuwt columns look
swapped (height 2.2-4.3 'm', load 0.16-0.3 't/ha') so its load is not used.
Location: only "flood plain of the Mary River at Annaburroo Station" is given -> geocoded to the
station area, location_precision_m 10000, notes location_approx.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "annaburroo_fds_1986"
LAT, LON = -12.90, 131.67

if __name__ == "__main__":
    base = raw_dir(SOURCE_ID) / "RDS-2024-0052" / "Data"
    fd = pd.read_csv(base / "fire_data.csv")
    fs = pd.read_csv(base / "fuel_samples.csv")
    g = (fd.groupby(["blkid", "date", "treat", "fmc"], as_index=False)
         .agg(igntime=("igntime", "first"), temp=("temp", "mean"), rh=("rh", "mean"),
              aw10=("aw10", "mean"), awind=("awind", "mean"), cure=("cure", "first"), n=("fmc", "size")))
    print(g)
    load = fs[fs["blkid"] == "F19"]["fuwt"].mean() / 10.0  # t/ha -> kg/m2
    species = g["treat"].map({"T1": "Themeda australis (natural uncut)",
                              "E3": "Eriachne sp. (cut to 50% height)"})
    out = pd.DataFrame({
        "source_record_id": g["blkid"] + "@" + g["date"] + "_fmc" + g["fmc"].astype(str),
        "date": pd.to_datetime(g["date"], format="%m/%d/%Y"),
        "time": g["igntime"].str.slice(0, 5),
        "timezone": "Australia/Darwin",
        "lat": LAT, "lon": LON, "location_precision_m": 10000,
        "country": "Australia",
        "site_name": "Annaburroo Station (Mary River floodplain) burn block " + g["blkid"],
        "fuel_class": "dead", "fuel_type": "grass", "species": species,
        "moisture_pct": g["fmc"], "method": "oven_dry", "measured": True, "qa_flag": pd.NA,
        "notes": ("cured grass, curing_pct=" + g["cure"].astype(str) + " (ocular); basis_unclear"
                  + "; time=ignition time; location_approx; CSIRO 1986 Annaburroo experiment"),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)

    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "source_provided(RDS-2024-0052 fire_data.csv, measured at burn)",
        "air_temp_c": g["temp"], "rh_pct": g["rh"], "wind_10m_ms": g["aw10"], "wind_2m_ms": g["awind"],
        "curing_pct": g["cure"],
        "fuel_load_kg_m2": [load if b == "F19" else float("nan") for b in g["blkid"]],
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
