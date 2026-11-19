"""Fetch RDS-2014-0028: RxCADRE 2008, 2011, and 2012: Ground fuel measurements from prescribed fires.

USDA Forest Service Research Data Archive, https://doi.org/10.2737/RDS-2014-0028
Use constraints: US Government-funded data, usable without additional permissions or fees
(public domain; citation requested). Photo packages are skipped.
"""
from rds import fetch_rds

SOURCE_ID = "usfs_rxcadre_fuels"
RDS_ID = "RDS-2014-0028"

if __name__ == "__main__":
    fetch_rds(RDS_ID, SOURCE_ID)
