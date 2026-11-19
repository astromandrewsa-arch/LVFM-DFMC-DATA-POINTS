"""Merge by-source parquet files into data/normalized/observations.parquet/ with QA and
cross-source de-duplication.

observations.parquet is a Parquet *dataset directory* (one file per source, or per source-year for
large sources) so every file stays under GitHub's 100 MB limit. Read it as one table with
    pd.read_parquet("data/normalized/observations.parquet")   # or polars.scan_parquet(".../*.parquet")

De-duplication (rows are kept but flagged 'duplicate_of=<observation_id>'):
  Sources compiled from others (e.g. Globe-LFMC includes NFMD, ONF, Catalonia data) are matched
  against more original sources on: location within ~0.01 deg (about 1 km), same date, same
  fuel_class, same normalized species, and moisture within 1 percentage point (or 1 % relative).
  The row from the source with the lowest SOURCE_PRIORITY number (most original) is kept
  unflagged; the duplicate links are also written to data/normalized/duplicates.parquet.
"""
from __future__ import annotations

import glob
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from common import BY_SOURCE, NORM, OBS_COLUMNS
from qa import add_flag, apply_qa, is_clean

# Lower = more original. Compilations get higher numbers.
SOURCE_PRIORITY = {
    "nfmd": 0, "madis_raws": 0, "fems_nfmd": 0,
    "globe_lfmc2": 50,
}
DEFAULT_PRIORITY = 10
# Sources whose rows may duplicate each other (others are known to be disjoint, e.g. MADIS sticks).
DEDUPE_SOURCES_EXCLUDE = {"madis_raws"}

OUT = NORM / "observations.parquet"


def norm_species(s: pd.Series) -> pd.Series:
    return (s.fillna("").str.lower().str.replace(r"[^a-z ]", "", regex=True)
             .str.split().str[:2].str.join(" "))


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["_prio"] = df["source_id"].map(SOURCE_PRIORITY).fillna(DEFAULT_PRIORITY)
    df["_key"] = (df["lat"].round(2).astype(str) + "|" + df["lon"].round(2).astype(str) + "|"
                  + df["date"].astype(str) + "|" + df["fuel_class"].astype(str) + "|"
                  + norm_species(df["species"].astype("string")))
    links = []
    multi = df[df.duplicated("_key", keep=False)]
    for key, g in multi.groupby("_key", sort=False):
        if g["source_id"].nunique() < 2:
            continue
        g = g.sort_values("_prio")
        keep_rows = g[g["_prio"] == g["_prio"].iloc[0]]
        for idx, r in g[g["_prio"] > g["_prio"].iloc[0]].iterrows():
            diff = (keep_rows["moisture_pct"] - r["moisture_pct"]).abs()
            tol = np.maximum(1.0, 0.01 * keep_rows["moisture_pct"].abs())
            m = keep_rows[diff <= tol]
            if len(m):
                links.append((r["observation_id"], m["observation_id"].iloc[0], r["source_id"], m["source_id"].iloc[0]))
    links = pd.DataFrame(links, columns=["observation_id", "duplicate_of", "source_id", "kept_source_id"])
    if len(links):
        lk = links.set_index("observation_id")["duplicate_of"]
        mask = df["observation_id"].isin(lk.index)
        df.loc[mask, "qa_flag"] = add_flag(df["qa_flag"], mask, "duplicate_of=")[mask] + df.loc[mask, "observation_id"].map(lk)
    return df.drop(columns=["_prio", "_key"]), links


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    single = sorted(glob.glob(str(BY_SOURCE / "*.parquet")))
    multi = sorted(glob.glob(str(BY_SOURCE / "*" / "*.parquet")))

    # 1) sources that may overlap: load together, QA, dedupe
    dd = [pd.read_parquet(f) for f in single if Path(f).stem not in DEDUPE_SOURCES_EXCLUDE]
    dd += [pd.read_parquet(f) for f in multi if Path(f).parent.name not in DEDUPE_SOURCES_EXCLUDE]
    summary = []
    if dd:
        df = apply_qa(pd.concat(dd, ignore_index=True))
        df, links = dedupe(df)
        links.to_parquet(NORM / "duplicates.parquet", index=False)
        print("duplicate links:", len(links))
        for sid, g in df.groupby("source_id"):
            g = g[OBS_COLUMNS]
            g.to_parquet(OUT / f"{sid}.parquet", index=False, compression="zstd")
            summary.append(g)
    # 2) large disjoint sources: QA file by file
    for f in multi:
        sid = Path(f).parent.name
        if sid not in DEDUPE_SOURCES_EXCLUDE:
            continue
        g = apply_qa(pd.read_parquet(f))[OBS_COLUMNS]
        g.to_parquet(OUT / f"{sid}-{Path(f).stem}.parquet", index=False, compression="zstd")
        summary.append(g[["source_id", "fuel_class", "country", "date", "qa_flag"]])
    for f in single:
        sid = Path(f).stem
        if sid in DEDUPE_SOURCES_EXCLUDE:
            g = apply_qa(pd.read_parquet(f))[OBS_COLUMNS]
            g.to_parquet(OUT / f"{sid}.parquet", index=False, compression="zstd")
            summary.append(g)

    s = pd.concat([x[["source_id", "fuel_class", "country", "date", "qa_flag"]] for x in summary])
    s["clean"] = is_clean(s["qa_flag"].astype("string"))
    s["year"] = pd.to_datetime(s["date"], errors="coerce").dt.year
    print("total rows", len(s), "clean", int(s["clean"].sum()))
    print(s.groupby(["source_id", "fuel_class"])["clean"].agg(["size", "sum"]))
    s.groupby(["source_id", "fuel_class", "country", "year", "clean"], dropna=False).size() \
        .rename("n").reset_index().to_csv(NORM / "summary_counts.csv", index=False)


if __name__ == "__main__":
    main()
