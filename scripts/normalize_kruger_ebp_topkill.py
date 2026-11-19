"""Normalize the Kruger plot-scale fire database of Ongole et al. (2026) (Zenodo 23915836, CC-BY-4.0).

Source file: data/pfe_and_lfe_fires.csv (1,660 rows). Per README:
  m = observed fuel moisture (proportion); fuel.load.gm.m2 = fuel load (g/m2);
  INTEN = observed fire intensity (kW/m); PLOTROS = rate of spread (m/s);
  vpd = max VPD in the 7 days before the fire, from ERA5-Land (kPa; NOT measured);
  windsp = mean wind on fire day, from ERA5-Land (m/s; NOT measured);
  Location = Kruger landscape (Pretoriuskop, Skukuza, Satara, Mopani); FIRESEASON = WET/DRY.
fireid 1-1274: plot fire experiments (PFE, Experimental Burn Plots) with measured intensity;
1275-1586: PFE fires without intensity; 1587-1660: one landscape fire experiment (LFE,
"afsaal" fire near Skukuza) whose single moisture value is repeated for 74 tree plots.

Decisions:
- Moisture basis: the authors' JAGS model (scripts.zip) computes rate of spread as
  ... / (3015*m + Qv*(1-m)), i.e. m is the water fraction of fresh (wet) mass. So m is
  treated as wet basis and converted to % of dry weight: 100*m/(1-m). Raw m kept in notes
  and covariates (fuel_moisture_wet_fraction) so the conversion can be reverted.
- Sward = mixed green + cured grass at time of burn -> fuel_class live, fuel_type grass,
  notes "mixed_curing" (the source does not separate live/dead).
- No dates or coordinates are in the data. Date left null; FIRESEASON (given) kept in notes;
  no year is given. Location geocoded to an approximate centroid of the four EBP strings in
  that landscape (strings are within ~20 km of each other; string not given) ->
  location_precision_m = 15000 and notes "location_approx". The LFE fire is put at Skukuza.
- LFE: the 74 tree-plot rows carry only a few distinct fire moisture samples; collapsed to
  one row per distinct moisture sample (3 samples over the 74 tree-plot rows) with notes
  "aggregated_mean n=<k>" (fuel load, VPD, wind = means over those plots, in covariates).
- PFE rows that share an identical (landscape, season, m, vpd) were probably burned the same day
  with one moisture sample; they are kept (one row per fire) and annotated shared_value_n=<k>.
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "kruger_ebp_topkill"

# Approximate centroids of the 4 EBP strings per landscape (Biggs et al. 2003 Koedoe 46:1-15;
# strings named in Riddell et al. 2012 Koedoe 54). Derived from rest camp / landmark positions:
# Pretoriuskop (Fayi, Kambeni, Numbi, Shabeni), Skukuza (Biyamiti, Skukuza, N'washitshaka, Napi),
# Satara (Satara, Lindanda, Marheya, N'wanetsi), Mopani (Dzombo, Mooiplaas, Tsende, Nshawo).
LANDSCAPE_XY = {
    "Pretoriuskop": (-25.15, 31.30),
    "Skukuza": (-25.05, 31.55),
    "Satara": (-24.40, 31.80),
    "Mopani": (-23.50, 31.40),
}
PRECISION_M = 15000

if __name__ == "__main__":
    src = raw_dir(SOURCE_ID) / "data" / "data" / "pfe_and_lfe_fires.csv"
    df = pd.read_csv(src)
    df = df.rename(columns={"Unnamed: 0": "src_row"})
    print(len(df), "raw rows")
    assert df["m"].between(0, 1, inclusive="neither").all()

    df["exp"] = pd.cut(df["fireid"], [0, 1274, 1586, 10**9], labels=["PFE", "PFE_noInten", "LFE"]).astype(str)

    lfe = df[df["exp"] == "LFE"]
    # 74 LFE tree-plot rows carry only 3 distinct moisture samples (m, season); one row per sample.
    lfe_row = (lfe.groupby(["m", "FIRESEASON", "Location"], as_index=False)
               .agg(**{"fuel.load.gm.m2": ("fuel.load.gm.m2", "mean"), "vpd": ("vpd", "mean"),
                       "windsp": ("windsp", "mean"), "src_row": ("src_row", "first"),
                       "fid_min": ("fireid", "min"), "fid_max": ("fireid", "max"),
                       "n_agg": ("fireid", "size"), "INTEN": ("INTEN", "first"),
                       "PLOTROS": ("PLOTROS", "first")}))
    lfe_row["exp"] = "LFE"
    lfe_row["fireid_label"] = ("LFE_m" + lfe_row["m"].round(6).astype(str) + "_"
                               + lfe_row["fid_min"].astype(str) + "-" + lfe_row["fid_max"].astype(str))
    pfe = df[df["exp"] != "LFE"].copy()
    pfe["fireid_label"] = pfe["fireid"].astype(str)
    pfe["n_agg"] = 1
    pfe["shared_n"] = pfe.groupby(["Location", "FIRESEASON", "m", "vpd"])["m"].transform("size")
    lfe_row["shared_n"] = 1
    d = pd.concat([pfe, lfe_row], ignore_index=True)

    moist = (100 * d["m"] / (1 - d["m"])).round(2)
    notes = ("fire_season=" + d["FIRESEASON"] + "; experiment=" + d["exp"]
             + "; landscape=" + d["Location"]
             + "; m_wet_fraction=" + d["m"].round(6).astype(str)
             + "; converted_from_wet_basis (m/(1-m)*100; basis inferred from source model 3015*m+Qv*(1-m))"
             + "; mixed_curing; location_approx (landscape centroid of 4 EBP strings, string unknown)"
             + "; no_date_in_source; vpd/wind in covariates are ERA5-Land, not measured")
    notes = notes.where(d["shared_n"] <= 1, notes + "; shared_value_n=" + d["shared_n"].astype(str))
    notes = notes.where(d["n_agg"] <= 1,
                        notes + "; aggregated_mean n=" + d["n_agg"].astype(str)
                        + " tree plots of the landscape fire share this moisture sample; fuel load/vpd/wind averaged)")

    lat = d["Location"].map(lambda k: LANDSCAPE_XY[k][0])
    lon = d["Location"].map(lambda k: LANDSCAPE_XY[k][1])
    out = pd.DataFrame({
        "source_record_id": "fireid=" + d["fireid_label"],
        "date": pd.NaT,
        "time": pd.NA,
        "timezone": "Africa/Johannesburg",
        "lat": lat,
        "lon": lon,
        "location_precision_m": PRECISION_M,
        "country": "South Africa",
        "site_name": "Kruger NP EBP " + d["Location"] + " landscape",
        "fuel_class": "live",
        "fuel_type": "grass",
        "species": "grass sward (mixed species)",
        "moisture_pct": moist,
        "method": "oven_dry",
        "measured": True,
        "qa_flag": "no_date",
        "notes": notes,
    })
    out.loc[d["exp"].eq("LFE").values, "site_name"] = "Kruger NP Skukuza landscape fire experiment (afsaal)"
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)

    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "source_provided(Ongole et al. 2026; vpd & wind = ERA5-Land, others measured)",
        "fuel_moisture_wet_fraction": d["m"],
        "fuel_load_kg_m2": d["fuel.load.gm.m2"] / 1000.0,
        "vpd_max_7d_kpa_era5land": d["vpd"],
        "wind_mean_ms_era5land": d["windsp"],
        "fire_intensity_kw_m": d["INTEN"],
        "rate_of_spread_ms": d["PLOTROS"],
        "fire_season": d["FIRESEASON"],
        "landscape": d["Location"],
        "source_row_index": d["src_row"],
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
