# Aluminium Data Workflow

This folder builds country-level aluminium projections from Zijie's 10-region baseline scenario and the OMNIA country-region mapping.

## Folder Structure

- `inputs/`: raw source files, including Zijie's scenario workbook, the OMNIA INF workbook, and the Bertram region definition document.
- `maps/`: derived mapping files used for allocation.
- `outputs/`: final country-level projection CSVs and figures.
- `*.py`: scripts used to create maps, projections, and plots.

Generated projection outputs are kept as `.csv` only. The remaining `.xlsx` files are raw inputs.

## Processing Steps

1. Add Zijie regions to the OMNIA country mapping:
   `add_zijie_regions_to_omnia_mapping.py`

   This reads `maps/OMNIA_region_mapping_241120.csv` and assigns each country to
   one of Zijie's aluminium regions, based on the Bertram/IAI Alucycle regional
   definitions, with the UK separated from Europe.
2. Build producer-share maps:
   `create_primary_producer_zijie_map.py`
   `create_secondary_producer_zijie_map.py`

   These scripts extract 2019 country-level primary and secondary production values from the `INF_Data` sheet in `inputs/VT_OMNIA_IIS_INM_INF_v0.4.xlsx`.
   The resulting country values are matched to OMNIA countries and Zijie regions, then saved in `maps/`.
3. Build country-level projections:
   `create_primary_country_projection_from_zijie.py`
   `create_secondary_country_projection_from_zijie.py`
   `create_scrap_country_projection_from_zijie.py`

   These scripts read Zijie's regional baseline projections from
   `inputs/10 regions Al data.xlsx` and allocate them to all OMNIA countries.
   Countries with no allocation share receive zero.
4. Plot selected results:
   `plot_primary_country_projection_top9.py`
   `plot_secondary_country_projection_top9.py`
   `plot_scrap_country_projection_top9.py`
   `plot_zijie_primary_regions_top9.py`

   Figures are saved in `outputs/figures/`.

## Main Assumptions

- Primary production is allocated using 2019 primary producer shares from the INF workbook.
- Secondary production is allocated using 2019 secondary producer shares from the INF workbook.
- Scrap is allocated using the same shares as secondary production.
- For Zijie regions without explicit secondary producer shares, primary producer shares are used as a proxy.
- Zijie's projections start in 2024. Values for 2020-2023 are linearly interpolated between 2019 and 2024.
- For the 2019 scrap baseline, regional totals are back-extrapolated from Zijie's 2024-2030 regional trend and then allocated using secondary shares.
- Country-level totals are checked against Zijie's regional totals for all projected years.

## BGS-Aligned Primary Production Alternative

The original primary-production workflow above is retained unchanged. A parallel
workflow aligns the projection to country-level historical primary aluminium
production from the British Geological Survey (BGS):

- Source publication: *World Mineral Production 2020-24* (BGS, 2026),
  https://nora.nerc.ac.uk/id/eprint/541620/
- Raw publication: `inputs/WMP_2020_to_2024.pdf`
- Extracted primary-aluminium table:
  `inputs/bgs_primary_aluminium_2020_2024.csv`

The BGS table reports primary aluminium in tonnes. The aligned workflow converts
these values to kt; BGS estimate markers and table notes are retained in the
extracted CSV. The workflow uses:

- 2019: the existing OMNIA/INF value, to retain the previous baseline.
- 2020-2024: observed BGS country values.
- 2025: held equal to the BGS 2024 value, avoiding a level jump at the
  historical/model boundary.
- 2026-2050: each country's BGS 2024 value multiplied by its Zijie region's
  growth index relative to 2025.

Consequently, countries within the same Zijie region follow the same post-2025
percentage trajectory, while the country and regional levels are anchored to
BGS history. A country with zero BGS production in 2024 remains at zero unless
an explicit new-production assumption is added.

Run:

```text
python aluminium/create_primary_country_projection_bgs_aligned.py
python aluminium/create_primary_bgs_aligned_omnia_region_projection.py
python aluminium/plot_primary_bgs_alignment_top9.py
```

The first script also compares OMNIA 2019 with BGS 2020. A difference is flagged
as major when it is at least 50 kt and at least 25 per cent, or when a producer
of at least 50 kt appears in only one of the two sources.

BGS does not provide equivalent country-level secondary aluminium or aluminium
scrap tables in *World Mineral Production 2020-24*. The existing secondary and
scrap methods are therefore retained; primary-production history is not used as
a substitute for those distinct metrics.

Acknowledgement: World Mineral Statistics contributed by permission of the
British Geological Survey.

## Secondary and Scrap 2025 Boundary Alignment

A parallel boundary-aligned alternative is also provided for secondary
production and scrap without introducing new historical sources. It:

- retains the existing country values from 2019 through 2024;
- fits an ordinary least-squares linear trend to each country's 2019-2024
  values and extrapolates it to 2025, flooring negative results at zero; and
- applies each Zijie region's growth index relative to 2025 from 2026 onward.

The 2019-2024 values in these alternatives remain those produced by the original
secondary and scrap methods; they should not be interpreted as newly observed
history. The country-level 2025 trend estimates provide the anchor for all
subsequent projections. The original outputs are retained unchanged.

Run:

```text
python aluminium/create_secondary_scrap_2025_aligned_projections.py
python aluminium/plot_secondary_scrap_2025_alignment_top27.py
```

## Final Outputs

- `outputs/aluminium_primary_country_projection_2019_2050.csv`
- `outputs/aluminium_secondary_country_projection_2019_2050.csv`
- `outputs/aluminium_scrap_country_projection_2019_2050.csv`
- `outputs/aluminium_primary_country_projection_bgs_aligned_2019_2050.csv`
- `outputs/aluminium_primary_bgs_vs_omnia_2019_misalignment.csv`
- `outputs/aluminium_primary_bgs_aligned_omnia_region_projection_2019_2050.csv`
- `outputs/aluminium_primary_bgs_aligned_omnia_region_growth_2019_2050.csv`
- `outputs/figures/aluminium_primary_bgs_alignment_top9_2024_3x3.pdf`
- `outputs/figures/aluminium_primary_bgs_alignment_top27_2024_9x3.pdf`
- `outputs/aluminium_secondary_country_projection_2025_aligned_2019_2050.csv`
- `outputs/aluminium_scrap_country_projection_2025_aligned_2019_2050.csv`
- `outputs/aluminium_secondary_2025_aligned_omnia_region_projection_2019_2050.csv`
- `outputs/aluminium_scrap_2025_aligned_omnia_region_projection_2019_2050.csv`
- `outputs/figures/aluminium_secondary_2025_alignment_top27_2024_9x3.pdf`
- `outputs/figures/aluminium_scrap_2025_alignment_top27_2024_9x3.pdf`
