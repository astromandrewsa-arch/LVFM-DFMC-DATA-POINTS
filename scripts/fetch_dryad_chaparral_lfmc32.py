"""Fetch Dryad doi:10.5061/dryad.rjdfn2zkw (Varga & Jones 2026): 32-year species-specific LFMC for
southern California chaparral. License CC0-1.0. Only lfmc_observations.csv (field LFMC, ~0.8 MB)
and README are wanted; the 2.4 GB modelled NetCDF (sba_lfmc_1987-2019.nc) is skipped (modelled,
would be estimates). Field observations largely overlap NFMD/FEMS.
Status 2026-11-19: file downloads blocked (401 without Dryad API token / 403 web) - see dryad.py.
"""
from dryad import fetch_dryad

SOURCE_ID = "dryad_chaparral_lfmc32"

if __name__ == "__main__":
    fetch_dryad("rjdfn2zkw", SOURCE_ID, skip_larger_than=50_000_000)
