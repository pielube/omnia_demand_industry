# Cement Data Workflow

This folder builds the final country-level and OMNIA-region cement-production
projections using income elasticities and WCA regional totals.

## Folder Structure

- `inputs/`: cement-specific WCA source data and documentation.
- `maps/`: the WCA country-region mapping used to constrain projections.
- `outputs/`: the country projection and OMNIA absolute and growth-rate CSVs.
- `../shared_inputs/`: population, SSP2 GDP projections, and the OMNIA
  country-region mapping.

## Method

Historical country cement production is downloaded from Zenodo and retained
through 2024. From 2025 onward, each country's unconstrained demand follows GDP
per capita and the cement income-elasticity curve. Within every WCA region,
country projections are then rescaled so their sum exactly matches the
corresponding WCA regional total.

The WCA trajectories are first calibrated to mapped historical production in
2024 without changing their percentage path:

```text
python cement/rescale_wca_regional_consumption.py
```

Generate the country projection:

```text
python cement/create_cement_country.py
```

This uses:

- historical cement production from Zenodo;
- population from `../shared_inputs/undesa_pop.xlsx`;
- SSP2 GDP from `../shared_inputs/gdp_projection_country_SSP2.xlsx`;
- calibrated WCA totals from
  `inputs/wca_regional_cement_consumption_rescaled.csv`; and
- country assignments from `maps/wca_country_region_mapping.csv`.

Aggregate the same country projection to OMNIA regions:

```text
python cement/create_cement_omnia.py
```

## Final Outputs

- `outputs/cement_country.csv`: country cement production in kt, 1951-2100.
- `outputs/cement_omnia.csv`: OMNIA-region cement production in kt, 2019-2050.
- `outputs/cement_omnia_growth_rates.csv`: OMNIA-region percentage growth
  relative to 2019, for 2019-2050.
