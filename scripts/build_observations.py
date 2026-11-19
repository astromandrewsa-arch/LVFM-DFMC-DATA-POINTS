"""Merge by-source parquet files into data/normalized/observations.parquet/ with QA and
cross-source de-duplication.

observations.parquet is a Parquet *dataset directory* (one file per source, or per source-year for
large sources) so every file stays under GitHub's 100 MB limit. Read it as one table with
    pd.read_parquet("data/normalized/observations.parquet")   # or polars.scan_parquet(".../*.parquet")

De-duplication (rows are kept but flagged 'duplicate_of=<observation_id>'):
  Sources compiled from others (e.g. Globe-LFMC includes NFMD, ONF, Catalonia data) are matched
  one-to-one against more original sources on: location within ~0.01 deg (about 1 km), same date,
  same fuel_class, and moisture within 1 percentage point (or 1 % relative). Species is not used
  because compilations rename species.
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


def _key(df: pd.DataFrame) -> pd.Series:
    return (df["lat"].round(2).astype(str) + "|" + df["lon"].round(2).astype(str) + "|"
            + df["date"].astype(str) + "|" + df["fuel_class"].astype(str))


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One-to-one matching, most original source first.

    Rows of a lower-priority (more compiled) source are matched to already-kept rows on
    (lat, lon rounded to 0.01 deg, date, fuel_class) with |moisture difference| <= max(1, 1 %).
    Species is not used because compilations rename species (e.g. Latin vs common names).
    Each kept row absorbs at most one duplicate per source; closest values match first.
    """
    df = df.copy()
    df["_prio"] = df["source_id"].map(SOURCE_PRIORITY).fillna(DEFAULT_PRIORITY)
    df["_key"] = _key(df)
    links = []
    levels = sorted(df["_prio"].unique())
    pool = df[df["_prio"] == levels[0]][["observation_id", "source_id", "_key", "moisture_pct"]]
    for lv in levels[1:]:
        for sid in sorted(df.loc[df["_prio"] == lv, "source_id"].unique()):
            cand_rows = df[(df["source_id"] == sid)][["observation_id", "source_id", "_key", "moisture_pct"]]
            m = cand_rows.merge(pool[pool["source_id"] != sid], on="_key", suffixes=("", "_kept"))
            m["diff"] = (m["moisture_pct"] - m["moisture_pct_kept"]).abs()
            tol = np.maximum(1.0, 0.01 * m["moisture_pct_kept"].abs())
            m = m[m["diff"] <= tol].sort_values("diff")
            m = m.drop_duplicates("observation_id").drop_duplicates("observation_id_kept")
            links.append(m[["observation_id", "observation_id_kept", "source_id", "source_id_kept", "diff"]])
            unmatched = cand_rows[~cand_rows["observation_id"].isin(m["observation_id"])]
            pool = pd.concat([pool, unmatched], ignore_index=True)
    links = (pd.concat(links, ignore_index=True) if links else pd.DataFrame(
        columns=["observation_id", "observation_id_kept", "source_id", "source_id_kept", "diff"]))
    links = links.rename(columns={"observation_id_kept": "duplicate_of", "source_id_kept": "kept_source_id"})
    if len(links):
        lk = links.set_index("observation_id")["duplicate_of"]
        mask = df["observation_id"].isin(lk.index)
        flagged = add_flag(df["qa_flag"], mask, "duplicate_of=")
        df.loc[mask, "qa_flag"] = flagged[mask] + df.loc[mask, "observation_id"].map(lk)
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
