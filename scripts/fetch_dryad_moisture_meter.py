"""Fetch Dryad doi:10.5061/dryad.zs7h44jkw (Dong & Williams 2026): hand-held moisture meter vs
oven-dry dead fine fuel moisture, 90 samples (litter, 1-h, 10-h). License CC0-1.0.
Status 2026-11-19: file downloads blocked (401 without Dryad API token / 403 web) - see dryad.py.
"""
from dryad import fetch_dryad

SOURCE_ID = "dryad_moisture_meter"

if __name__ == "__main__":
    fetch_dryad("zs7h44jkw", SOURCE_ID)
