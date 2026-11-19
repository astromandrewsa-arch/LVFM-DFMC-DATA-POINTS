"""Fetch RDS-2015-0019: Data for developing fuel consumption models for pine flatwoods fuel types in the southeastern United States.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2015-0019
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_flatwoods_consumption"
RDS_ID = "RDS-2015-0019"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
