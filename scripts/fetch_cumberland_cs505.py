"""Fetch Resco de Dios, Boer, Bradstock & Nolan (2024): "Dead fine fuel moisture content. 2013.
Cumberland Plains Flux Tower (Richmond, NSW, Australia)" - daily minimum CS505 10-h fuel moisture
sensor plus VPD/T/RH/precip (data of Resco de Dios et al. 2015 Agric. For. Meteorol. 203:64-73).

figshare article 26014618 (doi:10.6084/m9.figshare.26014618.v1), license CC BY 4.0.
The OzFlux/TERN Cumberland Plain NetCDF releases (dap.tern.org.au THREDDS, CC BY 4.0; checked 2020,
2021_v1 and 2026_v3 L3) carry NO fuel-moisture variable, so this figshare file is the only open
CS505 series for the site.
"""

from common import download, raw_dir, session

SOURCE_ID = "cumberland_cs505"
ARTICLE = 26014618

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
