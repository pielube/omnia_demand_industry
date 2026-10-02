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
- `ARCHIVED_outputs_skt_taiwan/`: preserved outputs from before the Taiwan region
  reassignment, including the existing workbooks and figures.
- `README.md`: brief sector-specific workflow notes.

The shared inputs currently comprise the UN DESA population and SSP2 GDP
workbooks, the OMNIA country-region mapping, and the OMNIA INF workbook.

Generated outputs are generally stored as `.csv`; steel also retains its final
OMNIA-facing workbook.

## TIAM regional outputs

Aluminium and cement also have TIAM-region CSVs beside every current
`*omnia*.csv`, with `omnia` replaced by `tiam` in the filename. Their absolute
projections contain `TIAMRegion` and annual 2019-2050 values in kt. Growth
files use the same milestone years as OMNIA, with 2019 equal to 1 and the 2050
index held constant through 2100. TIAM indices are recalculated from the TIAM
totals rather than averaging OMNIA indices.

The supplied map is saved as
`shared_inputs/tiam_country_countrycode_region.csv`; documented coverage
additions are in `shared_inputs/tiam_country_region_supplements.csv`. See
`shared_inputs/README.md` for the five approved geographic corrections and
the assumptions used for omitted territories.

Regenerate all 26 TIAM CSVs from the existing country projections with:

```text
python create_tiam_country_outputs.py
```

Run this after refreshing aluminium or cement country projections. It checks
mapping coverage and annual global totals before writing the TIAM files.
Steel has a separate TIAM workbook and seven regional CSVs. Rebuild them with:

```text
python steel/create_tiam_steel_outputs.py --calibration-method worldsteel
```

This replays the steel workbook's production calculation with TIAM country
aggregations, uses reported World Steel 2019 country production for calibration,
and recalculates a formula-based TIAM workbook in a separate hidden Excel
instance before extracting the CSVs. See `steel/README.md` for the calibration
and growth-adjustment assumptions.

## OMNIA region definition

The shared country-region mapping now assigns only South Korea (`KOR`) to
`SKT`; Taiwan (`TWN`) belongs to `CHN`, alongside its existing members. Current
projections are in each sector's `outputs/` directory. Compare the same relative
filenames in `ARCHIVED_outputs_skt_taiwan/` for the previous region definition.

This is an OMNIA geography change. The source WCA and Zijie regional definitions
remain as supplied (Taiwan remains in Zijie's `Other Asia`). Aluminium source
allocations are interpreted using their original geography before applying the
current OMNIA mapping; sector READMEs describe the regeneration steps.
For steel, the updated workbook supplies regional production and scrap under
the revised geography. The WSA-indexed production variant preserves its OMNIA
2019 anchors and applies the workbook's post-2025 growth from its indexed
2025 level. Scrap includes Taiwan in CHN throughout, including 2019.
The existing `aluminium/ARCHIVED_outputs_old/` directory retains its earlier comparison
baseline and is separate from this archive.
