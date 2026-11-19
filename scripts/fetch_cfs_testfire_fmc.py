"""Fetch Canadian Forest Service historic 'Test fire, fuel moisture and weather observations'
(11 field stations across Canada, 1931-1961), released by Library and Archives Canada as open
data under the Open Government Licence - Canada (ca-ogl-lgo; CKAN records on open.canada.ca /
data.amerigeoss.org harvest, e.g. 7721f3b0-6ce6-4615-92a8-16022326acb3).
Files: G0000391 fuel moisture data, G0000390 noon weather, G0000388 basic weather,
G0000389 revised weather, G0000392 test fire data; each with an OCR'd PDF codebook.
"""
import time

from common import download, raw_dir, session

SOURCE_ID = "cfs_testfire_fmc"
BASE = "http://data2.collectionscanada.ca/open-data_donnees-ouvertes/"
IDS = ["G0000391", "G0000390", "G0000388", "G0000389", "G0000392"]

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    for i in IDS:
        for name in (f"{i}.txt", f"{i}_Codebook-OCR.pdf"):
            p = download(BASE + name, d / name, sess=s)
            print(p.name, p.stat().st_size)
            time.sleep(1)
