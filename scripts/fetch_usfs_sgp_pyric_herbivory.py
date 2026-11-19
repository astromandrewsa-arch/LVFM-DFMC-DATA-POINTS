"""Fetch RDS-2023-0025: Vegetation and fuels characteristics of four sites in the southern Great Plains: Pyric herbivory study.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2023-0025
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_sgp_pyric_herbivory"
RDS_ID = "RDS-2023-0025"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
