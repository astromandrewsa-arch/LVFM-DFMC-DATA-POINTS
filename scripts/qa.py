"""QA rules for normalized fuel moisture observations.

Flags are appended to qa_flag (semicolon-separated); rows are never dropped or altered here.
Flags:
  missing_value          moisture_pct is null
  sensor_error_code      value <= -999 (logger fill/error codes such as -8190)
  negative_value         -999 < value < 0
  dead_below_1pct        dead fuel < 1 %
  dead_above_40pct       dead fuel > 40 % (possible only when saturated; check rain)
  dead_implausible       dead fuel > 250 %
  live_below_30pct       live fuel < 30 % (cured or dead material, or a fraction-vs-percent error)
  live_above_400pct      live fuel > 400 %
  live_implausible       live fuel > 1000 %
  unit_fraction_suspect  site median below 1.5 for live fuel or below 0.4 for dead fuel, i.e. the values look like fractions
  bad_coords             lat/lon missing, outside range, or exactly 0,0
  bad_date               missing, before 1900, or in the future
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def add_flag(cur: pd.Series, mask, flag: str) -> pd.Series:
    mask = pd.Series(mask, index=cur.index).fillna(False).astype(bool)
    new = cur.copy()
    empty = new.isna() | (new == "")
    new[mask & empty] = flag
    new[mask & ~empty] = new[mask & ~empty] + ";" + flag
    return new


def apply_qa(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    q = df["qa_flag"].astype("string")
    v = df["moisture_pct"].astype("float64")
    dead = (df["fuel_class"] == "dead").to_numpy()
    live = (df["fuel_class"] == "live").to_numpy()
    q = add_flag(q, v.isna(), "missing_value")
    q = add_flag(q, v <= -999, "sensor_error_code")
    q = add_flag(q, (v > -999) & (v < 0), "negative_value")
    q = add_flag(q, dead & (v >= 0) & (v < 1), "dead_below_1pct")
    q = add_flag(q, dead & (v > 40) & (v <= 250), "dead_above_40pct")
    q = add_flag(q, dead & (v > 250), "dead_implausible")
    q = add_flag(q, live & (v >= 0) & (v < 30), "live_below_30pct")
    q = add_flag(q, live & (v > 400) & (v <= 1000), "live_above_400pct")
    q = add_flag(q, live & (v > 1000), "live_implausible")

    site_key = df["source_id"].astype(str) + "|" + df["site_name"].astype(str) + "|" + df["fuel_class"].astype(str)
    med = v.where(v >= 0).groupby(site_key).transform("median")
    frac = (live & (med < 1.5)) | (dead & (med < 0.4))
    q = add_flag(q, frac, "unit_fraction_suspect")

    lat, lon = df["lat"].astype("float64"), df["lon"].astype("float64")
    badc = lat.isna() | lon.isna() | (lat.abs() > 90) | (lon.abs() > 180) | ((lat == 0) & (lon == 0))
    q = add_flag(q, badc, "bad_coords")
    d = pd.to_datetime(df["date"], errors="coerce")
    badd = d.isna() | (d < pd.Timestamp("1900-01-01")) | (d > pd.Timestamp(date.today()))
    q = add_flag(q, badd, "bad_date")
    df["qa_flag"] = q.astype("string")
    return df


def is_clean(qa_flag: pd.Series) -> pd.Series:
    """Rows with no hard-error flag (soft flags such as dead_above_40pct are allowed)."""
    hard = ["missing_value", "sensor_error_code", "negative_value", "dead_implausible",
            "live_implausible", "unit_fraction_suspect", "bad_coords", "bad_date", "duplicate_of"]
    s = qa_flag.fillna("")
    out = pd.Series(True, index=s.index)
    for h in hard:
        out &= ~s.str.contains(h, regex=False)
    return out


if __name__ == "__main__":
    import sys
    df = pd.read_parquet(sys.argv[1])
    df = apply_qa(df)
    print(df["qa_flag"].fillna("ok").str.split(";").explode().value_counts())
