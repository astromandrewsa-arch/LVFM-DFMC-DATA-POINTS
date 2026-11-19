"""Fetch USDA FS RDS-2024-0052: August 1986 Annaburroo Station prescribed fires F19 and C064,
Fire Dynamics Simulator evaluation data (CSIRO tropical grassland fires, NT Australia).

https://doi.org/10.2737/RDS-2024-0052 (also Ag Data Commons figshare 27010798). License CC0-1.0
(USDA Forest Service Research Data Archive). The zip (3 MB) holds Data/*.csv plus aerial photos.

Note: the full 1986 Annaburroo dataset (Gould, Cruz & Sullivan 2024 IJWF 33:WF23100, ~170 burn
blocks) is published under CC BY-NC-ND 4.0 and is therefore NOT fetched (non-commercial).
"""
import zipfile

from common import download, raw_dir

SOURCE_ID = "annaburroo_fds_1986"
URL = "https://www.fs.usda.gov/rds/archive/products/RDS-2024-0052/RDS-2024-0052.zip"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    p = download(URL, d / "RDS-2024-0052.zip")
    print(p, p.stat().st_size)
    with zipfile.ZipFile(p) as z:
        z.extractall(d / "RDS-2024-0052")
