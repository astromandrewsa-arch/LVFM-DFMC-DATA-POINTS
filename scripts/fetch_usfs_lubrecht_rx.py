"""Fetch RDS-2009-0003: Lubrecht State Experimental Forest Prescribed Fire Effects Study 1973-2006.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2009-0003
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_lubrecht_rx"
RDS_ID = "RDS-2009-0003"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
