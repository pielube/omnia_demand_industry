# Steel Data Workflow

This folder builds a combined country-level steel dataset from SteelIQ-derived inputs and UN DESA population data.

## Folder Structure

- `inputs/`: sector-specific raw source files and smaller extracts copied from SteelIQ.
- `maps/`: mapping files used by post-processing workflows.
- `outputs/`: final generated outputs.
- `data_extraction.py`: script used to combine demand, scrap, population, and per-capita rows.
- `rebase_steel_production_worldsteel_2021_2025.py`: higher-precision rebase
  using the World Steel 2021-2025 Excel export.
- `plot_steel_production_old_vs_worldsteel_2021_2025.py`: comparison plot for
  the original and Excel-rebased production paths.
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

## Processing Steps

1. Read SteelIQ end-use steel demand from `inputs/endusedemand.xlsx`.
2. Read total scrap data from `inputs/total_scrap.xlsx` and align it to the same column structure as the end-use demand data.
3. Read UN DESA population data from `../shared_inputs/undesa_pop.xlsx`, keeping country-level Medium variant values.
4. Create population rows and per-capita steel consumption rows.
5. Combine the original end-use rows, population rows, per-capita rows, and total scrap rows into one output file.
6. Extract OMNIA-region steel production and scrap projections from the `OMNIA_Data` sheet of the final workbook using `extract_omnia_region_projections.py`.

## World Steel 2021-2025 Excel Rebase

The Excel export supports a higher-precision historical variant built directly
from the original OMNIA projection:

```text
python steel/rebase_steel_production_worldsteel_2021_2025.py
```

The source-name-to-ISO3 assignments are recorded in
`maps/worldsteel_2021_2025_country_map.csv` and checked against the shared
OMNIA mapping. Fifteen regions have complete country coverage: `AFN`, `ANZ`,
`BRA`, `CAN`, `CHL`, `EUE`, `IDN`, `IND`, `JPN`, `MEA`, `MEX`, `NIG`, `RUS`,
`SKT`, and `USA`. `CHN` is included as the documented China Mainland
exception; the source's Hong Kong row is explicitly zero.

For each eligible region, 2019 retains its original value. The 2020 value is
the linear midpoint between original 2019 and observed 2021. Values for
2021-2025 are the exact sums of the World Steel country observations. From
2026 onward, the original projection path is rescaled relative to observed
2025:

```text
rebased[2020] = (original[2019] + observed[2021]) / 2
rebased[year] = observed[2025] * original[year] / original[2025]  # 2026-2050
```

Explicit zeroes in the source are treated as reported zero production.
Incomplete regions, demand, scrap, and the upstream projection workbook remain
unchanged. The source's geographically unassigned `Others` row is validated
against the World total but is not allocated, and no global rescaling is
applied.

Generate the corresponding comparison figure with:

```text
python steel/plot_steel_production_old_vs_worldsteel_2021_2025.py
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
- `outputs/steel_production_omnia_worldsteel_2021_2025_rebased.csv`
- `outputs/steel_production_omnia_worldsteel_2021_2025_rebased_growth_rates.csv`
- `outputs/steel_production_worldsteel_2021_2025_rebase_audit.csv`
- `outputs/figures/steel_production_omnia_old_vs_worldsteel_2021_2025_rebased_2019_2050.pdf`
- `outputs/figures/steel_production_omnia_old_vs_worldsteel_2021_2025_rebased_2019_2050.png`
