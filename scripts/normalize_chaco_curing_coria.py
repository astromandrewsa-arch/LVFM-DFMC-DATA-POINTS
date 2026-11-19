"""Normalize the Dry Chaco grass curing field data (Coria 2026 supplement, figshare 31017410, CC BY 4.0).

Appendix 1 of the DOCX supplement: 105 frame samples (0.25 m2), weekly 28 Mar - 27 Aug 2025,
with curing % by three methods: destructive (reference), frame-based Levy rod, frame-based visual.
NO grass moisture content is reported. Per pipeline rules curing % is not moisture, so every row
has moisture_pct = null (qa_flag curing_only_no_moisture) and the curing values go to
covariates_by_source + notes. Sward is mixed green + cured -> fuel_class live, fuel_type grass,
notes mixed_curing. Rows are kept so the curing ground truth (dated, located) is usable as a
covariate / label for curing models.
Location: single site; the supplement takes its weather from the INTA "F. Cantos Experimental
Field" station (La Abrita, Silipica, Santiago del Estero, 28.02 S 64.23 W), so the site is
geocoded there with location_precision_m 5000 and notes location_approx.
"""
import re
import zipfile

import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "chaco_curing_coria"


def appendix1(docx_path):
    x = zipfile.ZipFile(docx_path).read("word/document.xml").decode("utf8")
    rows = []
    for tr in re.findall(r"<w:tr[ >].*?</w:tr>", x, re.S):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<w:tc[ >].*?</w:tc>", tr, re.S)]
        if len(cells) == 5 and re.match(r"\d{1,2}-[A-Za-z]{3}-\d{2}$", cells[0]):
            rows.append(cells)
    df = pd.DataFrame(rows, columns=["date", "sample", "destructive", "levy_rod", "visual"])
    for c in ["destructive", "levy_rod", "visual"]:
        df[c] = pd.to_numeric(df[c].replace(".", pd.NA), errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%y")
    return df


if __name__ == "__main__":
    df = appendix1(raw_dir(SOURCE_ID) / "uasr_a_2611270_sm4532.docx")
    print(len(df), "samples")
    assert len(df) == 105, len(df)
    out = pd.DataFrame({
        "source_record_id": df["date"].dt.strftime("%Y-%m-%d") + "#" + df["sample"],
        "date": df["date"], "time": pd.NA, "timezone": "America/Argentina/Cordoba",
        "lat": -28.02, "lon": -64.23, "location_precision_m": 5000,
        "country": "Argentina", "site_name": "Dry Chaco grassland, INTA Santiago del Estero (F. Cantos field)",
        "fuel_class": "live", "fuel_type": "grass",
        "species": "mixed C4 grass sward (Setaria lachnea, Leptochloa pluriflora, Megathyrsus maximus ...)",
        "moisture_pct": pd.NA, "method": "other", "measured": True,
        "qa_flag": "curing_only_no_moisture",
        "notes": ("mixed_curing; curing_destructive_pct=" + df["destructive"].astype(str)
                  + "; curing_levy_rod_pct=" + df["levy_rod"].astype("string").fillna("NA")
                  + "; curing_visual_pct=" + df["visual"].astype(str)
                  + "; no moisture measured; location_approx"),
    })
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    finalize(out, SOURCE_ID)
    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "source_provided(Coria 2026 Appendix 1)",
        "curing_destructive_pct": df["destructive"], "curing_levy_rod_pct": df["levy_rod"],
        "curing_visual_pct": df["visual"],
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
