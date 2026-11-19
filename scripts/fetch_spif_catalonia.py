"""Fetch the SPIF (Servei de Prevencio d'Incendis Forestals, Generalitat de Catalunya) LFMC
database, as packaged in the spif-ctfc/LFMC R package (lfmc.sqlite), release v.1.0.0.

Zenodo 10.5281/zenodo.4694854 (v.1.0.0, 2021-04-15). Chosen over 10.5281/zenodo.4675335
(v.0.1.3, 2021-04-09): same 10,022 samples and identical masses/LFMC, but v.1.0.0 adds the
ManualOutlier/AdditiveOutlier flags described in Gabriel et al. 2021 (Ann For Sci 78:44).
License: Zenodo metadata "other-open"; repository LICENSE.md is MPL-2.0 (package DESCRIPTION
says GPL>=2). Both allow commercial use; attribution/notice retention applies.
"""
import json
import zipfile

from common import download, raw_dir, session

SOURCE_ID = "spif_catalonia"
RECORD = 4694854

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60).json()
    (d / "zenodo_record.json").write_text(json.dumps(meta, indent=1))
    for f in meta["files"]:
        p = download(f["links"]["self"], d / f["key"].replace("/", "_"), sess=s)
        print(p, p.stat().st_size)
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith(("data/lfmc.sqlite", "LICENSE.md", "DESCRIPTION", "README.md")):
                    (d / n.split("/")[-1]).write_bytes(z.read(n))
                    print("  extracted", n)
