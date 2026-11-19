"""Fetch RDS-2016-0023: Physical and chemical properties of the foliage of 10 live wildland fuels (JFSP 11-1-4-19).

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2016-0023
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_live_foliage_props"
RDS_ID = "RDS-2016-0023"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
