# OMNIA Industry Production/Demand data for Aluminium, Cement and Steel sectors

This repository contains sector-specific scripts and data outputs for preparing
country-level industrial demand, production, and scrap datasets for OMNIA.

## Structure

- `cement/`: cement demand projections based on WCA regional outlooks. Demand = production, no trade considered.
- `aluminium/`: aluminium primary production, secondary production, and scrap projections based on Zijie's regional data and assumptions used in OMNIA for further disaggregation.
- `steel/`: steel demand, scrap, and per-capita demand dataset built from SteelIQ-derived inputs, as well as steel production based on assumptions used in OMNIA.
- `shared_inputs/`: central source and reference inputs used by sector workflows.

Each sector folder follows the same basic layout:

- `inputs/`: raw source files.
- `maps/`: mapping or allocation files used by the sector workflows.
- `outputs/`: generated final datasets.
- `README.md`: brief sector-specific workflow notes.

The shared inputs currently comprise the UN DESA population and SSP2 GDP
workbooks, the OMNIA country-region mapping, and the OMNIA INF workbook.

Generated outputs are generally stored as `.csv`; steel also retains its final
OMNIA-facing workbook.
