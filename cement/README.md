# Cement Data Workflow

This folder builds country-level cement demand projections using the WCA regional outlook, with two allocation approaches: elasticity-based country shares and fixed within-region shares.

## Folder Structure

- `inputs/`: source files, including population and GDP workbooks, the WCA regional consumption CSV, and the WCA white paper.
- `maps/`: authoritative WCA country-region mapping used by both projection approaches.
- `outputs/`: final country-level projection CSVs and figures.
- `*.py`: scripts used to create projections, maps, and plots.

Generated projection outputs are kept as `.csv` only. The remaining `.xlsx` files are raw inputs.

## Data Sources

- Historical cement production is downloaded directly in the scripts from Zenodo:
  `https://zenodo.org/records/20397304/files/1.%20annual_cement_production.csv?download=1`
- Population data are read from `inputs/undesa_pop.xlsx`.
- GDP projections are read from `inputs/gdp_projection_country_SSP2.xlsx`.
- WCA country assignments are read from `maps/wca_country_region_mapping.csv`.
- Original WCA regional cement consumption values are stored in `inputs/wca_regional_cement_consumption.csv`.
- Country projections use `inputs/wca_regional_cement_consumption_rescaled.csv`, which preserves each WCA regional trajectory while matching its 2024 value to mapped historical production.

## Processing Steps

1. Rescale the WCA regional trajectories to observed 2024 regional totals:
   `rescale_wca_regional_consumption.py`

   This applies one multiplicative factor per region to all WCA table years, preserving the WCA percentage trajectory. The resulting CSV records the original 2024 value, observed 2024 value, and calibration factor.
2. Build WCA projections with elasticity-based shares:
   `data_extraction_wca_regions.py`

   This combines historical country cement production, population, GDP projections, the WCA country-region mapping, and WCA regional totals. From 2025 onward, countries are allocated regional WCA totals using dynamic shares informed by GDP per capita growth and the elasticity curve defined in the script.
3. Build WCA projections with fixed shares:
   `data_extraction_wca_fixed_shares.py`

   This uses the same country-region mapping and WCA regional totals, but keeps each country's share within its WCA region fixed from the base year. GDP projections are not used by this approach.
4. Compare the two WCA approaches:
   `plot_wca_projection_comparison.py`

   This creates a 3x3 comparison figure for the nine largest cement producers based on 2024 production.
5. Aggregate the dynamic-share projection to OMNIA regions:
   `create_omnia_region_projection.py`

   This creates regional absolute projections and percentage growth from 2019 using the OMNIA mapping shared with the aluminium workflow.
6. Plot the nine largest OMNIA cement-producing regions in 2019:
   `plot_omnia_region_projection_top9.py`

Both projection scripts validate that the mapping has unique ISO3 codes, nonblank WCA regions, recognised and fully represented region names, and complete coverage of the countries in the cement dataset. The mapping is treated as an input and is not overwritten by either script.

## Final Outputs

- `outputs/cement_demand_with_population_wca_regions.csv`
- `outputs/cement_demand_with_population_wca_fixed_shares.csv`
- `outputs/cement_omnia_region_projection_2019_2050.csv`
- `outputs/cement_omnia_region_growth_2019_2050.csv`
- `outputs/figures/cement_omnia_regions_top9_2019_3x3.pdf`
- `outputs/figures/wca_projection_comparison_top9_3x3.pdf`
