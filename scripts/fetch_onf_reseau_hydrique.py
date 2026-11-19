"""Fetch the ONF "Reseau Hydrique" multisite/multispecies LFMC series, French Mediterranean
1996-2016 (Duche, Savazzi, Toutchkov, Cabanne 2017; Martin-StPaul et al. 2018 Data in Brief).
License CC-BY-4.0. Zenodo record 162978 (DOI 10.5281/zenodo.162978).
"""
import json

from common import download, raw_dir, session

SOURCE_ID = "onf_reseau_hydrique"
RECORD = 162978

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60).json()
    (d / "zenodo_record.json").write_text(json.dumps(meta, indent=1))
    for f in meta["files"]:
        p = download(f["links"]["self"], d / f["key"], sess=s)
        print(p, p.stat().st_size)
