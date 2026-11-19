"""Fetch figshare article 20485665: Douglas-fir and Oregon white oak physiology and foliar moisture content, Kane et al. 2022.

License CC-BY-4.0 (figshare API). https://doi.org/10.6084/m9.figshare.20485665.v1
"""
import json

from common import download, raw_dir, session

SOURCE_ID = "figshare_kane_dfir_oak_fmc"
ARTICLE = 20485665

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    r = s.get(f"https://api.figshare.com/v2/articles/{ARTICLE}", timeout=60)
    r.raise_for_status()
    (d / "figshare_article.json").write_text(json.dumps(r.json(), indent=1))
    for f in r.json()["files"]:
        p = download(f["download_url"], d / f["name"], sess=s)
        print(p, p.stat().st_size)
