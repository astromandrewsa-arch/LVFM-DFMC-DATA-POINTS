"""Normalize Nolan et al. dead fine fuel moisture, SE Australia 2012-2014 (figshare 28208036, CC BY 4.0).

Wide CSV (one row per sample; several replicate samples per site-date) -> one observation per
sample and fuel component:
  Profile 1hr DFMC   -> fuel_type litter (litter layer down to soil: leaves, bark, twigs)
  Duff DFMC          -> fuel_type duff
  Suspended 1hr DFMC -> fuel_type 1hr (suspended dead material, < 6 mm)
  Suspended 10hr DFMC-> fuel_type 10hr (6-25 mm suspended dead material)
All are destructive gravimetric samples (oven_dry, % of dry weight per the source paper).
The source notes some samples hold free water, so values above fibre saturation (~35 %) are real.
Dates are dd/mm/yyyy; one site-date (Wombat Forest '3/7/2014', 8 rows) disagrees with its DoY
column (66 = 7 Mar 2014): kept as given (3 Jul 2014) with qa_flag date_doy_conflict.
"""
import pandas as pd

from common import finalize, make_obs_id, raw_dir

SOURCE_ID = "nolan_dfmc_seaus"
COMPONENTS = {
    "Profile 1hr DFMC": ("litter", "profile litter (1-h) incl. leaves, bark, twigs"),
    "Duff DFMC": ("duff", "duff"),
    "Suspended 1hr DFMC": ("1hr", "suspended dead 1-h (<6 mm)"),
    "Suspended 10hr DFMC": ("10hr", "suspended dead 10-h (6-25 mm)"),
}

if __name__ == "__main__":
    src = raw_dir(SOURCE_ID) / "Dead fuel moisture content.csv"
    d = pd.read_csv(src, skiprows=[1], encoding="latin-1")
    d = d.loc[:, ~d.columns.str.startswith("Unnamed")].dropna(how="all").reset_index(drop=True)
    print(len(d), "sample rows")
    d["rep"] = d.groupby(["Site name", "Date"]).cumcount() + 1
    date = pd.to_datetime(d["Date"], format="%d/%m/%Y")
    doy_conflict = (date.dt.dayofyear != d["DoY"]) | (date.dt.year != d["Year"])
    rows = []
    for col, (ft, desc) in COMPONENTS.items():
        v = pd.to_numeric(d[col], errors="coerce")
        m = v.notna()
        part = pd.DataFrame({
            "source_record_id": d.loc[m, "Site name"] + "@" + d.loc[m, "Date"] + "#" + d.loc[m, "rep"].astype(str) + ":" + ft,
            "date": date[m],
            "lat": d.loc[m, "Latitude"], "lon": d.loc[m, "Longitude"],
            "site_name": d.loc[m, "Site name"],
            "fuel_type": ft,
            "moisture_pct": v[m],
            "notes": f"component={desc}; replicate=" + d.loc[m, "rep"].astype(str),
            "qa_flag": doy_conflict[m].map({True: "date_doy_conflict", False: pd.NA}),
        })
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    out = out.assign(time=pd.NA, timezone="Australia/Sydney", location_precision_m=100,
                     country="Australia", fuel_class="dead", species=pd.NA,
                     method="oven_dry", measured=True)
    out.loc[out["qa_flag"].notna(), "notes"] += "; DoY column implies 2014-03-07"
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)
