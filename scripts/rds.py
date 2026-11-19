"""Helpers for USDA Forest Service Research Data Archive (RDS) sources.

Each RDS data publication has a public catalog page
https://www.fs.usda.gov/rds/archive/catalog/<RDS-ID> linking to its metadata HTML, file index and
one or more zip packages under /rds/archive/products/<RDS-ID>/. No login is required. RDS use
constraints (stated in each metadata record): "These data were collected using funding from the
U.S. Government and can be used without additional permissions or fees" (US Government work /
public domain; citation requested).
"""
from __future__ import annotations

import re
import time
import zipfile
from pathlib import Path

from common import download, raw_dir, session

BASE = "https://www.fs.usda.gov"
# A browser-like UA is not needed; the archive serves the pipeline UA fine.


def product_links(rds_id: str, sess=None) -> list[str]:
    sess = sess or session()
    r = sess.get(f"{BASE}/rds/archive/catalog/{rds_id}", timeout=60)
    r.raise_for_status()
    links = re.findall(r'href="(/rds/archive/products/%s/[^"]+)"' % re.escape(rds_id), r.text)
    return list(dict.fromkeys(BASE + l for l in links))


def fetch_rds(rds_id: str, source_id: str, *, skip=("Photos",), extract: bool = True) -> Path:
    """Download metadata, file index and data zips (skipping photo packages) into raw/<source_id>/."""
    d = raw_dir(source_id)
    s = session()
    for url in product_links(rds_id, s):
        name = url.rsplit("/", 1)[1]
        if any(k in name for k in skip):
            print("skip", name)
            continue
        p = download(url, d / name, sess=s)
        print(p.name, p.stat().st_size)
        if extract and p.suffix == ".zip":
            out = d / p.stem
            if not out.exists():
                with zipfile.ZipFile(p) as z:
                    z.extractall(out)
        time.sleep(1)
    return d


def find(d: Path, pattern: str) -> Path:
    hits = sorted(d.rglob(pattern))
    if not hits:
        raise FileNotFoundError(f"{pattern} under {d}")
    return hits[0]
