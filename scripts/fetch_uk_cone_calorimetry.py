"""Fetch "Flammability metrics from cone calorimetry for common wildfire fuels sampled in Great
Britain from 2021-2023" (Belcher et al.; UKFDRS). 1634 cone tests on 833 samples from 22 sites;
one gravimetric FMC (dry basis) per sample (+ duff moisture under litter samples) and in-situ
weather. NERC EIDC 10.5285/45af9c3d-999d-44dd-83fc-b4d81632967d, Open Government Licence v3.
Separate samples from the UKFDRS EIDC 9334118f database (<1% date+FMC coincidences).
"""
import json
import zipfile

from common import download, raw_dir, session

SOURCE_ID = "uk_cone_calorimetry"
EIDC = "45af9c3d-999d-44dd-83fc-b4d81632967d"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://catalogue.ceh.ac.uk/documents/{EIDC}",
                 headers={"Accept": "application/json"}, timeout=60).json()
    (d / "eidc_record.json").write_text(json.dumps(meta, indent=1))
    z = download(f"https://data-package.ceh.ac.uk/data/{EIDC}.zip", d / f"eidc_{EIDC}.zip", sess=s)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(d / "eidc")
        print(zf.namelist())
