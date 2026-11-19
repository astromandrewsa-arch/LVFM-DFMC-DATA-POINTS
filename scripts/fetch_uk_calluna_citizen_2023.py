"""Fetch "Fuel moisture and micro-scale combustion calorimetry data for Calluna vulgaris across
the UK, April-May 2023" (Ivison, Little, Belcher, Crawford, Davidson, Graham, Kettridge; citizen
science, 830 samples). NERC EIDC 10.5285/64d340d7-8f19-49f9-90e0-83d4013e76c2, Open Government
Licence v3. Not part of the UKFDRS EIDC 9334118f database (no date+FMC matches).
"""
import json
import zipfile

from common import download, raw_dir, session

SOURCE_ID = "uk_calluna_citizen_2023"
EIDC = "64d340d7-8f19-49f9-90e0-83d4013e76c2"

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
