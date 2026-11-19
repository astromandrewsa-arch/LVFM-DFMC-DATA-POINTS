"""Fetch the UK Fire Danger Rating System (UKFDRS) sampled fuel moisture database
(Ivison et al.; Little et al. 2024 Sci Data "A national-scale sampled temperate fuel moisture
database").

Primary: NERC EIDC 10.5285/9334118f-3389-4a13-89a1-d75ec6fcc43a (Open Government Licence v3),
data package with three CSVs: UK-wide (5,851 rows), North York Moors (1,124), West Midlands
(1,089) + supporting documentation.
Also fetched for covariates only (same samples, no new FMC values):
  - figshare 10.6084/m9.figshare.26363941.v3 "UK-wide dataset" (CC-BY-4.0): identical 5,851 rows
    plus ERA5-Land / E-OBS weather columns.
  - figshare 10.6084/m9.figshare.25041644.v1 met_fmc_landscape.csv (CC-BY-4.0): NYM samples
    with 5 h mean micrometeorology.
Not fetched (duplicates): figshare 22683508 (Little 2023 among-sampler, = subset of the EIDC
West Midlands file), figshare 25043603 (Little 2024, site-date averages derived from the NYM
data), figshare 26363917/26363929 and older versions (regional subsets / earlier copies).
"""
import json
import zipfile

from common import download, raw_dir, session

SOURCE_ID = "uk_fmc_national"
EIDC = "9334118f-3389-4a13-89a1-d75ec6fcc43a"
FIGSHARE = {
    "figshare_26363941_UK_dataset.csv": "https://ndownloader.figshare.com/files/47921461",
    "figshare_25041644_met_fmc_landscape.csv": "https://ndownloader.figshare.com/files/44181425",
}

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
    for name, url in FIGSHARE.items():
        p = download(url, d / name, sess=s)
        print(p, p.stat().st_size)
