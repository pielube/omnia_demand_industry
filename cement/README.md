# Cement Data Workflow

This folder builds country-level cement demand projections using the WCA regional outlook, with two allocation approaches: elasticity-based country shares and fixed within-region shares.

## Folder Structure

- `inputs/`: raw source files, including population and GDP workbooks,`cement.docx`, and the WCA white paper.
- `maps/`: derived WCA country-region mapping files.
- `outputs/`: final country-level projection CSVs and figures.
- `*.py`: scripts used to create projections, maps, and plots.

Generated projection outputs are kept as `.csv` only. The remaining `.xlsx` files are raw inputs.

## Data Sources

- Historical cement production is downloaded directly in the scripts from Zenodo:
  `https://zenodo.org/records/20397304/files/1.%20annual_cement_production.csv?download=1`
- Population data are read from `inputs/undesa_pop.xlsx`.
- GDP projections are read from `inputs/gdp_projection_country_SSP2.xlsx`.
- WCA regional cement consumption values are hard-coded in the scripts from the table extracted to `inputs/cement.docx`.

## Processing Steps

1. Build WCA projections with elasticity-based shares:
   `data_extraction_wca_regions.py`

   This combines historical country cement production, population, GDP projections, and WCA regional totals. From 2025 onward, countries are allocated regional WCA totals using dynamic shares informed by GDP per capita growth and the elasticity curve defined in the script.
2. Build WCA projections with fixed shares:
   `data_extraction_wca_fixed_shares.py`

   This uses the same WCA regional totals, but keeps each country's share within its WCA region fixed from the base year.
3. Compare the two WCA approaches:
   `plot_wca_projection_comparison.py`

   This creates a 3x3 comparison figure for the nine largest cement producers based on 2024 production.

## Final Outputs

- `outputs/cement_demand_with_population_wca_regions.csv`
- `outputs/cement_demand_with_population_wca_fixed_shares.csv`
- `outputs/figures/wca_projection_comparison_top9_3x3.png`
- `outputs/figures/wca_projection_comparison_top9_3x3.pdf`
