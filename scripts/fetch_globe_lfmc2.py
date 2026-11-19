"""Fetch Globe-LFMC 2.0 (Yebra et al. 2024, Scientific Data). License CC0.

Figshare: https://doi.org/10.6084/m9.figshare.25413790
"""
from common import download, raw_dir

SOURCE_ID = "globe_lfmc2"
FILES = {
    "Globe-LFMC-2.0_final.xlsx": "https://ndownloader.figshare.com/files/45049786",
    "S3_references_and_supplementary_information.xlsx": "https://ndownloader.figshare.com/files/43631865",
    "S1_dates_corrected.xlsx": "https://ndownloader.figshare.com/files/43631859",
}

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    for name, url in FILES.items():
        p = download(url, d / name)
        print(p, p.stat().st_size)
