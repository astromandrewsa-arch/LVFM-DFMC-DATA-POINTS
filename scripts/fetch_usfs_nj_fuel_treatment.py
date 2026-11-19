"""Fetch RDS-2017-0061: New Jersey fuel treatment effects: Pre- and post-burn biometric data.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2017-0061
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_nj_fuel_treatment"
RDS_ID = "RDS-2017-0061"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
