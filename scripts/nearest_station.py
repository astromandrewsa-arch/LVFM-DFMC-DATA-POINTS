"""Nearest-station daily weather for sites without co-located weather.

Builds
  data/raw/nearest/derived/<year>.parquet         station_id, date, ns_* daily features
  data/normalized/site_nearest_station.parquet    site_key -> up to 3 candidate stations
Candidates: RAWS (FEMS daily summaries) within 40 km and |elevation diff| <= 600 m, nearest
first; then GHCN-Daily within 75 km. join_weather.py takes, per observation, the first candidate
with data on the observation date and records its id, network, distance and elevation difference.

ns_ features: tmin_c, tmax_c, rh_min_pct, rh_max_pct (RAWS only), precip_1d/3d/7d/14d/30d_mm,
days_since_rain, wind_max_ms, solar_max_wm2 (RAWS), vpd_max_kpa (RAWS), snow_depth_mm (GHCN).
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

from common import NORM, RAW
from fetch_fems_raws_daily import haversine_km
from fetch_ghcnd import load_stations
from join_weather import add_precip_features

DER = RAW / "nearest" / "derived"


def load_raws(files) -> pd.DataFrame:
    parts = []
    for f in files:
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        if d.empty:
            continue
        d = d[d["ObservationType"].astype(str).str.upper().str.startswith("O")]
        parts.append(pd.DataFrame({
            "station_id": "RAWS:" + d["StationId"].astype(str),
            "date": pd.to_datetime(d["Date"], errors="coerce"),
            "ns_tmin_c": (pd.to_numeric(d["TemperatureMin(F)"], errors="coerce") - 32) / 1.8,
            "ns_tmax_c": (pd.to_numeric(d["TemperatureMax(F)"], errors="coerce") - 32) / 1.8,
            "ns_rh_min_pct": pd.to_numeric(d["RelativeHumidityMin(%)"], errors="coerce"),
            "ns_rh_max_pct": pd.to_numeric(d["RelativeHumidityMax(%)"], errors="coerce"),
            "_p": pd.to_numeric(d["Precipitation24hr(in)"], errors="coerce") * 25.4,
            "ns_wind_max_ms": pd.to_numeric(d["WindSpeedMax(mph)"], errors="coerce") * 0.44704,
            "ns_solar_max_wm2": pd.to_numeric(d["MaxSolarRadiation(W/m2)"], errors="coerce"),
            "ns_vpd_max_kpa": pd.to_numeric(d["VPDMax(Pa)"], errors="coerce") / 1000,
        }))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def load_ghcnd(files) -> pd.DataFrame:
    parts = []
    for f in files:
        try:
            d = pd.read_csv(f, usecols=lambda c: c in {"STATION", "DATE", "PRCP", "TMAX", "TMIN", "SNWD"},
                            low_memory=False)
        except Exception:
            continue
        g = lambda c: pd.to_numeric(d[c], errors="coerce") if c in d else np.nan  # noqa: E731
        parts.append(pd.DataFrame({
            "station_id": "GHCND:" + d["STATION"].astype(str),
            "date": pd.to_datetime(d["DATE"], errors="coerce"),
            "ns_tmin_c": g("TMIN") / 10, "ns_tmax_c": g("TMAX") / 10,
            "_p": g("PRCP") / 10, "ns_snow_depth_mm": g("SNWD"),
        }))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def build_derived(chunk: int = 150):
    """Process stations in chunks to bound memory; writes DER/<year>/<chunk>.parquet."""
    import shutil
    if DER.exists():
        shutil.rmtree(DER)
    DER.mkdir(parents=True)
    raws = sorted(glob.glob(str(RAW / "fems_raws_daily" / "daily" / "*.csv")))
    gh = sorted(glob.glob(str(RAW / "ghcnd" / "access" / "*.csv")))
    jobs = [("r", raws[i:i + chunk]) for i in range(0, len(raws), chunk)]
    jobs += [("g", gh[i:i + chunk]) for i in range(0, len(gh), chunk)]
    total = 0
    for n, (kind, files) in enumerate(jobs):
        df = load_raws(files) if kind == "r" else load_ghcnd(files)
        if df.empty:
            continue
        df = df.dropna(subset=["date"]).drop_duplicates(["station_id", "date"])
        df = add_precip_features(df, "station_id", "_p", "ns_").drop(columns="_p")
        for c in df.columns:
            if c.startswith("ns_"):
                df[c] = df[c].astype("float32")
        df["year"] = df["date"].dt.year
        for y, g in df.groupby("year"):
            (DER / str(y)).mkdir(exist_ok=True)
            g.drop(columns="year").to_parquet(DER / str(y) / f"{kind}{n:04d}.parquet", index=False, compression="zstd")
        total += len(df)
        del df
    print("station-days", total)


def build_site_map():
    sites = pd.read_parquet(NORM / "sites.parquet")
    static_p = NORM / "site_static.parquet"
    if static_p.exists():
        sites = sites.merge(pd.read_parquet(static_p)[["site_key", "dem_elevation_m"]], on="site_key", how="left")
    else:
        sites["dem_elevation_m"] = np.nan
    raws = pd.read_csv(RAW / "fems_raws_daily" / "stations.csv")
    raws = raws.assign(station_id="RAWS:" + raws.station_id.astype(str), elev_m=raws.elevation * 0.3048,
                       lat=raws.latitude, lon=raws.longitude)
    have_raws = {Path(f).stem for f in glob.glob(str(RAW / "fems_raws_daily" / "daily" / "*.csv"))}
    raws = raws[raws.station_id.str[5:].isin(have_raws)]
    gh = load_stations(RAW / "ghcnd" / "ghcnd-stations.txt")
    have_gh = {Path(f).stem for f in glob.glob(str(RAW / "ghcnd" / "access" / "*.csv"))}
    gh = gh[gh.id.isin(have_gh)].assign(station_id=lambda x: "GHCND:" + x.id, elev_m=lambda x: x.elev)
    rows = []
    for s in sites.itertuples():
        cands = []
        for net, tab, km in (("RAWS", raws, 40), ("GHCND", gh, 75)):
            box = tab[tab.lat.between(s.lat - 1, s.lat + 1) & tab.lon.between(s.lon - 1.5, s.lon + 1.5)]
            if box.empty:
                continue
            dist = haversine_km(s.lat, s.lon, box.lat.values, box.lon.values)
            de = box.elev_m.values - (s.dem_elevation_m if np.isfinite(s.dem_elevation_m) else np.nan)
            ok = dist <= km
            if net == "RAWS":
                ok &= ~(np.abs(de) > 600)
            for i in np.argsort(dist):
                if ok[i]:
                    cands.append((box.station_id.values[i], net, round(float(dist[i]), 2),
                                  None if not np.isfinite(de[i]) else round(float(de[i]), 1)))
        for rank, c in enumerate(cands[:3], 1):
            rows.append((s.site_key, rank, *c))
    m = pd.DataFrame(rows, columns=["site_key", "rank", "station_id", "network", "distance_km", "elev_diff_m"])
    m.to_parquet(NORM / "site_nearest_station.parquet", index=False)
    print("sites with a station:", m.site_key.nunique(), "of", len(sites))


if __name__ == "__main__":
    build_derived()
    build_site_map()
