**Rows:** 14,143,310 total; 13,717,078 pass QA (no hard flag, not a duplicate).

**By source and fuel class (QA-clean rows):**

| source_id                  | fuel_class   |        n |
|:---------------------------|:-------------|---------:|
| madis_raws                 | dead         | 12976301 |
| fems_nfmd                  | live         |   286837 |
| cfs_testfire_fmc           | dead         |   133813 |
| onf_reseau_hydrique        | live         |   103287 |
| fems_nfmd                  | dead         |    95519 |
| globe_lfmc2                | live         |    38231 |
| saxony_fmc_sticks          | dead         |    31308 |
| usfs_hawaii_dfm            | dead         |    12432 |
| spif_catalonia             | live         |     9541 |
| uk_fmc_national            | dead         |     4883 |
| bc_fire_skips              | dead         |     4083 |
| uk_fmc_national            | live         |     3139 |
| usfs_sgp_pyric_herbivory   | live         |     3138 |
| nolan_dfmc_seaus           | dead         |     3129 |
| bc_fire_skips              | live         |     2227 |
| cfs_testfire_fmc           | live         |     1280 |
| adai_pinaster_lousa        | dead         |     1018 |
| wfsi_dod_fmc               | dead         |      946 |
| uk_calluna_citizen_2023    | live         |      816 |
| uk_cone_calorimetry        | dead         |      674 |
| figshare_kane_dfir_oak_fmc | dead         |      502 |
| figshare_kane_dfir_oak_fmc | live         |      443 |
| cumberland_cs505           | dead         |      363 |
| usfs_fasmee_monroe         | dead         |      362 |
| hobart_ibutton_fmi         | dead         |      355 |
| uk_cone_calorimetry        | live         |      343 |
| uk_calluna_diurnal         | dead         |      317 |
| usfs_mazama_grass_uav      | dead         |      238 |
| uk_calluna_diurnal         | live         |      237 |
| wfsi_dod_fmc               | live         |      218 |
| saxony_fmc_sticks          | live         |      129 |
| usfs_live_foliage_props    | live         |      127 |
| usfs_flatwoods_consumption | live         |      116 |
| usfs_flatwoods_consumption | dead         |      113 |
| usfs_sagebrush_consumption | dead         |       94 |
| usfs_lubrecht_rx           | dead         |       80 |
| usfs_nj_fuel_treatment     | dead         |       66 |
| usfs_ga_loblolly_rx        | dead         |       59 |
| usfs_sagebrush_consumption | live         |       58 |
| usfs_mazama_grass_uav      | live         |       56 |
| figshare_kane_canopy_fmc   | live         |       54 |
| usfs_camp_swift            | dead         |       52 |
| usfs_fasmee_monroe         | live         |       40 |
| usfs_hawaii_dfm            | live         |       22 |
| usfs_lubrecht_rx           | live         |       20 |
| usfs_camp_swift            | live         |        6 |
| annaburroo_fds_1986        | dead         |        3 |
| usfs_ga_loblolly_rx        | live         |        3 |

**By country (QA-clean):**

| country        |     dead |   live |    total |
|:---------------|---------:|-------:|---------:|
| USA            | 13084053 | 304300 | 13388353 |
| Canada         |   137896 |   3507 |   141403 |
| France         |        0 | 107856 |   107856 |
| Germany        |    31308 |    129 |    31437 |
| Spain          |        0 |  18818 |    18818 |
| United Kingdom |     5874 |   4535 |    10409 |
| Australia      |     3850 |   3355 |     7205 |
| unknown        |     2711 |      0 |     2711 |
| Italy          |        0 |   2630 |     2630 |
| Israel         |        0 |   2215 |     2215 |
| Portugal       |     1018 |     53 |     1071 |
| South Africa   |        0 |    950 |      950 |
| Türkiye        |        0 |    689 |      689 |
| Tunisia        |        0 |    449 |      449 |
| China          |        0 |    264 |      264 |
| Scotland       |        0 |    255 |      255 |
| Argentina      |        0 |    241 |      241 |
| Senegal        |        0 |     96 |       96 |
| England        |        0 |     26 |       26 |

**By decade (QA-clean):**

|   decade |     dead |   live |
|---------:|---------:|-------:|
|     1930 |     8832 |      5 |
|     1940 |    31374 |    346 |
|     1950 |    90074 |    929 |
|     1960 |     3533 |      0 |
|     1970 |       80 |     82 |
|     1980 |      135 |   1887 |
|     1990 |     1599 |  31369 |
|     2000 |    56150 | 121532 |
|     2010 |  2532201 | 179937 |
|     2020 | 10542732 | 114281 |

**Rows with at least one weather covariate set:** 14,140,857 of 14,143,310 (100.0%)

**Weather covariate coverage (rows):**

| source                     |     rows |   has_power |   has_gridmet |   has_source_weather |   has_nearest_station |   has_any_weather |
|:---------------------------|---------:|------------:|--------------:|---------------------:|----------------------:|------------------:|
| adai_pinaster_lousa        |     1018 |        1018 |             0 |                    0 |                   485 |              1018 |
| annaburroo_fds_1986        |        3 |           3 |             0 |                    0 |                     0 |                 3 |
| bc_fire_skips              |     6317 |        6317 |             0 |                    0 |                  2150 |              6317 |
| cfs_testfire_fmc           |   136246 |           0 |             0 |               132624 |                 90524 |            135578 |
| chaco_curing_coria         |      105 |         105 |             0 |                    0 |                    25 |               105 |
| cumberland_cs505           |      363 |         363 |             0 |                    0 |                   299 |               363 |
| fems_nfmd                  |   382778 |      382679 |        378193 |                    0 |                357548 |            382737 |
| figshare_kane_canopy_fmc   |       54 |          54 |            54 |                    0 |                    54 |                54 |
| figshare_kane_dfir_oak_fmc |      946 |         946 |           946 |                    0 |                   946 |               946 |
| globe_lfmc2                |   293796 |      293734 |        238945 |               293755 |                267927 |            293755 |
| hobart_ibutton_fmi         |      355 |         355 |             0 |                    0 |                     0 |               355 |
| kruger_ebp_topkill         |     1589 |           0 |             0 |                    0 |                     0 |                 0 |
| madis_raws                 | 13143594 |    13101948 |      12670463 |             13097007 |                     0 |          13143594 |
| nolan_dfmc_seaus           |     3148 |        3148 |             0 |                    0 |                  1981 |              3148 |
| onf_reseau_hydrique        |   103293 |      103293 |             0 |                    0 |                 99779 |            103293 |
| saxony_fmc_sticks          |    31437 |       31437 |             0 |                    0 |                 31437 |             31437 |
| spif_catalonia             |     9541 |        9541 |             0 |                    0 |                  6794 |              9541 |
| uk_calluna_citizen_2023    |      830 |         816 |             0 |                    0 |                   731 |               816 |
| uk_calluna_diurnal         |      554 |         554 |             0 |                    0 |                   554 |               554 |
| uk_cone_calorimetry        |     1020 |        1020 |             0 |                    0 |                   860 |              1020 |
| uk_fmc_national            |     8064 |        8064 |             0 |                 5845 |                  6654 |              8064 |
| usfs_camp_swift            |       58 |          58 |            58 |                    0 |                    58 |                58 |
| usfs_fasmee_monroe         |      404 |         404 |           404 |                    0 |                   404 |               404 |
| usfs_flatwoods_consumption |      229 |         229 |            32 |                  229 |                   176 |               229 |
| usfs_ga_loblolly_rx        |       64 |          64 |             0 |                    0 |                     0 |                64 |
| usfs_hawaii_dfm            |    12454 |       12454 |             0 |                12450 |                 12312 |             12454 |
| usfs_live_foliage_props    |      127 |         127 |            38 |                    0 |                    89 |               127 |
| usfs_lubrecht_rx           |      100 |           0 |             0 |                    0 |                     0 |                 0 |
| usfs_mazama_grass_uav      |      294 |         294 |           294 |                    0 |                   294 |               294 |
| usfs_nj_fuel_treatment     |       66 |          66 |            66 |                    0 |                    66 |                66 |
| usfs_sagebrush_consumption |      152 |         152 |             0 |                  152 |                   116 |               152 |
| usfs_sgp_pyric_herbivory   |     3146 |        3146 |          3146 |                    0 |                  3146 |              3146 |
| wfsi_dod_fmc               |     1165 |        1165 |          1165 |                    0 |                  1165 |              1165 |

**Licensing (sources with ingested rows):**

| source_id                        | license                                                                                                                                                                                |   records |
|:---------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------:|
| globe_lfmc2                      | CC0-1.0                                                                                                                                                                                |    293796 |
| fems_nfmd                        | US Government work, public domain (no restrictions stated)                                                                                                                             |    382778 |
| madis_raws                       | MADIS public (unrestricted) tier; RAWS is US Government public domain. MesoWest-provided rows: provider terms unclear -> flagged in notes (provider=MesoWest)                          |  13143594 |
| kruger_ebp_topkill               | CC-BY-4.0                                                                                                                                                                              |      1589 |
| annaburroo_fds_1986              | CC0-1.0                                                                                                                                                                                |         3 |
| nolan_dfmc_seaus                 | CC-BY-4.0                                                                                                                                                                              |      3148 |
| hobart_ibutton_fmi               | CC-BY-4.0                                                                                                                                                                              |       355 |
| cumberland_cs505                 | CC-BY-4.0                                                                                                                                                                              |       363 |
| chaco_curing_coria               | CC-BY-4.0                                                                                                                                                                              |       105 |
| onf_reseau_hydrique              | CC-BY-4.0                                                                                                                                                                              |    103293 |
| spif_catalonia                   | MPL-2.0 (repository LICENSE.md; package DESCRIPTION says GPL (>= 2); Zenodo metadata license "other-open")                                                                             |      9541 |
| uk_fmc_national                  | OGL-UK-3.0 (EIDC); figshare copy 10.6084/m9.figshare.26363941.v3 is CC-BY-4.0                                                                                                          |      8064 |
| uk_calluna_diurnal               | CC-BY-4.0                                                                                                                                                                              |       554 |
| uk_calluna_citizen_2023          | OGL-UK-3.0                                                                                                                                                                             |       830 |
| uk_cone_calorimetry              | OGL-UK-3.0                                                                                                                                                                             |      1020 |
| adai_pinaster_lousa              | CC-BY-4.0                                                                                                                                                                              |      1018 |
| saxony_fmc_sticks                | CC-BY-4.0                                                                                                                                                                              |     31437 |
| bc_fire_skips                    | CC-BY-4.0                                                                                                                                                                              |      6317 |
| usfs_hawaii_dfm                  | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |     12454 |
| usfs_sgp_pyric_herbivory         | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |      3146 |
| usfs_mazama_grass_uav            | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |       294 |
| usfs_camp_swift                  | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |        58 |
| usfs_fasmee_monroe               | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |       404 |
| usfs_sagebrush_consumption       | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |       152 |
| usfs_flatwoods_consumption       | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |       229 |
| usfs_lubrecht_rx                 | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |       100 |
| usfs_live_foliage_props          | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |       127 |
| usfs_nj_fuel_treatment           | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |        66 |
| usfs_ga_loblolly_rx              | US Government work - public domain (RDS use constraint: 'collected using funding from the U.S. Government and can be used without additional permissions or fees'; citation requested) |        64 |
| figshare_kane_canopy_fmc         | CC-BY-4.0                                                                                                                                                                              |        54 |
| figshare_kane_dfir_oak_fmc       | CC-BY-4.0                                                                                                                                                                              |       946 |
| wfsi_dod_fmc                     | CC-BY-4.0 (EML intellectualRights of each dataset)                                                                                                                                     |      1165 |
| cfs_testfire_fmc                 | Open Government Licence - Canada (ca-ogl-lgo)                                                                                                                                          |    136246 |
| github_schwilk_species_comp_flam | none (no license file)                                                                                                                                                                 |       254 |
