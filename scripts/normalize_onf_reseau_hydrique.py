"""Normalize the ONF "Reseau Hydrique" LFMC series (Zenodo 162978, CC-BY-4.0).

Uses LFMC_raw_Table.csv: one row per site x species x date with up to five individual
replicate LFMC values (LFMC1..LFMC5) -> one output row per individual replicate sample.
Values in this Zenodo table are already on a dry-weight basis (the Zenodo description says the
ONF website data are fresh-mass based, but ~19% of the replicate values here exceed 100%, which
is impossible on a fresh basis, and they agree with the dry-basis robust means in
LFMC_final_Table.csv), so no conversion is applied.

The INRA outlier flags (LFMCnFlag: 0 = ok, 1/2 = outlier identified manually / automatically,
Martin-StPaul et al. 2018 Ann For Sci 75:57) are kept in qa_flag; nothing is dropped. The
INRA robust site-species-date mean (LFMC_final_Table.csv) is added to notes for reference.

Sites: 35 geolocated sites have WGS84 coords (3 decimals, ~100 m) in InfoSite_ReseauHydrique.csv.
16 "SNG" (non-geolocated) sites are placed either at a same-named sibling site (precision 3 km)
or at their departement centroid (precision 50 km), with "location_approx" in notes.
RainTableFinal.csv (rain gauge total since previous visit) -> covariates file.
The source file is MacRoman-encoded and some accented characters were replaced by '_' in the
SiteName column, so site names are taken from InfoSite (Latin-1) via SiteCode.
"""
import numpy as np
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "onf_reseau_hydrique"
TREES = {"Acacia dealbata", "Quercus ilex", "Quercus pubescens"}

# Non-geolocated sites. sibling -> coords of the geolocated site with the same name stem.
SIBLING = {"D2ASNG1": "D2AS4", "D2ASNG2": "D2AS4", "D2ASNG4": "D2AS2", "D2BSNG1": "D2BS1"}
# departement approximate centroids (lat, lon)
DEPT_CENTROID = {
    "05": (44.66, 6.26), "07": (44.75, 4.42), "13": (43.54, 5.09), "26": (44.68, 5.17),
    "2A": (41.86, 8.98), "2B": (42.41, 9.21), "34": (43.58, 3.37), "48": (44.52, 3.50),
    "66": (42.60, 2.52),
}
EXTRA_NAMES = {"D2ASNG4": "FD Valle Mala"}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    raw = pd.read_csv(d / "LFMC_raw_Table.csv", sep=";", na_values=["NA"], dtype=str,
                      skipinitialspace=True, encoding="mac_roman")
    raw = raw.apply(lambda s: s.str.strip())
    site = pd.read_csv(d / "InfoSite_ReseauHydrique.csv", sep=";", encoding="latin1",
                       decimal=",", na_values=["NA"])
    fin = pd.read_csv(d / "LFMC_final_Table.csv", sep=";", encoding="latin1")
    print(len(raw), "raw site-species-date rows")

    # ---- site coordinates
    coords = {}
    for r in site.itertuples():
        if pd.notna(r._3):
            coords[r.SiteCode] = (r._4, r._3, 100, None)
    for code in set(raw.SiteCode) | set(site.SiteCode):
        if code in coords:
            continue
        if code in SIBLING and SIBLING[code] in coords:
            la, lo, _, _ = coords[SIBLING[code]]
            coords[code] = (la, lo, 3000, f"location_approx: coords of sibling site {SIBLING[code]}")
        else:
            la, lo = DEPT_CENTROID[code[1:3]]
            coords[code] = (la, lo, 50000, f"location_approx: departement {code[1:3]} centroid")
    names = dict(zip(site.SiteCode, site.SiteName)) | EXTRA_NAMES

    # ---- long format: one row per replicate
    rows = []
    for i in range(1, 6):
        t = raw[["SiteCode", "Species", "Date", f"LFMC{i}", f"LFMC{i}Flag", "FFSLFMC"]].copy()
        t.columns = ["SiteCode", "Species", "Date", "lfmc", "flag", "ffs"]
        t["rep"] = i
        rows.append(t)
    lg = pd.concat(rows, ignore_index=True)
    lg["lfmc"] = pd.to_numeric(lg["lfmc"], errors="coerce")
    lg = lg[lg["lfmc"].notna()]
    lg["date"] = pd.to_datetime(lg["Date"], format="%d/%m/%Y", errors="coerce")
    bad = lg["date"].isna() | (lg["date"].dt.year > 2016) | (lg["date"].dt.year < 1996)
    print("dropping", int(bad.sum()), "replicates with invalid date:", lg.loc[bad, "Date"].unique())
    lg = lg[~bad]

    fin["date"] = pd.to_datetime(fin["Date"], format="%d/%m/%Y", errors="coerce")
    fin = fin.rename(columns={"SiteCode": "SiteCode", "Species": "Species"})
    lg = lg.merge(fin[["SiteCode", "Species", "date", "RobustLFMC", "RobustStandErrLFMC", "RobustNval"]],
                  on=["SiteCode", "Species", "date"], how="left")

    c = lg["SiteCode"].map(coords)
    lat = c.map(lambda x: x[0]); lon = c.map(lambda x: x[1])
    prec = c.map(lambda x: x[2]); locnote = c.map(lambda x: x[3])
    flag = lg["flag"].astype("string")
    qa = flag.map({"1": "src_outlier_flag1(manual)", "2": "src_outlier_flag2(auto)"})

    s_ = lambda x: x.astype(object).where(x.notna(), "NA").astype(str)
    notes = ("replicate=" + lg["rep"].astype(str) + "/5; dry_weight_basis; ONF_mean_FFSLFMC="
             + s_(lg["ffs"]) + "; INRA_robust_mean=" + s_(lg["RobustLFMC"].round(2))
             + " (se=" + s_(lg["RobustStandErrLFMC"].round(2)) + ", n="
             + s_(lg["RobustNval"].astype("Int64")) + "); site_code=" + lg["SiteCode"])
    notes = notes.where(locnote.isna(), notes + "; " + locnote.fillna(""))

    out = pd.DataFrame({
        "source_record_id": lg["SiteCode"] + "|" + lg["Species"] + "|" + lg["Date"] + "|r" + lg["rep"].astype(str),
        "date": lg["date"],
        "time": pd.NA,
        "timezone": "Europe/Paris",
        "lat": lat, "lon": lon, "location_precision_m": prec,
        "country": "France",
        "site_name": lg["SiteCode"].map(names),
        "fuel_class": "live",
        "fuel_type": np.where(lg["Species"].isin(TREES), "tree_foliage", "shrub"),
        "species": lg["Species"],
        "moisture_pct": lg["lfmc"],
        "method": "oven_dry",
        "measured": True,
        "qa_flag": qa,
        "notes": notes,
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)

    # ---- covariates: rain since previous visit at the site gauge
    rain = pd.read_csv(d / "RainTableFinal.csv", sep=";", dtype=str, skipinitialspace=True,
                       encoding="mac_roman").apply(lambda s: s.str.strip())
    rain["date"] = pd.to_datetime(rain["MeasurementDate"], format="%d/%m/%Y", errors="coerce")
    rain["Rainfall"] = pd.to_numeric(rain["Rainfall"], errors="coerce")
    rain["days"] = pd.to_numeric(rain["MeasurementDoy"]) - pd.to_numeric(rain["PreviousDoy"])
    rain = rain.drop_duplicates(["SiteCode", "date"])
    k = pd.DataFrame({"observation_id": out["observation_id"], "SiteCode": lg["SiteCode"].values,
                      "date": lg["date"].values})
    cov = k.merge(rain[["SiteCode", "date", "Rainfall", "days", "RainFlag"]], on=["SiteCode", "date"], how="inner")
    cov = pd.DataFrame({
        "observation_id": cov["observation_id"],
        "cov_source": "onf_reseau_hydrique_provided(site rain gauge, RainTableFinal.csv)",
        "precip_since_prev_visit_mm": cov["Rainfall"],
        "precip_window_days": cov["days"],
        "precip_flag": cov["RainFlag"].astype("string"),
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
