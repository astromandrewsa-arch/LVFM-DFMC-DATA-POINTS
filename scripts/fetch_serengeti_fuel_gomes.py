"""Fetch Gomes, Donaldson, Anderson, Morrison, Hopcraft & Holdo (2026) Serengeti data.

"Data and code from: Increasing rainfall reorganizes fire and herbivores in savannas",
Duke Research Data Repository, doi:10.7924/r4r567, license CC0-1.0 (DataCite rightsList),
339 MB (zip, txt). Includes field measurements of grass fuel moisture and grass biomass across the
SE / central / NW Serengeti rainfall gradient plus weather-station observations.

STATUS (2026-11-19): BLOCKED for scripted access. https://research.repository.duke.edu/record/567
answers HTTP 202 with a bot-challenge page to scripted clients (403 to other fetchers); no public
JSON/file API was found (/api/records/567 -> 404; OAI-PMH has no record for it). The challenge is
not bypassed. This script records the DataCite metadata and tries the landing page once.

To unblock: download the record's files in a browser into data/raw/serengeti_fuel_gomes/, or ask
the Duke RDR curators (datamanagement@duke.edu) for a direct file URL; then write the normalizer.
"""
from common import raw_dir, session

SOURCE_ID = "serengeti_fuel_gomes"

if __name__ == "__main__":
    d = raw_dir(SOURCE_ID)
    s = session()
    meta = s.get("https://api.datacite.org/dois/10.7924/r4r567", timeout=60)
    meta.raise_for_status()
    (d / "datacite.json").write_text(meta.text)
    r = s.get("https://research.repository.duke.edu/record/567", timeout=60)
    print("landing page HTTP", r.status_code, r.headers.get("content-type"))
    if r.status_code != 200:
        print("BLOCKED: repository bot protection; manual browser download required.")
