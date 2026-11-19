"""Normalize the Canadian Forest Service historic Fuel Moisture Data File (G0000391), 1931-1961.

Source: Library and Archives Canada open data, Open Government Licence - Canada. Fixed-width
records (codebook G0000391_Codebook-OCR.pdf, Public Archives Canada 1979): one record per fuel
moisture observation with the nearest-in-time weather and the noon weather attached.
Columns (1-based): 2-6 location (2-digit province, station, 2-digit site), 8-13 YYMMDD,
15-18 time (24 h), 20 general type, 22-24 field title code, 26-27 sample description,
29-33 moisture content (% oven-dry basis, explicit decimal), 35-38 matched weather time,
40-41 dry bulb F, 43-44 wet bulb F, 46-47 RH %, 49-50 max T F, 52-53 min T F,
55-57 24 h precip (0.01 in), 77-78 wind mph; noon weather 81-84 time, 86-87 dry bulb,
89-90 wet bulb, 92-93 RH, 95-97 precip, 100-101 wind.

General types (col 20) and how they are mapped:
  4 oven-dried samples (duff horizons, tree foliage, lichen, moss, shrubs, ferns, grass, misc
    dead fuels) -> method oven_dry
  5 oven-dried log borings (8 depth classes)       -> dead 1000hr, oven_dry
  6 match-splint trays / moss & lichen trays (exposed indicator material weighed daily)
                                                     -> method other (indicator), dead
  7 hazard sticks (wood sticks of several sizes, flat sticks, B.C. hazard stick sets)
                                                     -> method fuel_stick, fuel_type stick
  8 weigh-beam / express-scale logs (heavy fuel indicators) -> dead 1000hr, method other
All are real measurements (measured=True). Moisture 0.0 (656 records, used for 'not read' on
indicator rows) and >= 999 are dropped; invalid dates (codebook: month/day codes 16/44/58
unknown) and years outside 1930-1962 are dropped. Dead fine/stick/log values > 400 % are
flagged implausible_high. Unknown station codes (60406, 60408, 60806, 50606, xx100) are dropped.
Codes not decodable unambiguously from the OCR'd codebook are kept with the raw code in notes.

Locations: the files give station/site codes only; stations are geocoded to the named
experiment station / town -> location_approx with location_precision_m 10-50 km.
"""
import numpy as np
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "cfs_testfire_fmc"
# province+station -> (name, lat, lon, precision_m, province)
STATIONS = {
    "401": ("Petawawa Forest Experiment Station", 45.99, -77.43, 10000, "ON"),
    "501": ("Whiteshell (Forest Reserve)", 49.80, -95.30, 40000, "MB"),
    "601": ("Bittern Creek", 53.70, -105.50, 50000, "SK"),
    "701": ("Kananaskis Forest Experiment Station", 51.03, -115.03, 10000, "AB"),
    "702": ("Whitecourt", 54.14, -115.68, 20000, "AB"),
    "801": ("100 Mile House", 51.64, -121.29, 20000, "BC"),
    "802": ("Lake Cowichan", 48.82, -124.10, 15000, "BC"),
    "901": ("Fort Smith", 60.00, -111.89, 20000, "NT"),
    "261": ("Fredericton (Acadia FES)", 45.96, -66.50, 25000, "NB"),
    "301": ("Valcartier Forest Experiment Station", 46.95, -71.47, 10000, "QC"),
    "101": ("Rattling Brook", 49.10, -55.30, 50000, "NL"),
}
TREE = {101: "Pinus sp.", 102: "Pinus strobus", 103: "Pinus resinosa", 104: "Pinus banksiana",
        105: "Pinus contorta var. latifolia", 106: "Pinus contorta var. contorta", 107: "Pinus ponderosa",
        108: "Pinus monticola", 110: "Picea sp.", 111: "Picea mariana", 112: "Picea rubens",
        113: "Picea glauca", 114: "Picea engelmannii", 115: "Picea sitchensis", 120: "Abies sp.",
        121: "Abies balsamea", 122: "Abies lasiocarpa", 123: "Abies grandis", 124: "Abies amabilis",
        125: "Pseudotsuga menziesii", 130: "Larix sp.", 131: "Larix laricina", 132: "Larix lyallii",
        133: "Larix occidentalis", 140: "Thuja/Cedar sp.", 141: "Thuja occidentalis", 142: "Thuja plicata",
        143: "Callitropsis nootkatensis", 144: "Juniperus virginiana", 145: "Juniperus scopulorum",
        150: "Tsuga sp.", 151: "Tsuga canadensis", 152: "Tsuga heterophylla", 153: "Tsuga mertensiana",
        160: "Populus sp.", 161: "Populus tremuloides", 162: "Populus grandidentata",
        163: "Populus balsamifera", 168: "Populus trichocarpa", 170: "Betula sp.", 171: "Betula papyrifera",
        172: "Betula alleghaniensis", 180: "Acer sp.", 181: "Acer saccharum", 182: "Acer rubrum",
        190: "Alnus sp. (tree)", 198: "Quercus sp.", 199: "Salix sp."}
DUFF = {0: ("duff", "duff/soil horizon not classified"), 1: ("litter", "fresh leaf fall"),
        2: ("duff", "top layer duff (TLD)"), 3: ("duff", "middle layer duff (MLD)"),
        4: ("duff", "bottom layer duff (BLD)"), 5: ("duff", "full layer duff (FLD)"),
        6: ("duff", "full organic layer (FOL)"), 8: ("duff", "peat")}
SHRUB = {400: "low shrub n.c.", 401: "blueberry", 402: "cranberry", 403: "bearberry", 404: "Labrador tea",
         405: "shrub code 405 ('Goldworthy' in OCR codebook)", 406: "sweet fern", 407: "salal (green)", 408: "juniper",
         409: "buffaloberry", 410: "fireweed", 411: "salal (dead)", 420: "high shrub n.c.", 421: "hazel",
         422: "alder", 423: "willow"}
MISC = {901: ("dead", "other", "chips of logs"), 902: ("dead", "fine_dead", "branches off ground"),
        903: ("dead", "other", "bark of trees"), 904: ("live", "herb", "herbs, general"),
        905: ("dead", "other", "cones"), 911: ("dead", "fine_dead", "twigs on ground (TOG)"),
        912: ("dead", "fine_dead", "twigs on trees (TOT)"), 913: ("dead", "fine_dead", "twigs on slash"),
        920: ("dead", "other", "slash, general"), 921: ("dead", "other", "slash, green needles/leaves/twigs"),
        922: ("dead", "fine_dead", "slash, leaves/needles and twigs (dead)"),
        924: ("dead", "fine_dead", "slash twigs and branches"), 925: ("dead", "10hr", "slash pieces"),
        930: ("dead", "dead_foliage", "needles off slash / dead trees (NOS)"),
        931: ("dead", "other", "dead vegetation"), 932: ("dead", "other", "vegetation not specified")}
DEPTH = {"1": "0-1/4 in", "2": "5/16-1/2 in", "3": "9/16-3/4 in", "4": "13/16-1 in", "5": "1-1/16-1-1/2 in",
         "6": "1-9/16-2 in", "7": "2-1/16-3 in", "8": "3-1/16-4 in"}


def classify(gt, code_s, desc_s):
    """Return (fuel_class, fuel_type, species, method, label, qa)."""
    code = int(code_s) if code_s.strip().isdigit() else -1
    desc = int(desc_s) if desc_s.strip().isdigit() else 0
    if gt == "4":
        if code in DUFF:
            ft, lab = DUFF[code]
            return "dead", ft, None, "oven_dry", lab, None
        if 100 <= code <= 199:
            sp = TREE.get(code, f"tree code {code}")
            if desc in (33,):
                return "dead", "fine_dead", sp, "oven_dry", "twigs, dead branches", None
            if desc in (31, 32):
                return "live", "other", sp, "oven_dry", "living twigs", None
            return "live", "tree_foliage", sp, "oven_dry", f"tree foliage (desc {desc:02d})", None
        if 200 <= code <= 299:
            return "dead", "other", "Cladonia/lichen", "oven_dry", f"lichen (code {code})", "class_ambiguous_lichen"
        if 300 <= code <= 399:
            return "dead", "other", "moss", "oven_dry", f"moss (code {code})", "class_ambiguous_moss"
        if 400 <= code <= 499:
            lab = SHRUB.get(code, f"shrub code {code}")
            if code == 411 or desc == 3:
                return "dead", "dead_foliage" if code == 411 else "fine_dead", lab, "oven_dry", lab, None
            return "live", "shrub", lab, "oven_dry", lab, None
        if 500 <= code <= 599:
            if code == 530:
                return "dead", "dead_foliage", "fern", "oven_dry", "dead fern on ground (TLDF)", None
            return "live", "herb", "fern (bracken etc.)", "oven_dry", f"fern (code {code})", None
        if code == 600:
            return "dead", "grass", None, "oven_dry", "grass", "live_dead_unspecified"
        if code in MISC:
            fc, ft, lab = MISC[code]
            return fc, ft, None, "oven_dry", lab, None
        return None
    if gt == "5":
        sp = TREE.get(code, f"tree code {code}" if code > 0 else None)
        dep = DEPTH.get(desc_s.strip()[-1:] if desc_s.strip() else "", "depth n/a")
        return "dead", "1000hr", sp, "oven_dry", f"windfall log boring, depth {dep}", None
    if gt == "6":
        c = code % 100
        if c in (0, 1, 2, 3, 4):
            return "dead", "stick", "match splints", "other", f"match-splint tray (basket code {c:02d})", "indicator_tray"
        if c == 50:
            return "dead", "other", "lichen tray", "other", "lichen tray (uncorrected)", "indicator_tray"
        if 10 <= c <= 43:
            return "dead", "other", "moss tray", "other", f"moss tray (species code {c})", "indicator_tray"
        return None
    if gt == "7":
        if code_s.strip() == "6":
            return "dead", "stick", "white pine flat sticks", "fuel_stick", f"flat sticks (exposure/n code {desc_s.strip()})", None
        if code_s.strip() == "7":
            return "dead", "stick", "B.C. hazard sticks", "fuel_stick", f"B.C. hazard stick set (code {desc_s.strip()})", None
        cs = code_s.strip().rjust(3)
        size = {"1": "size class I", "2": "size class II", "3": "3/4 in", "4": "1 in", "5": "2 in"}.get(cs[0], "size ?")
        shape = {"1": "square", "2": "round", "3": "square 6 in long"}.get(cs[1], "?")
        sp = TREE.get(100 + desc, None) if desc else None
        return "dead", "stick", sp, "fuel_stick", f"hazard stick {size}, {shape}, exposure code {cs[2]}", None
    if gt == "8":
        n = code_s.strip()
        kind = "weigh-beam log" if n in "12345" else "express-scale log set"
        sp = TREE.get(100 + desc, None) if desc else None
        return "dead", "1000hr", sp, "other", f"{kind} #{n} (heavy fuel indicator)", "indicator_log"
    return None


def num(s, scale=1.0):
    s = s.strip()
    try:
        return float(s) * scale
    except ValueError:
        return np.nan


if __name__ == "__main__":
    src = raw_dir(SOURCE_ID) / "G0000391.txt"
    lines = [l for l in src.read_text(encoding="latin-1").split("\n") if l.strip()]
    rows, covs, skipped = [], [], {"station": 0, "date": 0, "mc": 0, "code": 0}
    for i, l in enumerate(lines):
        l = l.ljust(102)
        loc, ymd, tm, gt, code, desc, mc = l[1:6], l[7:13], l[14:18], l[19], l[21:24], l[25:27], l[28:33]
        st = STATIONS.get(loc[:3])
        if st is None or loc[3:] == "00":
            skipped["station"] += 1
            continue
        try:
            date = pd.Timestamp(year=1900 + int(ymd[:2]), month=int(ymd[2:4]), day=int(ymd[4:6]))
            if not 1930 <= date.year <= 1962:  # programme ran 1931-1961; other years are miscodes
                raise ValueError
        except ValueError:
            skipped["date"] += 1
            continue
        m = num(mc)
        if not (m > 0) or m >= 999:
            skipped["mc"] += 1
            continue
        c = classify(gt, code, desc)
        if c is None:
            skipped["code"] += 1
            continue
        fc, ft, sp, method, label, qa = c
        t = tm.strip()
        time = f"{int(t) // 100:02d}:{int(t) % 100:02d}" if t.isdigit() and int(t) % 100 < 60 and int(t) < 2400 else None
        rid = f"L{i}"
        rows.append((rid, date, time, st[1], st[2], st[3], f"{st[0]} site {loc} ({st[4]})", fc, ft, sp, m, method, qa,
                     f"CFS fuel moisture file G0000391; type={gt}; field_code={code.strip()}; desc={desc.strip()}; "
                     f"{label}; location_approx (station geocoded from name)"))
        F = lambda s: (num(s) - 32) * 5 / 9
        covs.append((rid, F(l[39:41]), F(l[42:44]), num(l[45:47]), F(l[48:50]), F(l[51:53]),
                     num(l[54:57], 0.254), num(l[76:78], 0.44704), l[34:38].strip(),
                     F(l[85:87]), num(l[91:93]), num(l[94:97], 0.254), num(l[99:101], 0.44704)))
    print(len(lines), "records;", len(rows), "kept; skipped", skipped)
    out = pd.DataFrame(rows, columns=["source_record_id", "date", "time", "lat", "lon", "location_precision_m",
                                      "site_name", "fuel_class", "fuel_type", "species", "moisture_pct",
                                      "method", "qa_flag", "notes"])
    hi = (out["fuel_type"].isin(["stick", "1hr", "10hr", "100hr", "1000hr", "fine_dead", "litter", "grass"])
          & (out["moisture_pct"] > 400))
    out.loc[hi, "qa_flag"] = (out.loc[hi, "qa_flag"].fillna("") + ";implausible_high").str.lstrip(";")
    out["timezone"] = "local"
    out["country"] = "Canada"
    out["measured"] = True
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
    cov = pd.DataFrame(covs, columns=["source_record_id", "obs_temp_c", "obs_wetbulb_c", "obs_rh_pct",
                                      "tmax_c", "tmin_c", "precip_24h_mm", "obs_wind_ms", "obs_time_hhmm",
                                      "noon_temp_c", "noon_rh_pct", "noon_precip_24h_mm", "noon_wind_ms"])
    cov.insert(0, "observation_id", out["observation_id"].values)
    cov = cov.drop(columns="source_record_id")
    cov.insert(1, "cov_source", "source_measured(station weather matched by time + noon)")
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
