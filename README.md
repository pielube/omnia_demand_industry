# OMNIA Industry Demand Data

This repository contains sector-specific scripts and data outputs for preparing
country-level industrial demand, production, and scrap datasets for OMNIA.

## Structure

- `cement/`: cement demand projections based on WCA regional outlooks.
- `aluminium/`: aluminium primary production, secondary production, and scrap
  projections based on Zijie's regional data.
- `steel/`: steel demand, scrap, population, and per-capita dataset built from
  SteelIQ-derived inputs.

Each sector folder follows the same basic layout:

- `inputs/`: raw source files.
- `maps/`: derived mapping or allocation files.
- `outputs/`: generated CSV outputs and figures.
- `README.md`: brief sector-specific workflow notes.

Generated outputs are generally stored as `.csv`; source Excel workbooks are
kept only where needed as raw inputs.

