"""Fetch RDS-2015-0005: Fuels, weather, fire behavior and vegetation data pertaining to Rx fire in a young loblolly pine plantation in Jones County, Georgia.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2015-0005
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_ga_loblolly_rx"
RDS_ID = "RDS-2015-0005"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
