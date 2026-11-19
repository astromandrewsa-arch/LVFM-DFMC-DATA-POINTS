"""Normalize RDS-2009-0003 (Lubrecht Experimental Forest prescribed fire study, Montana, 1973).

BURNED_PLOT_MOISTURE_CONTENT.csv: for each of 20 burned 25 x 25 m plots (Douglas-fir / western
larch stand), pre-burn moisture content (%) of 0-0.25 in and 0.25-1 in dead woody fuels, upper
and lower duff, and herbaceous fuels, on the burn date (Norum 1973 study). One value per plot and
fuel class (sampling n not published) -> notes 'aggregated_mean n=unknown'. Basis not stated
-> 'basis_unclear' (USFS convention: dry weight). Herbaceous live/dead status not stated; values
91-343 % indicate mostly live herbs -> fuel_class live, qa 'live_dead_unspecified'.
Location: metadata gives only the Experimental Forest centre (46.89167, -113.4333) and elevation
4600-4800 ft -> location_approx, precision 5 km. Effective wind speed (mph) and RH at burn time
from EFFECTIVE_WINDSPEED_AND_RH.csv go to covariates.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir
from rds import find

SOURCE_ID = "usfs_lubrecht_rx"
LAT, LON = 46.89167, -113.4333
COLS = {
    "0-0.25 IN MOISTURE CONTENT": ("dead", "1hr", "dead woody 0-0.25 in", None),
    "0.25-1.0 IN MOISTURE CONTENT": ("dead", "10hr", "dead woody 0.25-1.0 in", None),
    "UPPER DUFF MOISTURE CONTENT": ("dead", "duff", "upper duff", None),
    "LOWER DUFF MOISTURE CONTENT": ("dead", "duff", "lower duff", None),
    "HERBACEOUS MOISTURE CONTENT": ("live", "herb", "herbaceous fuels", "live_dead_unspecified"),
}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    fm = pd.read_csv(find(d, "BURNED_PLOT_MOISTURE_CONTENT.csv"), encoding="latin-1")
    fm.columns = [c.strip() for c in fm.columns]
    wx = pd.read_csv(find(d, "EFFECTIVE_WINDSPEED_AND_RH.csv"), encoding="latin-1")
    wx.columns = [c.strip().upper() for c in wx.columns]
    print("wx cols", wx.columns.tolist())
    plotcol = [c for c in wx.columns if "PLOT" in c][0]
    wcol = [c for c in wx.columns if "WIND" in c][0]
    rhcol = [c for c in wx.columns if "HUMID" in c or c == "RH"][0]
    wx = wx.set_index(plotcol)
    rows, covs = [], []
    for col, (fc, ft, label, qa) in COLS.items():
        v = pd.to_numeric(fm[col], errors="coerce")
        sub = fm[v.notna()]
        rid = "plot" + sub["PLOTNUMBER"].astype(str) + "|" + label
        r = pd.DataFrame({
            "source_record_id": rid,
            "date": pd.to_datetime(sub["DATE OF BURN"], format="%m/%d/%Y", errors="coerce"),
            "time": pd.NA, "timezone": "America/Denver",
            "lat": LAT, "lon": LON, "location_precision_m": 5000.0, "country": "USA",
            "site_name": "Lubrecht EF plot " + sub["PLOTNUMBER"].astype(str) + " (MT)",
            "fuel_class": fc, "fuel_type": ft, "species": pd.NA,
            "moisture_pct": v[sub.index], "method": "oven_dry", "measured": True, "qa_flag": qa,
            "notes": ("aggregated_mean n=unknown; basis_unclear; pre-burn on burn date; category=" + label
                      + "; location_approx (Experimental Forest centre; plots in a Douglas-fir/western larch stand)"),
        })
        r["observation_id"] = [make_obs_id(SOURCE_ID, x) for x in rid]
        rows.append(r)
        p = sub["PLOTNUMBER"]
        covs.append(pd.DataFrame({
            "observation_id": r["observation_id"], "cov_source": "source_measured(at burn)",
            "obs_rh_pct": pd.to_numeric(p.map(wx[rhcol]), errors="coerce") * 100,  # stored as fraction
            "effective_wind_ms": pd.to_numeric(p.map(wx[wcol]), errors="coerce") * 0.44704,
        }))
    out = pd.concat(rows, ignore_index=True)
    finalize(out, SOURCE_ID)
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    pd.concat(covs, ignore_index=True).to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
