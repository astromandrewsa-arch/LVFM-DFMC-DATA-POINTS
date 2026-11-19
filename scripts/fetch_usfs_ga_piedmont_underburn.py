"""Fetch RDS-2016-0028: Long-term site responses to season and interval of underburns on the Georgia Piedmont.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2016-0028
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_ga_piedmont_underburn"
RDS_ID = "RDS-2016-0028"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
