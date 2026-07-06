# Aluminium Data Workflow

This folder builds country-level aluminium projections from Zijie's 10-region baseline scenario and the OMNIA country-region mapping.

## Folder Structure

- `inputs/`: raw source files, including Zijie's scenario workbook, the OMNIA INF workbook, and the Bertram region definition document.
- `maps/`: derived mapping files used for allocation.
- `outputs/`: final country-level projection CSVs and figures.
- `*.py`: scripts used to create maps, projections, and plots.

Generated projection outputs are kept as `.csv` only. The remaining `.xlsx` files are raw inputs.

## Processing Steps

1. Add Zijie regions to the OMNIA country mapping:
   `add_zijie_regions_to_omnia_mapping.py`

   This reads `maps/OMNIA_region_mapping_241120.csv` and assigns each country to
   one of Zijie's aluminium regions, based on the Bertram/IAI Alucycle regional
   definitions, with the UK separated from Europe.
2. Build producer-share maps:
   `create_primary_producer_zijie_map.py`
   `create_secondary_producer_zijie_map.py`

   These scripts extract 2019 country-level primary and secondary production values from the `INF_Data` sheet in `inputs/VT_OMNIA_IIS_INM_INF_v0.4.xlsx`.
   The resulting country values are matched to OMNIA countries and Zijie regions, then saved in `maps/`.
3. Build country-level projections:
   `create_primary_country_projection_from_zijie.py`
   `create_secondary_country_projection_from_zijie.py`
   `create_scrap_country_projection_from_zijie.py`

   These scripts read Zijie's regional baseline projections from
   `inputs/10 regions Al data.xlsx` and allocate them to all OMNIA countries.
   Countries with no allocation share receive zero.
4. Plot selected results:
   `plot_primary_country_projection_top9.py`
   `plot_secondary_country_projection_top9.py`
   `plot_scrap_country_projection_top9.py`
   `plot_zijie_primary_regions_top9.py`

   Figures are saved in `outputs/figures/`.

## Main Assumptions

- Primary production is allocated using 2019 primary producer shares from the INF workbook.
- Secondary production is allocated using 2019 secondary producer shares from the INF workbook.
- Scrap is allocated using the same shares as secondary production.
- For Zijie regions without explicit secondary producer shares, primary producer shares are used as a proxy.
- Zijie's projections start in 2024. Values for 2020-2023 are linearly interpolated between 2019 and 2024.
- For the 2019 scrap baseline, regional totals are back-extrapolated from Zijie's 2024-2030 regional trend and then allocated using secondary shares.
- Country-level totals are checked against Zijie's regional totals for all projected years.

## Final Outputs

- `outputs/aluminium_primary_country_projection_2019_2050.csv`
- `outputs/aluminium_secondary_country_projection_2019_2050.csv`
- `outputs/aluminium_scrap_country_projection_2019_2050.csv`
