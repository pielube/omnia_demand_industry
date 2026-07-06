# Steel Data Workflow

This folder builds a combined country-level steel dataset from SteelIQ-derived inputs and UN DESA population data.

## Folder Structure

- `inputs/`: raw source files and smaller extracts copied from SteelIQ.
- `maps/`: reserved for derived mapping files if needed later.
- `outputs/`: final generated outputs.
- `data_extraction.py`: script used to combine demand, scrap, population, and per-capita rows.

Most generated outputs are kept as `.csv`. The workbook in `outputs/` is the final OMNIA-facing steel production projection file.

## Data Sources

- `inputs/demand-scrap-availability.xlsx` is the full SteelIQ workbook. It is large, so it is ignored by git.
- `inputs/endusedemand.xlsx` contains the SteelIQ end-use demand extract.
- `inputs/total_scrap.xlsx` contains the SteelIQ total scrap extract.
- `inputs/undesa_pop.xlsx` provides UN DESA population data.

## Processing Steps

1. Read SteelIQ end-use steel demand from `inputs/endusedemand.xlsx`.
2. Read total scrap data from `inputs/total_scrap.xlsx` and align it to the same column structure as the end-use demand data.
3. Read UN DESA population data from `inputs/undesa_pop.xlsx`, keeping country-level Medium variant values.
4. Create population rows and per-capita steel consumption rows.
5. Combine the original end-use rows, population rows, per-capita rows, and total scrap rows into one output file.

## Final Output

- `outputs/steel_demand_and_scrap.csv`
- `outputs/Steel_demand_and_scrap_projections [SP].xlsx`: final output used to compute steel production for OMNIA.
