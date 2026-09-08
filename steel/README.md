# Steel Data Workflow

This folder builds a combined country-level steel dataset from SteelIQ-derived inputs and UN DESA population data.

## Folder Structure

- `inputs/`: sector-specific raw source files and smaller extracts copied from SteelIQ.
- `maps/`: mapping files used by post-processing workflows.
- `outputs/`: final generated outputs.
- `outputs_skt_taiwan/`: preserved outputs before the WSA region change,
  including the original indexed projection and comparison figures.
- `outputs_before_workbook_update/`: checkpoint of the derived outputs before
  refreshing them from the user-updated workbook, including comparison figures.
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

After editing and saving the final workbook with recalculated formula values,
refresh all dependent projections and figures in this order:

```text
python steel/extract_omnia_region_projections.py
python steel/rebase_steel_production_omnia_2019_worldsteel_indexed.py
python steel/plot_steel_production_old_vs_omnia_2019_worldsteel_indexed.py
python plot_chn_skt_comparison.py
```

The extraction reads the workbook's saved values without modifying the workbook.
It refreshes regional production, scrap, and their growth indices. The WSA
variant then takes its 2019 anchors and post-2025 growth path from the refreshed
production CSV. `steel_demand_and_scrap.csv` is an upstream country dataset
built from the raw extracts; it does not depend on this final workbook.

## OMNIA-2019-Anchored World Steel Index

This separate production variant uses OMNIA for each region's calibrated 2019
level and World Steel only for the 2019-2025 change. It does not overwrite the
original projection, demand, scrap, or either upstream workbook.

The revised WSA definition assigns Taiwan (`TWN`) to CHN and only South Korea
(`KOR`) to SKT. Both country maps use this definition for every WSA observation
from 2019 through 2025, including the 2019 denominator. The OMNIA anchor is a
separate input: its original 2019 regional values are kept exactly, with no
Taiwan production transfer by the indexing script. The updated workbook retains
CHN's 932.634463 Mt and SKT's 68.171605 Mt production anchors. The refreshed
`outputs/steel_production_omnia.csv` supplies the post-2025 growth path.

The user-updated workbook also assigns Taiwan to CHN in its regional
aggregations. This changes CHN/SKT's standard production paths after 2019 and
their scrap totals in every year, including 2019. Refreshing from this workbook
leaves the WSA-indexed 2019-2025 levels unchanged and updates its 2026-2050
growth path. Country inputs and the archived outputs are preserved.

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

For OMNIA region `r`, workbook-derived OMNIA production `O`, fixed-basket World Steel
production `W`, and new production `N`, the calculation is:

```text
N[r, 2019] = O[r, 2019]
N[r, y] = O[r, 2019] * W[r, y] / W[r, 2019]       # 2020-2025
N[r, y] = N[r, 2025] * O[r, y] / O[r, 2025]       # 2026-2050
```

Thus 2025 is both WSA-indexed from OMNIA 2019 and the anchor for the future
projection. The workbook's post-2025 regional growth path is preserved,
including the 2025-2026 handoff: `N[r, 2026] / N[r, 2025]` equals
`O[r, 2026] / O[r, 2025]`. The audit reports the handoff change and checks this
relationship explicitly. Regional series are not rescaled to force their sum
to equal global steel demand.

Generate the indexed projection, growth indices, and calculation audit with:

```text
python steel/rebase_steel_production_omnia_2019_worldsteel_indexed.py
```

Generate the workbook-OMNIA-versus-revised-WSA comparison figure with:

```text
python steel/plot_steel_production_old_vs_omnia_2019_worldsteel_indexed.py
```

To compare the archived and revised WSA-indexed projections directly for CHN
and SKT, with the same 2019 anchors, run:

```text
python plot_chn_skt_comparison.py
```

The steel production panel in `../comparison_figures/` reads the indexed CSV
from `outputs_skt_taiwan/` and `outputs/`. Its two curves use different WSA
regional indices and, from 2026 onward, the respective workbook growth paths.
The scrap comparison uses the old and updated workbook regional scrap totals.
The detailed audit
records the revised baskets, denominators, index calculations, input hashes,
and 2025-2026 handoff checks. The existing archive is preserved unchanged.

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
