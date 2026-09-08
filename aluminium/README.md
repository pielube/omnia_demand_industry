# Aluminium Data Workflow

This folder builds the final country-level and OMNIA-region aluminium
projections for primary production, secondary production, and scrap.

## Folder Structure

- `inputs/`: aluminium-specific source data, including Zijie's scenario
  workbook and the extracted BGS primary-production history.
- `maps/`: derived country allocation maps for primary and secondary
  production.
- `outputs/`: scenario subdirectories containing country projections,
  OMNIA-region projections, and growth-rate CSVs for primary, secondary, scrap,
  and total aluminium production.
- `ARCHIVED_outputs_skt_taiwan/`: unchanged outputs from before Taiwan moved from SKT
  to CHN, including the original comparison figures.
- `ARCHIVED_outputs_old/`: the earlier methodology archive, retained separately.
- `../shared_inputs/`: central reference inputs, including the OMNIA
  country-region mapping and INF workbook.

## Preparation

The committed mapping files can be rebuilt from the shared OMNIA inputs with:

```text
python aluminium/add_zijie_regions_to_omnia_mapping.py
python aluminium/create_primary_producer_zijie_map.py
python aluminium/create_secondary_producer_zijie_map.py
```

The secondary producer map uses the 2019 source-region values in
`INF_Data!G232:AH232` as binding totals (31.75 Mt globally). Available
secondary-country observations provide within-region allocation weights.
Where those observations are absent, OMNIA primary-production country shares
are used; a single-country region is assigned directly. Zijie data is not used
to construct the 2019 secondary baseline.

The source workbook retains its original geography, with Taiwan in SKT.
Country baselines are allocated within those source regions first, then
aggregated using the current shared mapping: SKT contains South Korea only,
and Taiwan belongs to CHN. The producer maps retain source-region metadata;
the secondary map reports both source and current totals and shares. This
preserves country production and global totals. Taiwan remains in Zijie's
`Other Asia` region, since that independent scenario geography has not changed.

The `build_*_zijie_baseline.py` modules construct the country baselines in
memory. The secondary baseline is OMNIA-controlled in 2019; the later modeled
years use Zijie's regional trajectories. These are support modules for the
final workflows and do not write legacy projection files.

## Final Workflows

To rebuild both producer maps, all three scenarios (including total production),
and the comparison figures in the correct order, run:

```text
python aluminium/regenerate_aluminium_outputs.py
```

This command leaves both archives unchanged. The original figures continue to
compare against `ARCHIVED_outputs_old/baseline/`; additional figures named
`*_skt_taiwan_vs_corrected_*` compare the new baseline against
`ARCHIVED_outputs_skt_taiwan/baseline/`, including total production.

Run `python aluminium/test_region_allocation.py` to check that reassigning
Taiwan preserves country baselines even when it has positive 2019 production.

Run the BGS-aligned primary workflow:

```text
python aluminium/create_primary_country_projection_bgs_aligned.py
```

It retains the OMNIA/INF value for 2019 and uses observed BGS country
production for 2020-2024. Zijie's 2024 regional value is replaced in memory
with a linear back-extrapolation, `2 × Zijie 2025 − Zijie 2026`. Each country
is anchored to its BGS 2024 value and follows its Zijie region's trajectory
relative to that synthetic 2024 value from 2025 onward. This avoids a flat
2024-2025 splice while preserving BGS history and Zijie's future curve shape.
It writes both the country and OMNIA-region outputs.

Run the 2025-aligned secondary and scrap workflow:

```text
python aluminium/create_secondary_scrap_2025_aligned_projections.py
```

For secondary aluminium, it starts from the OMNIA-controlled 2019 country
allocation described above. It retains the constructed baseline values through
2024, estimates each country's 2025 value using an ordinary least-squares trend
over 2019-2024 (floored at zero), and applies Zijie regional growth from 2026
onward. It writes country and OMNIA-region outputs for both metrics.

Run the recycling-rate and lifetime scenario workflows:

```text
python aluminium/create_aluminium_scenario_outputs.py
```

This applies the same primary BGS alignment, secondary OMNIA baseline, 2025
trend alignment, country allocation, and OMNIA aggregation methods to Zijie's
`recycling rate scenario` and `lifetime scenario` sheets. Outputs use the same
twelve filenames as the baseline. Scenario outputs are written to:

- `outputs/baseline/`
- `outputs/recycling_rate_scenario/`
- `outputs/lifetime_scenario/`

## Final Outputs

The `*_omnia_growth_rates.csv` files are transposed milestone-year indices:
years are rows, OMNIA regions are columns, 2019 equals 1, and the 2050 index is
held constant through 2100.

- `outputs/baseline/aluminium_primary_country.csv`
- `outputs/baseline/aluminium_primary_omnia.csv`
- `outputs/baseline/aluminium_primary_omnia_growth_rates.csv`
- `outputs/baseline/aluminium_secondary_country.csv`
- `outputs/baseline/aluminium_secondary_omnia.csv`
- `outputs/baseline/aluminium_secondary_omnia_growth_rates.csv`
- `outputs/baseline/aluminium_scrap_country.csv`
- `outputs/baseline/aluminium_scrap_omnia.csv`
- `outputs/baseline/aluminium_scrap_omnia_growth_rates.csv`
- `outputs/baseline/aluminium_total_country.csv`
- `outputs/baseline/aluminium_total_omnia.csv`
- `outputs/baseline/aluminium_total_omnia_growth_rates.csv`

The `aluminium_total_*` files sum primary and secondary aluminium ingot
production at country level, then use the same OMNIA aggregation and
milestone-year growth-rate formats as the individual metrics.

Primary-production history is sourced from the British Geological Survey,
*World Mineral Production 2020-24*. BGS does not provide equivalent
country-level secondary aluminium or scrap tables in that publication.

Acknowledgement: World Mineral Statistics contributed by permission of the
British Geological Survey.
