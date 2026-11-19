"""Normalize RDS-2024-0049 (FASMEE Monroe Mountain, Fishlake NF, Utah): day-of-burn fuel moisture.

FASMEE-MonroeMountain-Ground_fuelmoistures_raw.csv: one row per bagged sample with gross wet
weight + bag tare and gross oven-dry weight + aluminium-tin tare. Gravimetric moisture on a dry
basis is computed here: ((wet-tare_wet) - (dry-tare_dry)) / (dry-tare_dry) * 100
(Methods: oven 70 C for 48 h; 'water weight / oven-dry fuel weight').

Dates (units_overview DAY-OF date): per Methods, 1/10/100-h, litter and live conifer were taken
the morning of the burn; duff and 1000-h fuels the day before -> date = burn date - 1 day for those.
Samples whose notes say they came from the proxy location (Langdon: ~1/4 mile N of unit; Manning
Creek: ~2 miles NW) get location_approx and a larger location_precision_m.
Dropped (documented): 'Annabella Proxy' (proxy samples whose burn date is ambiguous between the
11/2 and 11/5/2020 Annabella burns), 'Annabella Reservoir B' (no DAY-OF date in units_overview),
samples noted 'Not Sampled', and samples with non-positive dry mass. Samples noted as damaged
('bag ripped/torn', 'contaminated', 'lost some material', 'tipped in oven') are kept with qa_flag.
Unit coordinates = mean of the unit's GPS plot centres (plots span ~100-300 m).
"""
import pandas as pd

from common import finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_fasmee_monroe"
MAT = {  # SampleMaterial -> fuel_class, fuel_type, note
    "Downed Woody: 1-hr": ("dead", "1hr", ""), "Downed Woody: 10-hr": ("dead", "10hr", ""),
    "Downed Woody: 100-hr": ("dead", "100hr", ""), "Downed Woody: 1000-hr": ("dead", "1000hr", ""),
    "Litter": ("dead", "litter", ""), "Duff": ("dead", "duff", ""),
    "Trees: Conifer": ("live", "tree_foliage", "live conifer foliage"),
    "Trees: Conifer - branches": ("live", "other", "conifer branches; live/dead status not stated"),
}
UNIT_PLOTS = {"Annabella Reservoir A": "Annabella A", "Annabella Reservoir C": "Annabella C",
              "Langdon A": "Langdon A", "Manning Creek A": "Manning Creek A",
              "Manning Creek B": "Manning Creek B"}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    fm = pd.read_csv(find(d, "FASMEE-MonroeMountain-Ground_fuelmoistures_raw.csv"), encoding="utf-8-sig")
    units = pd.read_csv(find(d, "FASMEE-MonroeMountain-Ground_units_overview.csv"), encoding="utf-8-sig")
    plots = pd.read_csv(find(d, "FASMEE-MonroeMountain-Ground_plots_overview.csv"), encoding="utf-8-sig")
    fm["_row"] = range(len(fm))
    n0 = len(fm)
    burn = units[units["epShort"] == "DAY-OF"].set_index("unitName")["samplingStartDate"]
    burn = pd.to_datetime(burn, format="%m/%d/%Y")
    xy = plots.groupby("unitName")[["lat", "lon"]].mean()

    note = fm["notes"].fillna("").astype(str)
    fm = fm[fm["unitName"].isin(UNIT_PLOTS) & ~note.str.contains("Not Sampled", case=False)].copy()
    note = fm["notes"].fillna("").astype(str)
    wet = fm["grossWetWt_g"] - fm["wetContWt_g"]
    dry = fm["grossDryWt_g"] - fm["dryContWt_g"]
    mp = (wet - dry) / dry * 100
    ok = (dry > 0) & mp.notna()
    fm, mp, note = fm[ok], mp[ok], note[ok]
    print(n0, "raw;", len(fm), "kept")

    mat = fm["SampleMaterial"].map(MAT)
    unk = mat.isna()
    assert not unk.any(), fm.loc[unk, "SampleMaterial"].unique()
    date = fm["unitName"].map(burn)
    prior = fm["SampleMaterial"].isin(["Duff", "Downed Woody: 1000-hr"])
    date = date.where(~prior, date - pd.Timedelta(days=1))
    unit_xy = fm["unitName"].map(UNIT_PLOTS).map(lambda u: tuple(xy.loc[u]))
    proxy = note.str.contains("proxy", case=False)
    prec = pd.Series(300.0, index=fm.index)
    prec[proxy & fm["unitName"].str.startswith("Langdon")] = 800.0
    prec[proxy & fm["unitName"].str.startswith("Manning")] = 4000.0
    qa = pd.Series(pd.NA, index=fm.index, dtype="string")
    qa[mp <= 0] = "nonpositive_moisture"
    qa[note.str.contains("ripped|torn|contaminated|lost some|tipped|Hole in Bag|opened|36 hrs", case=False)] = "src_sample_issue"
    notes = ("gravimetric dry basis computed from net weights; oven 70C 48h; day-of-burn sampling; material="
             + fm["SampleMaterial"] + mat.str[2].map(lambda s: f"; {s}" if s else "")
             + prior.map({True: "; collected day before burn (per Methods)", False: ""})
             + note.map(lambda s: f"; src_note={s}" if s else "")
             + proxy.map({True: "; proxy location near unit, location_approx", False: ""}))
    out = pd.DataFrame({
        "source_record_id": fm["unitName"] + "|" + fm["SampleMaterial"] + "|" + fm["sampleNo"].astype(str) + "#" + fm["_row"].astype(str),
        "date": date, "time": pd.NA, "timezone": "America/Denver",
        "lat": unit_xy.str[0], "lon": unit_xy.str[1], "location_precision_m": prec, "country": "USA",
        "site_name": "FASMEE " + fm["unitName"] + " (Fishlake NF, UT)",
        "fuel_class": mat.str[0], "fuel_type": mat.str[1], "species": pd.NA,
        "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": qa, "notes": notes,
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
