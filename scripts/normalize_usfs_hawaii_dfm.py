"""Normalize RDS-2026-0026 (Weise & Corcoran 2026): diurnal dead fuel moisture, Hawaii 1999-2001.

Two kinds of measurement:
1. all_hawaii_diurnal_fuel_moisture.csv - hourly destructive samples (2 per fuel per hour, ~96 h
   per site), oven-dried 85-95 C to constant weight; Moisture_content is % of dry mass. Only dead
   material, except 'Live ERAT'/'Live DENU6' (live grass, Pohakuloa 1999). Blank moisture = fuel
   had surface water and was not sampled -> dropped (not imputed).
   Grasses and uluhe fern were clipped from standing plants; Eucalyptus/pine needles are surface
   litter.
2. 10-h fuel-stick sensor readings co-located with the sampling: RAWS_2000_HI.csv (hourly
   Fuel_moisture_10hr at Schofield / PTA_East / Makua RAWS) and RAWS_2001_portable.csv
   (5-minute mean 10-h stick moisture from the portable station at the 2001 sites). Kept at
   full resolution (~10k rows), method fuel_stick.
Times are local Hawaii standard time (no DST). Site coordinates from
all_hawaii_dfm_site_locations.csv; samples were taken within ~100 m of the station.
Co-measured weather (F -> C, mph -> m/s, kW/m2 -> W/m2) goes to covariates_by_source.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_hawaii_dfm"
MPH = 0.44704
F2C = lambda f: (pd.to_numeric(f, errors="coerce") - 32) * 5 / 9

GRASS = {"ANVI2", "SCCO10", "PECI", "HOLA", "PESE3", "DENU6", "URMA3", "ERAT"}
LITTER = {"EURO2", "PITA&PIEL", "PIRA2"}


def read(path):
    x = pd.read_csv(path, encoding="utf-8-sig")
    x.columns = [c.strip() for c in x.columns]
    for c in x.columns:
        if x[c].dtype == object or str(x[c].dtype).startswith("str"):
            x[c] = x[c].str.strip()
    return x


def hhmm(v):
    v = pd.to_numeric(v, errors="coerce")
    return v.map(lambda t: pd.NA if pd.isna(t) else f"{int(t) // 100:02d}:{int(t) % 100:02d}")


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    sites = read(find(d, "all_hawaii_dfm_site_locations.csv"))
    sp = pd.read_csv(find(d, "fuel_to_species.csv"), encoding="utf-8-sig")
    sp.columns = [c.strip().lower() for c in sp.columns]
    spmap = dict(zip(sp["fuel"].str.strip(), sp["species"].str.strip()))
    site_xy = {r.Site: (r.Lat, r.Long, r.Elev) for r in sites.itertuples()}
    site_xy["Makua_Valley"] = site_xy["Makua"]  # RAWS name for the Makua sampling site

    # ---- 1. destructive samples
    fm = read(find(d, "all_hawaii_diurnal_fuel_moisture.csv"))
    fm["_row"] = range(len(fm))
    fm = fm[fm["Moisture_content"].notna()].copy()
    code = fm["Fuel_species"].str.strip()
    live = code.str.startswith("Live ")
    base = code.str.replace("Live ", "", regex=False)
    fuel_type = pd.Series("other", index=fm.index)
    fuel_type[base.isin(GRASS)] = "grass"
    fuel_type[base.isin(LITTER)] = "litter"
    fuel_type[base == "DILI"] = "dead_foliage"
    xy = fm["Site"].map(site_xy)
    date = pd.to_datetime(dict(year=fm["Year"], month=fm["Month"], day=fm["Day"]), errors="coerce")
    a = pd.DataFrame({
        "source_record_id": "fm#" + fm["_row"].astype(str),
        "date": date, "time": hhmm(fm["Time"]), "timezone": "Pacific/Honolulu",
        "lat": xy.str[0], "lon": xy.str[1], "location_precision_m": 100.0, "country": "USA",
        "site_name": fm["Site"] + " (" + fm["Island"] + ", HI)",
        "fuel_class": live.map({True: "live", False: "dead"}),
        "fuel_type": fuel_type,
        "species": base.map(spmap),
        "moisture_pct": fm["Moisture_content"], "method": "oven_dry", "measured": True,
        "notes": ("gravimetric, dry basis; fuel_code=" + code
                  + base.map(lambda c: "; surface litter" if c in LITTER else "; clipped standing")
                  + "; samples within ~100 m of weather station"),
    })
    a["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in a["source_record_id"]]
    cov_a = pd.DataFrame({
        "observation_id": a["observation_id"], "cov_source": "source_measured(sling psychrometer at sample)",
        "obs_temp_c": F2C(fm["Dry-bulb-temp"]), "obs_wetbulb_c": F2C(fm["Wet_bulb_temp"]),
        "obs_rh_pct": pd.to_numeric(fm["Relative_humidity"], errors="coerce"),
        "obs_wind_ms": pd.to_numeric(fm["Wind_velocity"], errors="coerce") * MPH,
        "obs_wind_dir_deg": pd.to_numeric(fm["Wind_direction"], errors="coerce"),
        "elevation_m": xy.str[2].astype(float),
    })

    # ---- 2a. RAWS 2000 hourly 10-h stick
    r0 = read(find(d, "RAWS_2000_HI.csv"))
    r0["_row"] = range(len(r0))
    r0 = r0[pd.to_numeric(r0["Fuel_moisture_10hr"], errors="coerce").notna()].copy()
    xy0 = r0["Station_Name"].str.strip().map(site_xy)
    b = pd.DataFrame({
        "source_record_id": "raws2000#" + r0["_row"].astype(str),
        "date": pd.to_datetime(dict(year=r0["Year"], month=r0["Month"], day=r0["Day"]), errors="coerce"),
        "time": r0["Hour"].map(lambda h: f"{int(h):02d}:00"), "timezone": "Pacific/Honolulu",
        "lat": xy0.str[0], "lon": xy0.str[1], "location_precision_m": 100.0, "country": "USA",
        "site_name": r0["Station_Name"].str.strip() + " RAWS " + r0["Station_Number"].astype(str) + " (" + r0["Island"] + ", HI)",
        "fuel_class": "dead", "fuel_type": "10hr", "species": pd.NA,
        "moisture_pct": pd.to_numeric(r0["Fuel_moisture_10hr"], errors="coerce"),
        "method": "fuel_stick", "measured": True,
        "notes": "RAWS 10-h fuel stick sensor, hourly; data via WRCC RAWS archive as packaged in RDS-2026-0026",
    })
    b["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in b["source_record_id"]]
    cov_b = pd.DataFrame({
        "observation_id": b["observation_id"], "cov_source": "station_colocated(RAWS)",
        "obs_temp_c": F2C(r0["Air_temp"]), "obs_fuel_temp_c": F2C(r0["Fuel_temp"]),
        "obs_rh_pct": pd.to_numeric(r0["Relative_humidity"], errors="coerce"),
        "obs_wind_ms": pd.to_numeric(r0["Wind_speed"], errors="coerce") * MPH,
        "obs_wind_dir_deg": pd.to_numeric(r0["Wind_direction"], errors="coerce"),
        "elevation_m": xy0.str[2].astype(float),
    })

    # ---- 2b. portable station 2001, 5-minute 10-h stick
    r1 = read(find(d, "RAWS_2001_portable.csv"))
    r1["_row"] = range(len(r1))
    stick = pd.to_numeric(r1["Mean_10hr_stick_fuel_moisture"], errors="coerce")
    r1 = r1[stick.notna()].copy()
    stick = stick[r1.index]
    xy1 = r1["Site"].str.strip().map(site_xy)
    no_site = xy1.isna()
    t = pd.to_numeric(r1["TIME"], errors="coerce")
    c = pd.DataFrame({
        "source_record_id": "portable2001#" + r1["_row"].astype(str),
        "date": pd.to_datetime(dict(year=r1["YEAR"], month=r1["Month"], day=r1["Day"]), errors="coerce"),
        "time": hhmm(t.where(t < 2400)), "timezone": "Pacific/Honolulu",
        "lat": xy1.str[0], "lon": xy1.str[1], "location_precision_m": 100.0, "country": "USA",
        "site_name": r1["Site"].str.strip() + " portable wx station (" + r1["Island"] + ", HI)",
        "fuel_class": "dead", "fuel_type": "10hr", "species": pd.NA, "moisture_pct": stick,
        "method": "fuel_stick", "measured": True,
        "notes": ("portable station 10-h fuel stick, mean over 5-min interval ending at time; min="
                  + r1["Min_10hr_stick_fuel_moisture"].astype(str) + " max="
                  + r1["Max_10hr_stick_fuel_moisture"].astype(str)),
    })
    c.loc[t.ge(2400).values, "notes"] = c.loc[t.ge(2400).values, "notes"] + "; time_raw=2400"
    c["qa_flag"] = pd.Series(pd.NA, index=c.index, dtype="string")
    c.loc[no_site.values, "qa_flag"] = "no_site_coords"
    c["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in c["source_record_id"]]
    cov_c = pd.DataFrame({
        "observation_id": c["observation_id"], "cov_source": "station_colocated(portable)",
        "obs_temp_c": F2C(r1["AIR_TEMP"]), "obs_fuel_temp_c": F2C(r1["Mean_Fuel_temp"]),
        "obs_rh_min_pct": pd.to_numeric(r1["Min_relative_humidity"], errors="coerce"),
        "obs_rh_max_pct": pd.to_numeric(r1["Max_relative_humidity"], errors="coerce"),
        "obs_wind_ms": pd.to_numeric(r1["Wind_velocity"], errors="coerce") * MPH,
        "obs_wind_dir_deg": pd.to_numeric(r1["Mean_wind_direction"], errors="coerce"),
        "obs_solar_wm2": pd.to_numeric(r1["Mean_incoming_solar_radiation"], errors="coerce") * 1000,
        "elevation_m": xy1.str[2].astype(float),
    })

    # Pu_u_KoleKole (Molokai) has station data but no coordinates in the site table (no fuel
    # samples were taken there) -> dropped rather than geocoded from a name only.
    keep = c["lat"].notna().values
    c, cov_c = c[keep], cov_c[keep]
    out = pd.concat([a, b, c], ignore_index=True)
    if "qa_flag" not in out:
        out["qa_flag"] = pd.NA
    out["qa_flag"] = out["qa_flag"].astype("string")
    out.loc[out["moisture_pct"] <= 0, "qa_flag"] = "nonpositive_moisture"
    print("rows: samples", len(a), "raws2000", len(b), "portable2001", len(c),
          "| dropped no-site", int(no_site.sum()))
    finalize(out, SOURCE_ID)
    cov = pd.concat([cov_a, cov_b, cov_c], ignore_index=True)
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
