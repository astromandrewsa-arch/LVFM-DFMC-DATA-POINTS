"""Dryad helper. Dryad's v2 API lists dataset versions/files without auth, but file downloads
(/api/v2/files/<id>/download) return 401 without an API token and the web file_stream links
return 403 to scripted clients (checked 2026-11-19). If the user obtains a Dryad API token
(https://datadryad.org/api, free account) put it in DRYAD_TOKEN; nothing else is attempted.
"""
from __future__ import annotations

import json
import os

from common import download, raw_dir, session

API = "https://datadryad.org/api/v2"


def fetch_dryad(doi_suffix: str, source_id: str, skip_larger_than: int | None = None) -> None:
    d = raw_dir(source_id)
    s = session()
    tok = os.environ.get("DRYAD_TOKEN")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    ds = s.get(f"{API}/datasets/doi%3A10.5061%2Fdryad.{doi_suffix}", timeout=60)
    ds.raise_for_status()
    (d / "dryad_dataset.json").write_text(json.dumps(ds.json(), indent=1))
    ver = ds.json()["_links"]["stash:version"]["href"]
    files = s.get(f"https://datadryad.org{ver}/files", timeout=60).json()["_embedded"]["stash:files"]
    (d / "dryad_files.json").write_text(json.dumps(files, indent=1))
    for f in files:
        if skip_larger_than and f.get("size", 0) > skip_larger_than:
            print("skip (size)", f["path"], f.get("size"))
            continue
        url = "https://datadryad.org" + f["_links"]["stash:download"]["href"]
        try:
            p = download(url, d / f["path"], sess=s, retries=1)
            print(p.name, p.stat().st_size)
        except Exception as e:  # 401 without token
            print("BLOCKED", f["path"], e)
