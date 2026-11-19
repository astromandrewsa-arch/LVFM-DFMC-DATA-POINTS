"""Fetch RDS-2018-0044: Camp Swift Fire Experiment 2014: Field fuel samples.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2018-0044
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_camp_swift"
RDS_ID = "RDS-2018-0044"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
