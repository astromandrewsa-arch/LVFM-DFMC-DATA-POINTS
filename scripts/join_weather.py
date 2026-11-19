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


def _power_frame(f) -> pd.DataFrame:
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
    return out


def build_power_derived(chunk: int = 150):
    """Derived POWER features, written as POWER_DERIVED/<year>/<chunk>.parquet (chunked for memory)."""
    files = sorted(glob.glob(str(POWER_RAW / "*.csv")))
    done_marker = POWER_DERIVED / "_cells.txt"
    if done_marker.exists() and set(done_marker.read_text().split()) == {Path(f).stem for f in files}:
        return
    if POWER_DERIVED.exists():
        shutil.rmtree(POWER_DERIVED)
    POWER_DERIVED.mkdir(parents=True)
    for n in range(0, len(files), chunk):
        allp = pd.concat([_power_frame(f) for f in files[n:n + chunk]], ignore_index=True)
        allp = add_precip_features(allp, "power_cell", "_p", "pw_").drop(columns="_p")
        for c in allp.columns:
            if c.startswith("pw_"):
                allp[c] = allp[c].astype("float32")
        allp["year"] = allp["date"].dt.year
        for y, g in allp.groupby("year"):
            (POWER_DERIVED / str(y)).mkdir(exist_ok=True)
            g.drop(columns="year").to_parquet(POWER_DERIVED / str(y) / f"c{n:05d}.parquet", index=False, compression="zstd")
        del allp
    done_marker.write_text("\n".join(Path(f).stem for f in files))


# ---------------------------------------------------------------- gridMET
GM_VARS = {"pr": "_p", "tmmx": "gm_tmax_c", "tmmn": "gm_tmin_c", "rmax": "gm_rh_max_pct",
           "rmin": "gm_rh_min_pct", "vs": "gm_wind_ms", "th": "gm_wind_dir_deg", "srad": "gm_solar_wm2",
           "vpd": "gm_vpd_kpa", "fm100": "gm_fm100_pct", "fm1000": "gm_fm1000_pct"}


def gm_cell(lat, lon) -> pd.Series:
    """gridMET 1/24-deg cell id 'row_col' (grid origin 49.4N, 124.7667W)."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    r = np.round((49.4 - lat) * 24).astype(int)
    c = np.round((lon + 124.7666667) * 24).astype(int)
    return pd.Series(r.astype(str)) + "_" + pd.Series(c.astype(str))


def gridmet_year(y: int) -> pd.DataFrame | None:
    out = GM_DERIVED / f"{y}.parquet"
    need = [GM_RAW / f"{v}_{y}.parquet" for v in GM_VARS]
    prev = [GM_RAW / f"{v}_{y - 1}.parquet" for v in GM_VARS]
    prev_ok = y <= 1979 or all(p.exists() for p in prev)
    if (out.exists() and prev_ok
            and all(p.exists() and p.stat().st_mtime < out.stat().st_mtime for p in need + (prev if y > 1979 else []))):
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
            d = pd.read_parquet(p).rename(columns={v: name})
            ll = d["site_key"].str.split(",", expand=True).astype(float)
            d["gm_cell"] = gm_cell(ll[0], ll[1]).values
            d = d.drop(columns="site_key").drop_duplicates(["gm_cell", "date"]).set_index(["gm_cell", "date"])
            cols = d if cols is None else cols.join(d, how="outer")
        if cols is not None:
            frames.append(cols.reset_index())
    df = pd.concat(frames, ignore_index=True)
    for c in ("gm_tmax_c", "gm_tmin_c"):
        df[c] = df[c] - 273.15
    df["gm_tmean_c"] = (df["gm_tmax_c"] + df["gm_tmin_c"]) / 2
    df = add_precip_features(df, "gm_cell", "_p", "gm_").drop(columns="_p")
    df = df[df["date"].dt.year == y]
    if prev_ok:  # only cache once the lookback year is available
        GM_DERIVED.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, index=False, compression="zstd")
    return df


# ---------------------------------------------------------------- nearest station
NS_DERIVED = RAW / "nearest" / "derived"
NO_NEAREST_STATION = {"madis_raws"}  # already has co-located station weather


def attach_nearest(g: pd.DataFrame, ns_map: pd.DataFrame, ns: pd.DataFrame) -> pd.DataFrame:
    """Per row, take the first of up to 3 ranked stations with data on that date."""
    g = g.reset_index(drop=True)
    cols = [c for c in ns.columns if c.startswith("ns_")]
    meta = ["station_id", "network", "distance_km", "elev_diff_m"]
    out = pd.DataFrame(index=g.index, columns=cols + meta, dtype="object")
    filled = pd.Series(False, index=g.index)
    for rank in (1, 2, 3):
        m = ns_map[ns_map["rank"] == rank][["site_key"] + meta]
        gg = g[["site_key", "date"]].merge(m, on="site_key", how="left").merge(ns, on=["station_id", "date"], how="left")
        has = gg[cols].notna().any(axis=1) & ~filled
        out.loc[has, cols + meta] = gg.loc[has, cols + meta].values
        filled |= has
    out = out.rename(columns={c: f"ns_{c}" for c in meta})
    for c in cols + ["ns_distance_km", "ns_elev_diff_m"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return pd.concat([g, out], axis=1)


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
    ns_cache: dict[int, pd.DataFrame | None] = {}
    ns_map_p = NORM / "site_nearest_station.parquet"
    ns_map = pd.read_parquet(ns_map_p) if ns_map_p.exists() else None
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
        o["gm_cell"] = gm_cell(o["lat"], o["lon"]).values
        o["year"] = o["date"].dt.year
        res = []
        for y, g in o.groupby("year"):
            y = int(y)
            if y not in pw_cache:
                p = POWER_DERIVED / str(y)
                pw_cache[y] = pd.read_parquet(p) if p.exists() else None
            if pw_cache[y] is not None:
                g = g.merge(pw_cache[y], on=["power_cell", "date"], how="left")
            if g["in_conus"].any():
                if y not in gm_cache:
                    gm_cache[y] = gridmet_year(y)
                if gm_cache[y] is not None:
                    g = g.merge(gm_cache[y], on=["gm_cell", "date"], how="left")
            if ns_map is not None and sid not in NO_NEAREST_STATION:
                if y not in ns_cache:
                    p = NS_DERIVED / str(y)
                    ns_cache[y] = pd.read_parquet(p) if p.exists() else None
                if ns_cache[y] is not None:
                    g = attach_nearest(g, ns_map, ns_cache[y])
            res.append(g)
        w = pd.concat(res, ignore_index=True)
        sc = source_covariates(sid, part)
        if sc is not None:
            w = w.merge(sc, on="observation_id", how="left")
        if terrain is not None:
            w = w.merge(terrain, on="site_key", how="left")
        w = w.drop(columns=["lat", "lon", "date", "country", "year", "in_conus", "gm_cell"])
        w["has_power"] = w.filter(like="pw_tmean").notna().any(axis=1) if "pw_tmean_c" in w else False
        w["has_gridmet"] = w["gm_tmax_c"].notna() if "gm_tmax_c" in w else False
        w["has_source_weather"] = w.filter(regex="^src_(obs_temp_c|tmean_c)$").notna().any(axis=1)
        w["has_nearest_station"] = w["ns_tmax_c"].notna() | w["ns_precip_1d_mm"].notna() if "ns_tmax_c" in w else False
        w.to_parquet(OUT / f"{name}.parquet", index=False, compression="zstd")
        stats.append((name, len(w), int(w["has_power"].sum()), int(np.sum(w["has_gridmet"])),
                      int(w["has_source_weather"].sum()), int(np.sum(w["has_nearest_station"]))))
        # bound memory: keep only a couple of years cached
        if len(gm_cache) > 3:
            for k in sorted(gm_cache)[:-3]:
                gm_cache.pop(k)
        if len(pw_cache) > 6:
            for k in sorted(pw_cache)[:-6]:
                pw_cache.pop(k)
        if len(ns_cache) > 6:
            for k in sorted(ns_cache)[:-6]:
                ns_cache.pop(k)
    st = pd.DataFrame(stats, columns=["file", "rows", "has_power", "has_gridmet", "has_source_weather",
                                      "has_nearest_station"])
    st.to_csv(NORM / "weather_join_coverage.csv", index=False)
    print(st.to_string())


if __name__ == "__main__":
    main()
