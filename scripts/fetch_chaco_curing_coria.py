"""Fetch Coria (2026) supplement to "Evaluating the accuracy of two simple field methods for estimating
grassland curing state in the Dry Chaco Region of Argentina" (Arid Land Res. Manage.,
doi:10.1080/15324982.2025.2611270), Taylor & Francis figshare; DOCX Appendix 1 = field data.

figshare article 31017410 (doi:10.6084/m9.figshare.31017410.v1), license CC BY 4.0.
"""

from common import download, raw_dir, session

SOURCE_ID = "chaco_curing_coria"
ARTICLE = 31017410

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
