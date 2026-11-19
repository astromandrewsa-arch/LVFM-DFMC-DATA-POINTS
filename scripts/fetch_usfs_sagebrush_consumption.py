"""Fetch RDS-2015-0016: Fuels data for developing models for predicting consumption in sagebrush-dominated ecosystems.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2015-0016
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_sagebrush_consumption"
RDS_ID = "RDS-2015-0016"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
