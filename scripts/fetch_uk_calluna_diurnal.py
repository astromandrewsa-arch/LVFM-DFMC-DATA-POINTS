"""Fetch "Calluna sampling data" - diurnal heather/moss/litter/organic-layer FMC sampled hourly
10:00-18:00 on seven days in 2022 near Blakey Ridge, North York Moors (K. Ivison, UKFDRS).
figshare 10.6084/m9.figshare.24476446.v1, CC-BY-4.0. Not part of the EIDC UKFDRS database
(checked: 0.5% of date+FMC pairs coincide, i.e. chance).
"""
import json

from common import download, raw_dir, session

SOURCE_ID = "uk_calluna_diurnal"
ARTICLE = 24476446

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get(f"https://api.figshare.com/v2/articles/{ARTICLE}", timeout=60).json()
    (d / "figshare_article.json").write_text(json.dumps(meta, indent=1))
    for f in meta["files"]:
        p = download(f["download_url"], d / f["name"], sess=s)
        print(p, p.stat().st_size)
