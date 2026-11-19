"""Attach covariates to every observation -> data/normalized/weather_join.parquet/ (dataset dir,
one file per observation file; keyed by observation_id).

Column groups (prefix = provenance):
  src_*    covariates provided by the source itself (station co-located for MADIS RAWS; the
           ERA5-Land-derived values shipped with Globe-LFMC 2.0). See covariates_by_source/.
  pw_*     NASA POWER daily (MERRA-2 / CERES), global, sampled at the POWER cell containing the
           site, on the observation's local date.
  gm_*     gridMET daily (CONUS only), 1/24 deg cell containing the site.
  dem_*, lc_*  static terrain (Copernicus GLO-30 DEM) and land cover (ESA WorldCover 2021),
           from fetch_terrain.py, when available.
  ERA5-Land (era5l_*) is added when a CDS key is available (see REPORT.md).

Derived features (for both pw_ and gm_): precipitation same day and 3/7/14/30-day totals
(ending on the observation date, inclusive), days since >= 1 mm rain (capped at 365),
vapor pressure deficit, and dew point where not supplied.
Units: degC, mm, m/s, %, W/m2 (or MJ/m2/day where noted), kPa for VPD.
"""
from __future__ import annotations

import glob
import io
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from common import BY_SOURCE, NORM, RAW
from sites import site_key

OUT = NORM / "weather_join.parquet"
POWER_RAW = RAW / "nasa_power"
POWER_DERIVED = POWER_RAW / "derived"
GM_RAW = RAW / "gridmet" / "extracted"
GM_DERIVED = RAW / "gridmet" / "derived"


def es_kpa(t_c):
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))


def add_precip_features(df: pd.DataFrame, key: str, pcol: str, prefix: str) -> pd.DataFrame:
    df = df.sort_values([key, "date"])
    g = df.groupby(key, sort=False)[pcol]
    df[f"{prefix}precip_1d_mm"] = df[pcol]
    for n in (3, 7, 14, 30):
        df[f"{prefix}precip_{n}d_mm"] = g.transform(lambda s: s.rolling(n, min_periods=n).sum())
    wet = (df[pcol] >= 1.0)
    # days since last wet day (0 = rained >= 1 mm that day)
    grp = wet.groupby(df[key]).cumsum()
    cnt = df.groupby([df[key], grp]).cumcount()
    first_seen = grp == 0  # no rain yet in record -> unknown
    dsr = cnt.where(~first_seen).astype("float64")
    df[f"{prefix}days_since_rain"] = dsr.clip(upper=365)
    return df


# ---------------------------------------------------------------- NASA POWER
def parse_power(path: Path) -> pd.DataFrame:
    txt = path.read_text()
    body = txt.split("-END HEADER-", 1)[1]
    d = pd.read_csv(io.StringIO(body))
    d = d.replace(-999.0, np.nan)
    d["date"] = pd.to_datetime(d["YEAR"].astype(str) + d["DOY"].astype(str).str.zfill(3), format="%Y%j")
    d["power_cell"] = path.stem
    return d


def build_power_derived():
    files = sorted(glob.glob(str(POWER_RAW / "*.csv")))
    POWER_DERIVED.mkdir(parents=True, exist_ok=True)
    done_marker = POWER_DERIVED / "_cells.txt"
    if done_marker.exists() and set(done_marker.read_text().split()) == {Path(f).stem for f in files}:
        return
    parts = []
    for f in files:
        d = parse_power(Path(f))
        out = pd.DataFrame({"power_cell": d["power_cell"], "date": d["date"],
                            "pw_tmean_c": d["T2M"], "pw_tmax_c": d["T2M_MAX"], "pw_tmin_c": d["T2M_MIN"],
                            "pw_rh_pct": d["RH2M"], "pw_dewpoint_c": d["T2MDEW"], "pw_q2m_gkg": d["QV2M"],
                            "pw_wind_ms": d["WS2M"], "pw_wind_max_ms": d["WS2M_MAX"], "pw_wind_dir_deg": d["WD2M"],
                            "pw_solar_mj_m2_day": d["ALLSKY_SFC_SW_DWN"], "pw_soil_wet_top": d["GWETTOP"],
                            "pw_soil_wet_root": d["GWETROOT"], "pw_snow_depth_cm": d["SNODP"],
                            "pw_surface_pressure_kpa": d["PS"], "_p": d["PRECTOTCORR"]})
        out["pw_vpd_kpa"] = es_kpa(out["pw_tmean_c"]) * (1 - out["pw_rh_pct"] / 100)
        out["pw_vpd_max_kpa"] = es_kpa(out["pw_tmax_c"]) - es_kpa(out["pw_dewpoint_c"])
        out = add_precip_features(out, "power_cell", "_p", "pw_").drop(columns="_p")
        parts.append(out)
    allp = pd.concat(parts, ignore_index=True)
    allp["year"] = allp["date"].dt.year
    for y, g in allp.groupby("year"):
        g.drop(columns="year").to_parquet(POWER_DERIVED / f"{y}.parquet", index=False, compression="zstd")
    done_marker.write_text("\n".join(Path(f).stem for f in files))


# ---------------------------------------------------------------- gridMET
GM_VARS = {"pr": "_p", "tmmx": "gm_tmax_c", "tmmn": "gm_tmin_c", "rmax": "gm_rh_max_pct",
           "rmin": "gm_rh_min_pct", "vs": "gm_wind_ms", "th": "gm_wind_dir_deg", "srad": "gm_solar_wm2",
           "vpd": "gm_vpd_kpa", "fm100": "gm_fm100_pct", "fm1000": "gm_fm1000_pct"}


def gridmet_year(y: int) -> pd.DataFrame | None:
    out = GM_DERIVED / f"{y}.parquet"
    need = [GM_RAW / f"{v}_{yy}.parquet" for v in GM_VARS for yy in (y,)]
    if out.exists() and all(p.exists() and p.stat().st_mtime < out.stat().st_mtime for p in need):
        return pd.read_parquet(out)
    if not all(p.exists() for p in need):
        return None
    frames = []
    for yy in (y - 1, y):
        cols = None
        for v, name in GM_VARS.items():
            p = GM_RAW / f"{v}_{yy}.parquet"
            if not p.exists():
                cols = None
                break
            d = pd.read_parquet(p).rename(columns={v: name}).set_index(["site_key", "date"])
            cols = d if cols is None else cols.join(d, how="outer")
        if cols is not None:
            frames.append(cols.reset_index())
    df = pd.concat(frames, ignore_index=True)
    for c in ("gm_tmax_c", "gm_tmin_c"):
        df[c] = df[c] - 273.15
    df["gm_tmean_c"] = (df["gm_tmax_c"] + df["gm_tmin_c"]) / 2
    df = add_precip_features(df, "site_key", "_p", "gm_").drop(columns="_p")
    df = df[df["date"].dt.year == y]
    GM_DERIVED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False, compression="zstd")
    return df


# ---------------------------------------------------------------- join
def obs_files():
    return sorted(glob.glob(str(BY_SOURCE / "*.parquet")) + glob.glob(str(BY_SOURCE / "*" / "*.parquet")))


def source_covariates(sid: str, part: str | None) -> pd.DataFrame | None:
    base = NORM / "covariates_by_source"
    p = base / sid / f"{part}.parquet" if part else base / f"{sid}.parquet"
    if not p.exists():
        return None
    c = pd.read_parquet(p)
    return c.rename(columns={k: (k if k == "observation_id" else f"src_{k}") for k in c.columns})


def main():
    build_power_derived()
    sites = pd.read_parquet(NORM / "sites.parquet")[["site_key", "power_cell", "in_conus"]]
    terrain_p = NORM / "site_static.parquet"
    terrain = pd.read_parquet(terrain_p) if terrain_p.exists() else None
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    gm_cache: dict[int, pd.DataFrame | None] = {}
    pw_cache: dict[int, pd.DataFrame | None] = {}
    stats = []
    for f in obs_files():
        f = Path(f)
        if f.parent == BY_SOURCE:
            sid, part, name = f.stem, None, f.stem
        else:
            sid, part, name = f.parent.name, f.stem, f"{f.parent.name}-{f.stem}"
        o = pd.read_parquet(f, columns=["observation_id", "lat", "lon", "date", "country"])
        o["site_key"] = site_key(o["lat"].values, o["lon"].values).values
        o["date"] = pd.to_datetime(o["date"])
        o = o.merge(sites, on="site_key", how="left")
        o["year"] = o["date"].dt.year
        res = []
        for y, g in o.groupby("year"):
            y = int(y)
            if y not in pw_cache:
                p = POWER_DERIVED / f"{y}.parquet"
                pw_cache[y] = pd.read_parquet(p) if p.exists() else None
            if pw_cache[y] is not None:
                g = g.merge(pw_cache[y], on=["power_cell", "date"], how="left")
            if g["in_conus"].any():
                if y not in gm_cache:
                    gm_cache[y] = gridmet_year(y)
                if gm_cache[y] is not None:
                    g = g.merge(gm_cache[y], on=["site_key", "date"], how="left")
            res.append(g)
        w = pd.concat(res, ignore_index=True)
        sc = source_covariates(sid, part)
        if sc is not None:
            w = w.merge(sc, on="observation_id", how="left")
        if terrain is not None:
            w = w.merge(terrain, on="site_key", how="left")
        w = w.drop(columns=["lat", "lon", "date", "country", "year", "in_conus"])
        w["has_power"] = w.filter(like="pw_tmean").notna().any(axis=1) if "pw_tmean_c" in w else False
        w["has_gridmet"] = w["gm_tmax_c"].notna() if "gm_tmax_c" in w else False
        w["has_source_weather"] = w.filter(regex="^src_(obs_temp_c|tmean_c)$").notna().any(axis=1)
        w.to_parquet(OUT / f"{name}.parquet", index=False, compression="zstd")
        stats.append((name, len(w), int(w["has_power"].sum()), int(np.sum(w["has_gridmet"])),
                      int(w["has_source_weather"].sum())))
        # bound memory: keep only a couple of years cached
        if len(gm_cache) > 3:
            for k in sorted(gm_cache)[:-3]:
                gm_cache.pop(k)
        if len(pw_cache) > 6:
            for k in sorted(pw_cache)[:-6]:
                pw_cache.pop(k)
    st = pd.DataFrame(stats, columns=["file", "rows", "has_power", "has_gridmet", "has_source_weather"])
    st.to_csv(NORM / "weather_join_coverage.csv", index=False)
    print(st.to_string())


if __name__ == "__main__":
    main()
