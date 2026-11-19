"""Fetch Nolan, Bradstock, Resco de Dios & Boer (2025): "Dead fine fuel moisture content. 2012-2014.
South East Australia" (data of Nolan et al. 2016 Remote Sens. Environ. 174:100-108).

figshare article 28208036 (doi:10.6084/m9.figshare.28208036.v1), license CC BY 4.0.
"""

from common import download, raw_dir, session

SOURCE_ID = "nolan_dfmc_seaus"
ARTICLE = 28208036

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
