"""Fetch "Sensitivity of fire weather indices, fuel sticks and satellite observations to fuel
moisture content in Central European forests - Data" (Kranz, Bauer, Pampanoni, Zhao, Marrs,
Mauder, Podebradska, van der Maaten-Theunissen 2024), Saxony, Germany, 2022-2023.
Zenodo 10.5281/zenodo.12732295 v1.0, CC-BY-4.0. One zip (FMC2022_2023_saxony.zip) with
destructive FMC samples (FMC_insitu), 30-min fire weather station series incl. 10-h fuel stick
sensors (FWS_30min) and daily FWI (FWS_FWI_24h). The zip is extracted next to itself.
"""
import json

from common import download, raw_dir, session

SOURCE_ID = "saxony_fmc_sticks"
RECORD = 12732295

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60).json()
    (d / "zenodo_record.json").write_text(json.dumps(meta, indent=1))
    for f in meta["files"]:
        p = download(f["links"]["self"], d / f["key"], sess=s)
        print(p, p.stat().st_size)
        if p.suffix == ".zip":
            import zipfile
            with zipfile.ZipFile(p) as zf:
                zf.extractall(d / "extracted")
                print(zf.namelist())
