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
- `outputs_skt_taiwan/`: preserved outputs from before the Taiwan region
  reassignment, including the existing workbooks and figures.
- `README.md`: brief sector-specific workflow notes.

The shared inputs currently comprise the UN DESA population and SSP2 GDP
workbooks, the OMNIA country-region mapping, and the OMNIA INF workbook.

Generated outputs are generally stored as `.csv`; steel also retains its final
OMNIA-facing workbook.

## OMNIA region definition

The shared country-region mapping now assigns only South Korea (`KOR`) to
`SKT`; Taiwan (`TWN`) belongs to `CHN`, alongside its existing members. Current
projections are in each sector's `outputs/` directory. Compare the same relative
filenames in `outputs_skt_taiwan/` for the previous region definition.

This is an OMNIA geography change. The source WCA and Zijie regional definitions
remain as supplied (Taiwan remains in Zijie's `Other Asia`). Aluminium source
allocations are interpreted using their original geography before applying the
current OMNIA mapping; sector READMEs describe the regeneration steps.
For steel, the updated workbook supplies regional production and scrap under
the revised geography. The WSA-indexed production variant preserves its OMNIA
2019 anchors and applies the workbook's post-2025 growth from its indexed
2025 level. Scrap includes Taiwan in CHN throughout, including 2019.
The existing `aluminium/outputs_old/` directory retains its earlier comparison
baseline and is separate from this archive.
