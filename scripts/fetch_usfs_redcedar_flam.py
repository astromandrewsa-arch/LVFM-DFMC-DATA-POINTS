"""Fetch RDS-2018-0012: Flammability thresholds of Eastern redcedar as a potential indicator for heightened wildfire danger.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2018-0012
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_redcedar_flam"
RDS_ID = "RDS-2018-0012"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
