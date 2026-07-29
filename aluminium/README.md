# Aluminium Data Workflow

This folder builds the final country-level and OMNIA-region aluminium
projections for primary production, secondary production, and scrap.

## Folder Structure

- `inputs/`: aluminium-specific source data, including Zijie's scenario
  workbook and the extracted BGS primary-production history.
- `maps/`: derived country allocation maps for primary and secondary
  production.
- `outputs/`: the six absolute projection CSVs and three OMNIA growth-rate CSVs.
- `../shared_inputs/`: central reference inputs, including the OMNIA
  country-region mapping and INF workbook.

## Preparation

The committed mapping files can be rebuilt from the shared OMNIA inputs with:

```text
python aluminium/add_zijie_regions_to_omnia_mapping.py
python aluminium/create_primary_producer_zijie_map.py
python aluminium/create_secondary_producer_zijie_map.py
```

The `build_*_zijie_baseline.py` modules construct the original Zijie-allocated
country baselines in memory. They are support modules for the final workflows
and do not write legacy projection files.

## Final Workflows

Run the BGS-aligned primary workflow:

```text
python aluminium/create_primary_country_projection_bgs_aligned.py
```

It retains the OMNIA/INF value for 2019, uses observed BGS country production
for 2020-2024, holds 2025 equal to 2024, and applies each Zijie region's growth
index from 2026 onward. It writes both the country and OMNIA-region outputs.

Run the 2025-aligned secondary and scrap workflow:

```text
python aluminium/create_secondary_scrap_2025_aligned_projections.py
```

It retains the existing Zijie-allocated values through 2024, estimates each
country's 2025 value using an ordinary least-squares trend over 2019-2024
(floored at zero), and applies Zijie regional growth from 2026 onward. It
writes country and OMNIA-region outputs for both metrics.

## Final Outputs

- `outputs/aluminium_primary_country.csv`
- `outputs/aluminium_primary_omnia.csv`
- `outputs/aluminium_primary_omnia_growth_rates.csv`
- `outputs/aluminium_secondary_country.csv`
- `outputs/aluminium_secondary_omnia.csv`
- `outputs/aluminium_secondary_omnia_growth_rates.csv`
- `outputs/aluminium_scrap_country.csv`
- `outputs/aluminium_scrap_omnia.csv`
- `outputs/aluminium_scrap_omnia_growth_rates.csv`

Primary-production history is sourced from the British Geological Survey,
*World Mineral Production 2020-24*. BGS does not provide equivalent
country-level secondary aluminium or scrap tables in that publication.

Acknowledgement: World Mineral Statistics contributed by permission of the
British Geological Survey.
