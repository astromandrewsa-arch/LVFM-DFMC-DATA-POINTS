"""Shared helpers for the fuel moisture harvest pipeline.

Every source has a fetch_<source_id>.py (writes untouched files to data/raw/<source_id>/)
and a normalize_<source_id>.py (writes data/normalized/by_source/<source_id>.parquet in the
OBS_COLUMNS schema below). build_observations.py merges, de-duplicates and QAs them into
data/normalized/observations.parquet.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
NORM = ROOT / "data" / "normalized"
BY_SOURCE = NORM / "by_source"
EST_BY_SOURCE = NORM / "estimates_by_source"
CATALOG = ROOT / "data" / "catalog"

USER_AGENT = "pyrome-fuel-moisture-harvest/0.1 (research data collection)"

OBS_COLUMNS = [
    "observation_id", "source_id", "source_record_id", "date", "time", "timezone",
    "lat", "lon", "location_precision_m", "country", "site_name", "fuel_class",
    "fuel_type", "species", "moisture_pct", "method", "measured", "qa_flag", "notes",
]

FUEL_CLASSES = {"dead", "live"}
METHODS = {"oven_dry", "fuel_stick", "sensor", "other", "unknown"}


def raw_dir(source_id: str) -> Path:
    d = RAW / source_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def download(url: str, dest: Path, *, sess: requests.Session | None = None,
             overwrite: bool = False, retries: int = 4, timeout: int = 300, **kw) -> Path:
    """Stream a URL to dest, skipping if it already exists. Retries with backoff."""
    if dest.exists() and dest.stat().st_size > 0 and not overwrite:
        return dest
    sess = sess or session()
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(retries):
        try:
            with sess.get(url, stream=True, timeout=timeout, **kw) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            tmp.rename(dest)
            return dest
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    return dest


def make_obs_id(source_id: str, *parts) -> str:
    h = hashlib.sha1("|".join([source_id, *map(str, parts)]).encode()).hexdigest()[:16]
    return f"{source_id}:{h}"


def finalize(df: pd.DataFrame, source_id: str, *, estimates: bool = False) -> Path:
    """Coerce to the observation schema and write by-source parquet."""
    df = df.copy()
    for c in OBS_COLUMNS:
        if c not in df.columns:
            df[c] = pd.NA
    df["source_id"] = source_id
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["moisture_pct"] = pd.to_numeric(df["moisture_pct"], errors="coerce")
    df["location_precision_m"] = pd.to_numeric(df["location_precision_m"], errors="coerce")
    df["measured"] = df["measured"].fillna(not estimates).astype(bool)
    for c in ["source_record_id", "time", "timezone", "country", "site_name", "fuel_class",
              "fuel_type", "species", "method", "qa_flag", "notes"]:
        df[c] = df[c].astype("string")
    if df["observation_id"].isna().all():
        df["observation_id"] = [
            make_obs_id(source_id, r, i) for i, r in enumerate(df["source_record_id"].fillna(""))
        ]
    df = df[OBS_COLUMNS]
    out_dir = EST_BY_SOURCE if estimates else BY_SOURCE
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{source_id}.parquet"
    df.to_parquet(out, index=False)
    print(f"wrote {len(df):,} rows -> {out.relative_to(ROOT)}")
    return out
