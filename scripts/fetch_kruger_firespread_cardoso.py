"""Fetch Cardoso, Archibald, Bond, Coetsee, ... Staver (2022 PNAS) Kruger fire-spread data.

"Data from: Quantifying the environmental limits to fire spread in grassy ecosystems",
Dryad doi:10.5061/dryad.ncjsxksxm, license CC0-1.0. Files: Cardoso.etal_PNAS_fire_data.csv,
Cardoso.etal_PNAS_vca.plots_data.csv, Cardoso.etal_PNAS_finescale.wind_data.csv, README.rtf.

STATUS (2026-11-19): BLOCKED for scripted access. The Dryad API v2 lists the files, but every
file download (/api/v2/files/<id>/download and /api/v2/datasets/<doi>/download) returns
401 "must have current bearer token". The Wits figshare record 10.71796/wits-figshare.31644787
is a metadata-only mirror (0-byte link back to Dryad). No login is bypassed here.

To unblock: create a free Dryad API account (https://datadryad.org/api) and export
DRYAD_TOKEN=<bearer token>, or download the dataset zip in a browser and unzip it into
data/raw/kruger_firespread_cardoso/. Then write normalize_kruger_firespread_cardoso.py after
inspecting README.rtf (fuel moisture column/basis not yet verified) and check overlap with
kruger_ebp_topkill (both derive from SANParks Kruger fire records).
"""
import os
import sys

from common import download, raw_dir, session

SOURCE_ID = "kruger_firespread_cardoso"
API = "https://datadryad.org"
DOI = "doi%3A10.5061%2Fdryad.ncjsxksxm"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    ds = s.get(f"{API}/api/v2/datasets/{DOI}", timeout=60)
    ds.raise_for_status()
    (d / "dryad_dataset.json").write_text(ds.text)
    ver = ds.json()["_links"]["stash:version"]["href"]
    files = s.get(f"{API}{ver}/files", timeout=60)
    files.raise_for_status()
    (d / "dryad_files.json").write_text(files.text)
    token = os.environ.get("DRYAD_TOKEN")
    if not token:
        print("BLOCKED: Dryad file downloads need a bearer token (set DRYAD_TOKEN); file list saved.")
        sys.exit(0)
    s.headers["Authorization"] = f"Bearer {token}"
    for f in files.json()["_embedded"]["stash:files"]:
        p = download(API + f["_links"]["stash:download"]["href"], d / f["path"], sess=s)
        print(p, p.stat().st_size)
