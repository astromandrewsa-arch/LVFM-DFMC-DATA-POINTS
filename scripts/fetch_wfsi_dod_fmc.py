"""Fetch DoD Wildland Fire Science Initiative (WFSI) burn-campaign fuel moisture datasets.

WFSI Data Portal (MetacatUI over a DataONE member node). Public objects are served by the DataONE
MN REST API: https://portal.wfsi-data.org/catalog/d1/mn/v2/object/<pid>. For each dataset the EML
metadata is fetched, and every <otherEntity id=...> is downloaded under its entityName.
License per EML intellectualRights: CC-BY-4.0.
"""
import re
import time

from common import download, raw_dir, session

SOURCE_ID = "wfsi_dod_fmc"
BASE = "https://portal.wfsi-data.org/catalog/d1/mn/v2/object/"
DOIS = {
    "W4688D": "Fort Stewart 2022 Prescribed Burn Campaign: Fuel Moisture Data",
    "W41S34": "FMC Winter Burn Plots, Osceola NF, Feb 2022",
    "W4V30J": "FMC 2023 DoD WFSI Eglin AFB Campaign",
    "W4QC7Q": "FMC 2024 DoD WFSI Fort Stewart Campaign",
    "W4JP44": "FMC 2025 DoD WFSI Fort Stewart Campaign",
}

if __name__ == "__main__":
    root = raw_dir(SOURCE_ID)
    s = session()
    for suffix in DOIS:
        d = root / suffix
        d.mkdir(exist_ok=True)
        eml = download(BASE + f"doi:10.60594/{suffix}", d / "eml.xml", sess=s)
        t = eml.read_text(encoding="utf-8", errors="replace")
        for pid, body in re.findall(r'<otherEntity[^>]*id="([^"]+)"[^>]*>(.*?)</otherEntity>', t, re.S):
            name = re.search(r"<entityName>(.*?)</entityName>", body, re.S).group(1).strip()
            name = re.sub(r"[^\w.\-]+", "_", name)
            p = download(BASE + pid, d / name, sess=s)
            print(suffix, p.name, p.stat().st_size)
            time.sleep(0.5)
