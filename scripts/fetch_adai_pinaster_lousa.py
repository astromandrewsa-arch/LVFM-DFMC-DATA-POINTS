"""Fetch "Field measurements of moisture content of dead leaves of Pinus pinaster (2014-2023)"
(Viegas, Alves, Almeida, Ribeiro, Viegas, Rodrigues; ADAI/CEIF, Univ. Coimbra), Lousa, Portugal.
Zenodo 10.5281/zenodo.13147079, CC-BY-4.0. Files: xlsx (Info + mf_data sheets) and PDF (methods).

Note: the larger CEIF-ADAI dataset (DOI 10.48552/zkbd-4277, hdl 10316/120011, CC-BY-4.0,
2,525 records 2000-2024 incl. live Calluna / Pterospartum and Eucalyptus litter) is a superset
in time, but its repository (estudogeral.uc.pt) rejects this pipeline's User-Agent, so it is
not fetched here (see data/catalog/sources_europe_agent.csv).
"""
import json

from common import download, raw_dir, session

SOURCE_ID = "adai_pinaster_lousa"
RECORD = 13147079

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60).json()
    (d / "zenodo_record.json").write_text(json.dumps(meta, indent=1))
    for f in meta["files"]:
        p = download(f["links"]["self"], d / f["key"], sess=s)
        print(p, p.stat().st_size)
