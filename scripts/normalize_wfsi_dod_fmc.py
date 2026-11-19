"""Normalize DoD WFSI burn-campaign fuel moisture datasets (CC-BY-4.0 per EML intellectualRights).

Five datasets (SE US longleaf/slash pine systems), one row per sample, gravimetric moisture on a
dry basis (data dictionaries: 100*(wet-dry)/dry):
  W4688D Fort Stewart GA 2022 (Prichard/Nemens/Cronan; weights given -> recomputed and checked)
  W41S34 Osceola NF FL Feb 2022, W4V30J Eglin AFB FL Mar 2023, W4QC7Q Fort Stewart GA Feb 2024,
  W4JP44 Fort Stewart GA Apr 2025 (Loudermilk et al.).
Fuel codes are mapped from each dataset's data dictionary (codes differ between years: e.g. LEO
is live evergreen-oak leaves in 2023 but detached dead evergreen-oak leaves in 2025).
'FE' (field error) values are dropped. Grass / graminoid codes are 'living or dead' mixtures ->
fuel_class dead, qa_flag mixed_live_dead.
Locations: EML geographic coverage. When a dataset has several burn units and rows do not say
which unit, the centre of all units is used with a precision covering them (location_approx).
"""
import re

import pandas as pd

from common import finalize, make_obs_id, raw_dir

SOURCE_ID = "wfsi_dod_fmc"
D, L = "dead", "live"
LONGLEAF, PINES = "Pinus palustris", "Pinus palustris / Pinus elliottii"
CODES = {
    "W4688D": {
        "Downed Woody: 1-hr": (D, "1hr", None, None), "Downed Woody: 10-hr": (D, "10hr", None, None),
        "Downed Woody: 100-hr": (D, "100hr", None, None), "Duff": (D, "duff", None, None),
        "Grass": (D, "grass", "grass other than wiregrass", "live_dead_unspecified"),
        "Grass: Wiregrass": (D, "grass", "Aristida stricta / Aristida spp.", "live_dead_unspecified"),
        "Litter": (D, "litter", None, None),
        "Litter: Suspended pine needles": (D, "litter", "suspended pine needles (needle drape)", None),
        "Shrubs: Evergreen (live)": (L, "shrub", "evergreen shrubs other than gallberry", None),
        "Shrubs: Gallberry (live)": (L, "shrub", "Ilex glabra", None),
    },
    "W41S34": {
        "BG": (D, "grass", "Aristida stricta or Schizachyrium/Andropogon spp.", "mixed_live_dead"),
        "DSP": (D, "dead_foliage", "Serenoa repens", None), "LSP": (L, "shrub", "Serenoa repens", None),
        "PN": (D, "litter", PINES + " needles", None),
        "SPN": (D, "litter", PINES + " needles (shaded)", None),
        "UPN": (D, "litter", PINES + " needles (unshaded)", None),
    },
    "W4V30J": {
        "1hr": (D, "1hr", None, None), "10hr": (D, "10hr", None, None), "100hr": (D, "100hr", None, None),
        "1000hr": (D, "1000hr", None, None), "DLP": (D, "litter", LONGLEAF + " needles", None),
        "DOL": (D, "litter", "Quercus spp. (not Q. laevis) leaves", None),
        "DTL": (D, "litter", "Quercus laevis leaves", None),
        "FV": (D, "herb", "graminoids and forbs", "mixed_live_dead"),
        "LEO": (L, "tree_foliage", "evergreen Quercus spp.", None), "LLP": (L, "tree_foliage", LONGLEAF, None),
        "LTO": (L, "tree_foliage", "Quercus laevis", None),
        "ML": (D, "litter", "mixed hardwood leaves and pine needles", None),
        "PC": (D, "other", LONGLEAF + " cones", None),
    },
    "W4QC7Q": {
        "1hr": (D, "1hr", None, None), "10hr": (D, "10hr", None, None), "100hr": (D, "100hr", None, None),
        "BG": (D, "grass", "Aristida stricta or Schizachyrium/Andropogon spp.", "mixed_live_dead"),
        "DPN": (D, "litter", PINES + " needles", None),
        "LPN": (L, "tree_foliage", PINES + " (seedlings/saplings <= 2.4 m)", None),
        "PC": (D, "other", "pine cones", None),
        "WD": (D, "litter", "shrub leaf litter (Ilex/Vaccinium/Myrica or Lyonia/Persea)", None),
        "WL": (L, "shrub", "Ilex/Vaccinium arboreum/Myrica cerifera or Lyonia/Persea leaves", None),
    },
    "W4JP44": {
        "1hr": (D, "1hr", None, None), "10hr": (D, "10hr", None, None), "100hr": (D, "100hr", None, None),
        "BG": (D, "grass", "Andropogon spp.", "mixed_live_dead"),
        "DPN": (D, "litter", "Pinus elliottii / P. taeda needles", None),
        "LDO": (D, "litter", "Quercus nigra / Q. hemisphaerica leaves", None),
        "LEO": (D, "litter", "Quercus virginiana leaves", None),
        "LG": (D, "litter", "Ilex glabra leaves", None),
        "LPN": (L, "tree_foliage", "Pinus elliottii / P. taeda", None),
        "LSG": (D, "litter", "Liquidambar styraciflua leaves", None),
        "PC": (D, "other", "pine cones", None),
        "WG": (D, "grass", "Aristida spp.", "mixed_live_dead"),
        "WLDO": (L, "tree_foliage", "Quercus nigra / Q. hemisphaerica", None),
        "WLEO": (L, "tree_foliage", "Quercus virginiana", None),
        "WLG": (L, "shrub", "Ilex glabra", None),
        "WLSG": (L, "tree_foliage", "Liquidambar styraciflua", None),
        "WS": (D, "grass", "Carex spp.", "mixed_live_dead"),
    },
}
NAMES = {"W4688D": "Fort Stewart GA 2022", "W41S34": "Osceola NF FL 2022", "W4V30J": "Eglin AFB FL 2023",
         "W4QC7Q": "Fort Stewart GA 2024", "W4JP44": "Fort Stewart GA 2025"}


def coverage(eml_path):
    t = eml_path.read_text(encoding="utf-8", errors="replace")
    boxes = []
    for g in re.findall(r"<boundingCoordinates>(.*?)</boundingCoordinates>", t, re.S):
        v = {k: float(re.search(rf"<{k}BoundingCoordinate>(.*?)</", g).group(1))
             for k in ("west", "east", "north", "south")}
        boxes.append(v)
    w, e = min(b["west"] for b in boxes), max(b["east"] for b in boxes)
    s, n = min(b["south"] for b in boxes), max(b["north"] for b in boxes)
    lat, lon = (n + s) / 2, (w + e) / 2
    import math
    half_diag = math.hypot((n - s) * 111000 / 2, (e - w) * 111000 * math.cos(math.radians(lat)) / 2)
    return lat, lon, max(200.0, round(half_diag + 200, -2)), len(boxes)


def hhmm(v):
    v = pd.to_numeric(v, errors="coerce")
    return v.map(lambda t: pd.NA if pd.isna(t) else f"{int(t) // 100:02d}:{int(t) % 100:02d}")


if __name__ == "__main__":
    root = raw_dir(SOURCE_ID)
    parts = []
    for ds, codes in CODES.items():
        d = root / ds
        lat, lon, prec, nbox = coverage(d / "eml.xml")
        if ds == "W4688D":  # one EML point, but sites A/B/G/C lie in burn units 6.4, 6.3 and 16.2
            prec = 3000.0
        csv = [p for p in d.glob("*.csv") if not re.search(r"_(dd|flmd|codes)\.csv$", p.name)][0]
        x = pd.read_csv(csv, encoding="utf-8-sig", dtype=str)
        x.columns = [c.strip() for c in x.columns]
        x = x.loc[:, [c for c in x.columns if c and not c.startswith("Unnamed")]]
        x["_row"] = range(len(x))
        extra = pd.Series("", index=x.index)
        if ds == "W4688D":
            code = x["clipPlotMat"].str.strip()
            date = pd.to_datetime(x["samplingDate"], format="%m/%d/%Y", errors="coerce")
            time = pd.Series(pd.NA, index=x.index)
            num = lambda c: pd.to_numeric(x[c], errors="coerce")
            mp = (num("wet_wt") - num("dry_wt")) / num("dry_wt") * 100
            src = pd.to_numeric(x["fm%"].str.rstrip("%"), errors="coerce")
            qa_w = ((mp - src).abs() > 1).map({True: "src_pct_mismatch", False: None})
            extra = "; unit=" + x["unitName"].str.strip() + "; sample_no=" + x["sampleNo"].astype(str)
        else:
            code = x[[c for c in x.columns if c.lower() == "fuel_type"][0]].str.strip()
            mcol = [c for c in x.columns if c.lower() == "fuel_moisture_content"][0]
            mp = pd.to_numeric(x[mcol], errors="coerce")
            qa_w = pd.Series(None, index=x.index)
            if ds == "W41S34":
                day = x["day_number"].str.strip().map({"1": "2022-02-03", "2": "2022-02-04"})
                date = pd.to_datetime(day, errors="coerce")
                time = hhmm(x["time"])
                extra = "; time_block=" + x["time_block"] + "; years_since_burn=" + x["tsb"] + "; replicate=" + x["replicate"]
            else:
                date = pd.to_datetime(dict(year=pd.to_numeric(x["Year"]), month=pd.to_numeric(x["Month"]),
                                           day=pd.to_numeric(x["Day"])), errors="coerce")
                time = hhmm(x["Time"])
                extra = "; time_block=" + x["Time_Block"] + "; replicate=" + x["Replicate"]
                if "Landcover_Type" in x:
                    extra = extra + "; landcover=" + x["Landcover_Type"].fillna("")
        m = code.map(codes)
        unknown = m.isna() & mp.notna()
        if unknown.any():
            raise SystemExit(f"{ds}: unmapped codes {code[unknown].unique()}")
        keep = mp.notna() & date.notna()
        print(ds, len(x), "rows,", int((~keep).sum()), "dropped (FE/blank)")
        qa = m.str[3].where(m.str[3].notna(), qa_w)
        part = pd.DataFrame({
            "source_record_id": ds + "#" + x["_row"].astype(str),
            "date": date, "time": time, "timezone": "America/New_York" if ds != "W4V30J" else "America/Chicago",
            "lat": lat, "lon": lon, "location_precision_m": prec, "country": "USA",
            "site_name": "WFSI " + NAMES[ds],
            "fuel_class": m.str[0], "fuel_type": m.str[1], "species": m.str[2],
            "moisture_pct": mp, "method": "oven_dry", "measured": True, "qa_flag": qa,
            "notes": ("gravimetric dry basis; doi:10.60594/" + ds + "; fuel_code=" + code + extra
                      + ("; location_approx (centre of %d burn units in EML coverage)" % nbox if nbox > 1
                         else "; location from EML coverage")),
        })[keep]
        parts.append(part)
    out = pd.concat(parts, ignore_index=True)
    out["qa_flag"] = out["qa_flag"].astype("string")
    neg = out["moisture_pct"] < 0
    out.loc[neg, "qa_flag"] = (out.loc[neg, "qa_flag"].fillna("") + ";negative_moisture").str.lstrip(";")
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
