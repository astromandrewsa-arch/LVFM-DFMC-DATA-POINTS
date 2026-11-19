"""Fetch RDS-2021-0070: Estimating fuel moisture in grasslands using UAV-mounted infrared and visible light sensors: Field data.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2021-0070
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_mazama_grass_uav"
RDS_ID = "RDS-2021-0070"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
