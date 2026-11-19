"""Normalize the BC fire-skips FMC dataset (Xiao 2025, Zenodo 10.5281/zenodo.17087197, CC-BY-4.0).

Four CSVs (Prince George 2021/2022, Smithers 2021/2022): one row per tin sample of foliage
(>1 yr old conifer needles), fine woody debris ("fines", dead 2-7 mm) or duff (F+H layers).
Moisture_Percent is gravimetric FMC on a dry-weight basis, oven 100 C / 24 h (per 'meta data.txt').
We keep the provided value; rows where it disagrees with (fresh-dry)/(dry-tin) by >5 points
get qa_flag src_pct_mismatch.

Coordinates: site-centre lat/lon/elevation per Location x stand type from the metadata table
(stand 'mature' in the data = 'old' in the table). 'Bednesti' (Prince George, data only) is the
site the table lists as 'Tamarac' (the only PG site name missing from the data; Bednesti Lake is
adjacent) -> mapped with note site_alias_bednesti=tamarac and location_approx.
Times are local (PDT); 2022 PG times are written with AM/PM and several are clearly mis-keyed
(e.g. '11:25 PM'); times outside 07:00-19:59 are dropped to NA and the raw string kept in notes.
"""
import re

import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "bc_fire_skips"

SITES = {  # (location, table stand type) -> lat, lon, elev
    ("Barren", "open"): (54.5104, -126.6143, 1051), ("Barren", "juvenile"): (54.5080, -126.6151, 1059),
    ("Barren", "old"): (54.5113, -126.6112, 1043),
    ("Chapman", "open"): (54.8839, -126.6235, 848), ("Chapman", "juvenile"): (54.8828, -126.6376, 854),
    ("Chapman", "old"): (54.8827, -126.6289, 809),
    ("McDonnell", "open"): (54.7822, -127.5143, 980), ("McDonnell", "juvenile"): (54.7809, -127.5206, 990),
    ("McDonnell", "old"): (54.7819, -127.5061, 981),
    ("Dennis", "open"): (54.7613, -127.4677, 889), ("Dennis", "juvenile"): (54.7623, -127.4663, 881),
    ("Dennis", "old"): (54.7598, -127.4665, 898),
    ("Tamarac", "open"): (53.8713, -123.3704, 865), ("Tamarac", "juvenile"): (53.8701, -123.3702, 858),
    ("Tamarac", "old"): (53.8726, -123.3688, 869),
    ("North Fraser", "open"): (54.2439, -122.4907, 698), ("North Fraser", "juvenile"): (54.2437, -122.4882, 710),
    ("North Fraser", "old"): (54.2423, -122.4899, 698),
    ("Stone Creek", "open"): (53.6162, -122.5379, 881), ("Stone Creek", "juvenile"): (53.6162, -122.5359, 895),
    ("Stone Creek", "old"): (53.6139, -122.5464, 860),
}
LOC_ALIAS = {"NFraser": "North Fraser", "StoneCk": "Stone Creek", "Bednesti": "Tamarac"}
SPECIES = {"pine": "pine (unspecified in source)", "fir": "fir (unspecified in source)",
           "spruce": "spruce (unspecified in source)", "dfir": "Pseudotsuga menziesii",
           "thimbleberry": "Rubus parviflorus", "honeysuckle": "Lonicera sp."}


def parse_time(s):
    if pd.isna(s):
        return pd.NA
    s = str(s).strip().replace(" ", "").upper()
    m = re.match(r"^(\d{1,2}):(\d{2})(AM|PM)?$", s)
    if not m:
        return pd.NA
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "PM" and h < 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    if ap is None and 1 <= h <= 6:  # 2021 sheets use 12-h clock without suffix for afternoon
        h += 12
    if not 7 <= h <= 19:
        return pd.NA
    return f"{h:02d}:{mi:02d}"


if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    frames = []
    for f in sorted(d.glob("*.csv")):
        x = pd.read_csv(f, encoding="utf-8-sig", dtype=str)
        x["_file"] = f.name
        x["_row"] = range(len(x))
        if "Dry_Wt_24H" in x:
            x["Dry_Wt"] = x["Dry_Wt_24H"]
        frames.append(x)
    df = pd.concat(frames, ignore_index=True)
    print(len(df), "raw rows")

    loc = df["Location"].str.strip().replace(LOC_ALIAS)
    stand = df["Stand_Type"].str.strip().str.lower().replace({"mature": "old"})
    coords = [SITES.get((l, s), (None, None, None)) for l, s in zip(loc, stand)]
    lat, lon, elev = zip(*coords)
    assert all(v is not None for v in lat), "unmapped site"

    ft_raw = df["Fuel_Type"].str.strip().str.lower()
    sp_raw = df["Foliage_Sp"].str.strip().str.lower()
    fuel_class = ft_raw.map({"foliage": "live", "fines": "dead", "duff": "dead"})
    fuel_type = ft_raw.map({"foliage": "tree_foliage", "fines": "fine_dead", "duff": "duff"})
    shrub = sp_raw.isin(["thimbleberry", "honeysuckle"])
    fuel_type[shrub] = "shrub"
    species = sp_raw.map(SPECIES).astype("string")
    species[ft_raw == "duff"] = pd.NA

    mp = pd.to_numeric(df["Moisture_Percent"], errors="coerce")
    fw, dw, tw = (pd.to_numeric(df[c], errors="coerce") for c in ("Fresh_Wt", "Dry_Wt", "Tin_Wt"))
    calc = (fw - dw) / (dw - tw) * 100
    qa = pd.Series(pd.NA, index=df.index, dtype="string")
    qa[(calc - mp).abs() > 5] = "src_pct_mismatch"

    time = df["Time_Collected"].map(parse_time)
    region = df["_file"].str.split("_").str[0].map({"pg": "Prince George", "smithers": "Smithers"})

    def opt(col, label):
        if col not in df:
            return ""
        return df[col].map(lambda v: f"; {label}={str(v).strip()}" if pd.notna(v) and str(v).strip() else "")

    notes = ("gravimetric oven 100C 24h, dry basis; stand=" + df["Stand_Type"].str.strip()
             + "; fuel_src=" + ft_raw + "; region=" + region
             + opt("Foliage_exposure", "foliage_exposure") + opt("Foliage_height", "foliage_height")
             + opt("Duff_exposure", "duff_exposure") + opt("Duff_Canopy_Sp", "duff_canopy_sp")
             + opt("Notes", "src_note") + "; time_raw=" + df["Time_Collected"].fillna("").str.strip()
             + "; file=" + df["_file"] + "; location_approx(site centre)")
    notes = notes.where(ft_raw != "fines", notes + "; fwd 2-7 mm diameter")
    notes = notes.where(df["Location"].str.strip() != "Bednesti",
                        notes + "; site_alias_bednesti=tamarac")

    out = pd.DataFrame({
        "source_record_id": df["_file"] + "#" + df["_row"].astype(str),
        "date": pd.to_datetime(df["Date_Collected"].str.strip(), format="%d-%b-%y", errors="coerce"),
        "time": time,
        "timezone": "America/Vancouver",
        "lat": lat, "lon": lon,
        "location_precision_m": 300.0,
        "country": "Canada",
        "site_name": loc + " " + df["Stand_Type"].str.strip() + " (" + region + ", BC)",
        "fuel_class": fuel_class, "fuel_type": fuel_type, "species": species,
        "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": qa, "notes": notes,
    })
    bad = out["date"].isna() | out["moisture_pct"].isna()
    print("dropping rows without date/moisture:", int(bad.sum()))
    out = out[~bad]
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)

    cov = pd.DataFrame({"observation_id": out["observation_id"],
                        "cov_source": "source_site_table",
                        "elevation_m": pd.Series(elev, index=df.index)[out.index].astype(float)})
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
