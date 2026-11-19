"""Static site covariates -> data/normalized/site_static.parquet (keyed by site_key).

  dem_elevation_m, dem_slope_deg, dem_aspect_deg  Copernicus DEM GLO-30 (AWS open data COGs,
      s3://copernicus-dem-30m). Slope/aspect from a 3x3 Horn window at 30 m. Aspect is degrees
      clockwise from north (downslope direction); NaN where slope < 0.5 deg.
      License: Copernicus DEM, free for any use incl. commercial, attribution required
      ("produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and
      Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA").
  lc_worldcover_class, lc_worldcover_name  ESA WorldCover 10 m 2021 v200 (CC BY 4.0).

Only windows around each site are read (HTTP range requests); nothing large is stored.
"""
import math
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "3")

import rasterio  # noqa: E402
from rasterio.windows import Window  # noqa: E402

from common import NORM  # noqa: E402

WC = {10: "tree_cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built_up",
      60: "bare_sparse", 70: "snow_ice", 80: "water", 90: "herbaceous_wetland", 95: "mangroves",
      100: "moss_lichen"}


def dem_url(lat, lon):
    la, lo = math.floor(lat), math.floor(lon)
    ns = f"N{la:02d}" if la >= 0 else f"S{-la:02d}"
    ew = f"E{lo:03d}" if lo >= 0 else f"W{-lo:03d}"
    n = f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM"
    return f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"


def wc_url(lat, lon):
    la, lo = math.floor(lat / 3) * 3, math.floor(lon / 3) * 3
    ns = f"N{la:02d}" if la >= 0 else f"S{-la:02d}"
    ew = f"E{lo:03d}" if lo >= 0 else f"W{-lo:03d}"
    return (f"/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
            f"ESA_WorldCover_10m_2021_v200_{ns}{ew}_Map.tif")


def sample_dem(lat, lon):
    try:
        with rasterio.open(dem_url(lat, lon)) as r:
            row, col = r.index(lon, lat)
            w = r.read(1, window=Window(col - 1, row - 1, 3, 3), boundless=True, fill_value=np.nan).astype("float64")
            dx = abs(r.transform.a) * 111320 * math.cos(math.radians(lat))
            dy = abs(r.transform.e) * 110540
    except Exception:
        return np.nan, np.nan, np.nan
    z = w[1, 1]
    if not np.isfinite(w).all():
        return z, np.nan, np.nan
    dzdx = ((w[0, 2] + 2 * w[1, 2] + w[2, 2]) - (w[0, 0] + 2 * w[1, 0] + w[2, 0])) / (8 * dx)
    dzdy = ((w[2, 0] + 2 * w[2, 1] + w[2, 2]) - (w[0, 0] + 2 * w[0, 1] + w[0, 2])) / (8 * dy)
    slope = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
    # downslope direction, clockwise from north (row index increases southward)
    aspect = (math.degrees(math.atan2(-dzdx, dzdy)) + 360) % 360 if slope >= 0.5 else np.nan
    return z, slope, aspect


def sample_wc(lat, lon):
    try:
        with rasterio.open(wc_url(lat, lon)) as r:
            row, col = r.index(lon, lat)
            v = r.read(1, window=Window(col, row, 1, 1))
            return int(v[0, 0])
    except Exception:
        return None


def one(rec):
    key, lat, lon = rec
    z, s, a = sample_dem(lat, lon)
    c = sample_wc(lat, lon)
    return key, z, s, a, c


if __name__ == "__main__":
    sites = pd.read_parquet(NORM / "sites.parquet")
    out_p = NORM / "site_static.parquet"
    have = pd.read_parquet(out_p) if out_p.exists() else pd.DataFrame(columns=["site_key"])
    todo = sites[~sites.site_key.isin(have.site_key)]
    print(len(todo), "sites to sample")
    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(one, todo[["site_key", "lat", "lon"]].itertuples(index=False, name=None)))
    new = pd.DataFrame(res, columns=["site_key", "dem_elevation_m", "dem_slope_deg", "dem_aspect_deg",
                                     "lc_worldcover_class"])
    new["lc_worldcover_class"] = new["lc_worldcover_class"].astype("Int64")
    new["lc_worldcover_name"] = new["lc_worldcover_class"].map(WC).astype("string")
    allp = pd.concat([have, new], ignore_index=True) if len(have) else new
    allp.to_parquet(out_p, index=False)
    print(allp.describe(include="all").T[["count", "mean"]])
