"""Fetch Williamson (2025): summarised fuel moisture data for Bowman, Furlaud, Porter & Williamson
(2022) Fire 5:130, Hobart (Tasmania) wet/dry Eucalyptus forests, Nov 2021 - Mar 2022.

figshare article 20305317 (doi:10.6084/m9.figshare.20305317.v1), license CC BY 4.0.
Site locations are not given (paper Fig. 1 map only).
"""

from common import download, raw_dir, session

SOURCE_ID = "hobart_ibutton_fmi"
ARTICLE = 20305317

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    r = s.get(f"https://api.figshare.com/v2/articles/{ARTICLE}", timeout=60)
    r.raise_for_status()
    (d / "figshare_article.json").write_text(r.text)
    meta = r.json()
    print(meta["title"], "|", meta["license"]["name"])
    for f in meta["files"]:
        p = download(f["download_url"], d / f["name"], sess=s)
        print(p, p.stat().st_size)
