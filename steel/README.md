# Steel Data Workflow

This folder builds a combined country-level steel dataset from SteelIQ-derived inputs and UN DESA population data.

## Folder Structure

- `inputs/`: sector-specific raw source files and smaller extracts copied from SteelIQ.
- `maps/`: mapping files used by post-processing workflows.
- `outputs/`: final generated outputs.
- `data_extraction.py`: script used to combine demand, scrap, population, and per-capita rows.
- `rebase_steel_production_omnia_2019_worldsteel_indexed.py`: separate
  production variant that retains OMNIA 2019 levels and applies World Steel
  regional production indices.
- `plot_steel_production_old_vs_omnia_2019_worldsteel_indexed.py`: comparison
  plot for the original and OMNIA-2019-anchored WSA-indexed paths.
- `../shared_inputs/`: inputs shared with other sectors, including UN DESA population data.

Most generated outputs are kept as `.csv`. The workbook in `outputs/` is the final OMNIA-facing steel production projection file.

## Data Sources

- `inputs/demand-scrap-availability.xlsx` is the full SteelIQ workbook. It is large, so it is ignored by git.
- `inputs/endusedemand.xlsx` contains the SteelIQ end-use demand extract.
- `inputs/total_scrap.xlsx` contains the SteelIQ total scrap extract.
- `../shared_inputs/undesa_pop.xlsx` provides UN DESA population data.
- `inputs/worldsteel_crude_steel_production_2021_2025.xlsx` is a World Steel
  Association export retrieved on 18 August 2026 and last updated on 28 July
  2026. The workbook does not print a unit; its magnitudes and agreement with
  the published World Steel totals establish the values as kt crude steel.
- `inputs/Steel-Statistical-Yearbook-2021.pdf` is the archived World Steel
  Association *Steel Statistical Yearbook 2021*, finalized in November 2021.
  Table 1, printed pages 1-2 (PDF pages 5-6), reports crude steel production
  in thousand metric tonnes. Its SHA-256 is
  `e51e1919fbf694c8a40189c3d653e836ac9895161b6ab31ee8cd64b158998c36`.
- `inputs/worldsteel_crude_steel_production_2019_2020.csv` extracts the 94
  Table 1 country rows from that edition. Ninety-one countries have values in
  both years; Albania, Latvia, and Trinidad and Tobago are unavailable. The
  country sums differ from the published World totals by only 1 kt because of
  rounding: 1,875,329 versus 1,875,330 kt in 2019 and 1,880,446 versus
  1,880,445 kt in 2020. The CSV's SHA-256 is
  `efcb4a17eedf48546f1a2bebc751aea74741b30f31d6d84aa39398b2d7e92b0e`.
  The indexed variant deliberately uses this edition's revised 2019 column as
  its WSA denominator, keeping the 2019 and 2020 index observations in one
  source vintage.

## Processing Steps

1. Read SteelIQ end-use steel demand from `inputs/endusedemand.xlsx`.
2. Read total scrap data from `inputs/total_scrap.xlsx` and align it to the same column structure as the end-use demand data.
3. Read UN DESA population data from `../shared_inputs/undesa_pop.xlsx`, keeping country-level Medium variant values.
4. Create population rows and per-capita steel consumption rows.
5. Combine the original end-use rows, population rows, per-capita rows, and total scrap rows into one output file.
6. Extract OMNIA-region steel production and scrap projections from the `OMNIA_Data` sheet of the final workbook using `extract_omnia_region_projections.py`.

## OMNIA-2019-Anchored World Steel Index

This separate production variant uses OMNIA for each region's calibrated 2019
level and World Steel only for the 2019-2025 change. It does not overwrite the
original projection, demand, scrap, or either upstream workbook.

The regional World Steel aggregates use one fixed 87-country basket in every
year. The basket is the ISO3 intersection of the 2019-2020 Statistical
Yearbook extract and the 2021-2025 Excel export, restricted to countries with
reported 2019 and 2020 values. Source-name assignments for the earlier
vintage are recorded in `maps/worldsteel_2019_2020_country_map.csv` and
checked against the shared OMNIA map. Explicit zeroes remain zero; unavailable
values are excluded. The audit records basket membership, shared-map
coverage, estimates, zeroes, and hashes. All 28 OMNIA regions have a positive
2019 denominator and are rebased. Coverage confidence is based primarily on
the basket's share of reported regional production, rather than its raw share
of mapped country names; `AFE` is the only region below the 75% production
coverage threshold in a reference vintage.

For OMNIA region `r`, original OMNIA production `O`, fixed-basket World Steel
production `W`, and new production `N`, the calculation is:

```text
N[r, 2019] = O[r, 2019]
N[r, y] = O[r, 2019] * W[r, y] / W[r, 2019]       # 2020-2025
N[r, y] = N[r, 2025] * O[r, y] / O[r, 2025]       # 2026-2050
```

Thus 2025 is both WSA-indexed from OMNIA 2019 and the anchor for the future
projection. The original post-2025 regional growth path is preserved,
including the 2025-2026 handoff: `N[r, 2026] / N[r, 2025]` equals
`O[r, 2026] / O[r, 2025]`. The audit reports the handoff change and checks this
relationship explicitly. Regional series are not rescaled to force their sum
to equal global steel demand.

Generate the indexed projection, growth indices, and calculation audit with:

```text
python steel/rebase_steel_production_omnia_2019_worldsteel_indexed.py
```

Generate the old-versus-new comparison figure with:

```text
python steel/plot_steel_production_old_vs_omnia_2019_worldsteel_indexed.py
```

## Final Output

The `*_omnia_growth_rates.csv` files are transposed milestone-year indices:
years are rows, OMNIA regions are columns, 2019 equals 1, and the 2050 index is
held constant through 2100.

- `outputs/steel_demand_and_scrap.csv`
- `outputs/Steel_demand_and_scrap_projections [SP].xlsx`: final output used to compute steel production for OMNIA.
- `outputs/steel_production_omnia.csv`
- `outputs/steel_production_omnia_growth_rates.csv`
- `outputs/steel_scrap_omnia.csv`
- `outputs/steel_scrap_omnia_growth_rates.csv`
- `outputs/steel_production_omnia_2019_anchored_worldsteel_indexed.csv`
- `outputs/steel_production_omnia_2019_anchored_worldsteel_indexed_growth_rates.csv`
- `outputs/steel_production_omnia_2019_anchored_worldsteel_indexed_audit.csv`
- `outputs/figures/steel_production_omnia_old_vs_2019_anchored_worldsteel_indexed_2019_2050.pdf`
- `outputs/figures/steel_production_omnia_old_vs_2019_anchored_worldsteel_indexed_2019_2050.png`
