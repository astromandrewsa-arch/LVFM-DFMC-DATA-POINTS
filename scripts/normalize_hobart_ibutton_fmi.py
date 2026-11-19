"""Normalize the Hobart iButton FMI study data (figshare 20305317, CC BY 4.0; Bowman et al. 2022 Fire 5:130).

fmc_data.csv has one row per (sampling visit, site, litter disk, elevated iButton): each of the 2-3
litter disks per visit appears twice (once per elevated '_E' logger). Per the paper:
- MC_fuel  = gravimetric litter moisture of a litter disk (oven dried 105 C >= 24 h) -> litter,
             oven_dry; one observation per distinct litter disk.
- MC_Stick = gravimetric moisture of an array of three Pinus radiata fuel moisture sticks 30 cm
             above the litter, weighed in the field -> fuel_type stick, method fuel_stick; one
             observation per visit and site.
- MProbe   = an unspecified probe reading (instrument not described) -> covariate only.
Samples were collected 11:00-15:00 local; the dataset timestamp (02:00Z) is nominal, so time is
left null. Sites are on Hobart's wildland-urban interface (paper Fig. 1 map, no coordinates) ->
geocoded to Hobart WUI, location_precision_m 8000, notes location_approx.
Covariates: in-disk iButton T/RH/FMI (1 h and 24 h means), elevated iButtons averaged over the two
loggers, Soil Dryness Index and Drought Factor (met_join_data.csv, Hobart BoM station).
"""
import pandas as pd

from common import NORM, finalize, make_obs_id, raw_dir

SOURCE_ID = "hobart_ibutton_fmi"
LAT, LON = -42.89, 147.28

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    met = pd.read_csv(d / "met_join_data.csv")
    print(len(met), "raw rows")
    met["date"] = pd.to_datetime(met["Timestamp"], utc=True).dt.tz_convert("Australia/Hobart").dt.date
    disk_key = ["Timestamp", "SiteCode", "MC_fuel", "MProbe", "Temp1", "RH1"]
    elev = (met.groupby(["Timestamp", "SiteCode"])
            [["Temp1_E", "RH1_E", "FMI1_E", "Temp24_E", "RH24_E", "FMI24_E"]].mean())
    disks = met.drop_duplicates(disk_key).copy()
    disks["disk"] = disks.groupby(["Timestamp", "SiteCode"]).cumcount() + 1
    sticks = met.drop_duplicates(["Timestamp", "SiteCode"]).copy()
    print(len(disks), "litter disks;", len(sticks), "stick weighings")

    common = dict(time=pd.NA, timezone="Australia/Hobart", lat=LAT, lon=LON, location_precision_m=8000,
                  country="Australia", fuel_class="dead", measured=True, qa_flag=pd.NA)
    lit = pd.DataFrame({
        "source_record_id": disks["SiteCode"] + "@" + disks["Timestamp"] + "#disk" + disks["disk"].astype(str),
        "date": disks["date"], "site_name": "Hobart " + disks["SiteCode"] + " (" + disks["ForestType"] + " Eucalyptus forest)",
        "fuel_type": "litter", "species": "Eucalyptus leaf litter", "moisture_pct": disks["MC_fuel"],
        "method": "oven_dry",
        "notes": ("litter disk gravimetric (105C oven); forest=" + disks["ForestType"]
                  + "; collected 11:00-15:00 local; location_approx (Hobart WUI, site coords not published)"),
        **common})
    stk = pd.DataFrame({
        "source_record_id": sticks["SiteCode"] + "@" + sticks["Timestamp"] + "#sticks",
        "date": sticks["date"], "site_name": "Hobart " + sticks["SiteCode"] + " (" + sticks["ForestType"] + " Eucalyptus forest)",
        "fuel_type": "stick", "species": "Pinus radiata fuel moisture sticks (3, 30 cm above litter)",
        "moisture_pct": sticks["MC_Stick"], "method": "fuel_stick",
        "notes": ("field-weighed 10-h fuel moisture stick array; forest=" + sticks["ForestType"]
                  + "; collected 11:00-15:00 local; location_approx (Hobart WUI, site coords not published)"),
        **common})
    out = pd.concat([lit, stk], ignore_index=True)
    out["observation_id"] = [make_obs_id(SOURCE_ID, r) for r in out["source_record_id"]]
    assert out["observation_id"].is_unique
    finalize(out, SOURCE_ID)

    src = pd.concat([disks.assign(kind="disk"), sticks.assign(kind="stick")], ignore_index=True)
    e = elev.loc[list(zip(src["Timestamp"], src["SiteCode"]))].reset_index(drop=True)
    is_disk = src["kind"].eq("disk")
    cov = pd.DataFrame({
        "observation_id": out["observation_id"],
        "cov_source": "source_provided(iButton loggers; SDI/DF from BoM Hobart via authors)",
        "litter_ibutton_temp_1h_c": src["Temp1"].where(is_disk),
        "litter_ibutton_rh_1h_pct": src["RH1"].where(is_disk),
        "litter_ibutton_fmi_1h": src["FMI1"].where(is_disk),
        "litter_ibutton_temp_24h_c": src["Temp24"].where(is_disk),
        "litter_ibutton_rh_24h_pct": src["RH24"].where(is_disk),
        "litter_ibutton_fmi_24h": src["FMI24"].where(is_disk),
        "mprobe_reading": src["MProbe"].where(is_disk),
        "elev075m_temp_1h_c": e["Temp1_E"], "elev075m_rh_1h_pct": e["RH1_E"], "elev075m_fmi_1h": e["FMI1_E"],
        "elev075m_temp_24h_c": e["Temp24_E"], "elev075m_rh_24h_pct": e["RH24_E"], "elev075m_fmi_24h": e["FMI24_E"],
        "soil_dryness_index_mm": src["SDI"], "drought_factor": src["DF"],
        "forest_type": src["ForestType"],
    })
    cd = NORM / "covariates_by_source"
    cd.mkdir(parents=True, exist_ok=True)
    cov.to_parquet(cd / f"{SOURCE_ID}.parquet", index=False)
    print("covariates", len(cov))
