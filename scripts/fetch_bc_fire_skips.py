"""Fetch BC fire-skips fuel moisture content dataset (Xiao, Zenodo). License CC-BY-4.0.

Concept DOI 10.5281/zenodo.17087197 -> latest version record 17173324.
Foliage, fine woody debris and duff gravimetric FMC, Prince George & Smithers BC, 2021-2022.
"""
from common import download, raw_dir, session

SOURCE_ID = "bc_fire_skips"
RECORD = "17173324"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60)
    meta.raise_for_status()
    (d / "zenodo_record.json").write_bytes(meta.content)
    for f in meta.json()["files"]:
        p = download(f["links"]["self"], d / f["key"], sess=s)
        print(p, p.stat().st_size)
