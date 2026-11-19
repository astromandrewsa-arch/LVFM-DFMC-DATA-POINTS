"""Fetch RDS-2024-0049: Field plot measurements from the 2017-2020 FASMEE Rx fires.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2024-0049
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_fasmee_monroe"
RDS_ID = "RDS-2024-0049"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
