"""Fetch RDS-2026-0026: Diurnal dead fuel moisture content for selected Hawaiian fuels 1999-2001.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2026-0026
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_hawaii_dfm"
RDS_ID = "RDS-2026-0026"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
