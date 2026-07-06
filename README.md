# OMNIA Industry Production/Demand data for Aluminium, Cement and Steel sectors

This repository contains sector-specific scripts and data outputs for preparing
country-level industrial demand, production, and scrap datasets for OMNIA.

## Structure

- `cement/`: cement demand projections based on WCA regional outlooks. Demand = production, no trade considered.
- `aluminium/`: aluminium primary production, secondary production, and scrap projections based on Zijie's regional data and assumptions used in OMNIA for further disaggregation.
- `steel/`: steel demand, scrap, and per-capita demand dataset built from SteelIQ-derived inputs, as well as steel production based on assumptions used in OMNIA.

Each sector folder follows the same basic layout:

- `inputs/`: raw source files.
- `maps/`: derived mapping or allocation files.
- `outputs/`: generated CSV outputs and figures.
- `README.md`: brief sector-specific workflow notes.

Generated outputs are generally stored as `.csv`; source Excel workbooks are kept only where needed as raw inputs.
