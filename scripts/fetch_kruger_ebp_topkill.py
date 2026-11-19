"""Fetch Ongole, Midzi, Govender, Smit, Kruger & Higgins (2026) Kruger plot/landscape fire data.

"Data from: Calibrating a fire intensity model to predict topkill risk for trees in an African
savanna". Zenodo record 23915836 (concept DOI 10.5281/zenodo.23915835). License CC-BY-4.0.

Only data.zip (92 KB), scripts.zip (15 KB, used to document the fuel-moisture basis) and the
README are fetched; output.zip (2.6 GB of JAGS output) and figures.zip are skipped.
"""
import zipfile

from common import download, raw_dir, session

SOURCE_ID = "kruger_ebp_topkill"
RECORD = "23915836"
FILES = ["data.zip", "scripts.zip", "READMe.md"]

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60)
    meta.raise_for_status()
    (d / "zenodo_record.json").write_text(meta.text)
    for name in FILES:
        p = download(f"https://zenodo.org/api/records/{RECORD}/files/{name}/content", d / name, sess=s)
        print(p, p.stat().st_size)
        if name.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                z.extractall(d / name.removesuffix(".zip"))
