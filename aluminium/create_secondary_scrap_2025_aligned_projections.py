from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from aluminium_projection_utils import (
    aggregate_to_omnia_regions,
    calculate_growth_rates,
)
from create_total_aluminium_outputs import write_total_outputs
from build_scrap_zijie_baseline import (
    build_projection as build_scrap_baseline,
    make_total_checks as validate_scrap_baseline,
)
from build_secondary_zijie_baseline import (
    build_projection as build_secondary_baseline,
    make_total_checks as validate_secondary_baseline,
)


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs" / "baseline"

ZIJIE_SCENARIO_PATH = INPUTS_DIR / "10 regions Al data.xlsx"
SCENARIO_SHEET = "baseline"

LAST_EXISTING_YEAR = 2024
ALIGNMENT_YEAR = 2025
END_YEAR = 2050
YEARS = list(range(2019, END_YEAR + 1))
TREND_YEARS = list(range(2019, LAST_EXISTING_YEAR + 1))
PROJECTION_YEARS = list(range(ALIGNMENT_YEAR, END_YEAR + 1))
RESCALED_YEARS = list(range(ALIGNMENT_YEAR + 1, END_YEAR + 1))

ZIJIE_REGIONS = [
    "China",
    "North America",
    "Europe",
    "South America",
    "Other Asia",
    "Other main producer",
    "Middle East",
    "Japan",
    "UK",
    "Rest of World",
]

ALIGNMENT_METHOD = (
    "Existing values retained through 2024; 2025 extrapolated using a "
    "country-level OLS linear trend fitted over 2019-2024 and floored at zero; "
    "Zijie regional growth indexed to 2025 thereafter"
)

def make_configs(output_dir):
    return [
        {
            "name": "secondary",
            "scenario_label": "Secondary Al ingot (kt)",
            "baseline_builder": build_secondary_baseline,
            "baseline_validator": validate_secondary_baseline,
            "aligned_country": (
                output_dir / "aluminium_secondary_country.csv"
            ),
            "omnia_totals": (
                output_dir / "aluminium_secondary_omnia.csv"
            ),
            "omnia_growth": (
                output_dir / "aluminium_secondary_omnia_growth_rates.csv"
            ),
        },
        {
            "name": "scrap",
            "scenario_label": "Al scrap (kt)",
            "baseline_builder": build_scrap_baseline,
            "baseline_validator": validate_scrap_baseline,
            "aligned_country": (
                output_dir / "aluminium_scrap_country.csv"
            ),
            "omnia_totals": (
                output_dir / "aluminium_scrap_omnia.csv"
            ),
            "omnia_growth": (
                output_dir / "aluminium_scrap_omnia_growth_rates.csv"
            ),
        },
    ]


def read_zijie_scenario(label, scenario_sheet=SCENARIO_SHEET):
    raw = pd.read_excel(
        ZIJIE_SCENARIO_PATH,
        sheet_name=scenario_sheet,
        header=None,
    )
    matches = raw.iloc[0].eq(label)
    if matches.sum() != 1:
        raise ValueError(f"Could not find one block labelled {label!r}.")

    start_col = int(matches[matches].index[0])
    scenario = raw.iloc[
        1:,
        start_col : start_col + 1 + len(ZIJIE_REGIONS),
    ].copy()
    scenario.columns = ["Year"] + ZIJIE_REGIONS
    scenario = scenario[scenario["Year"].isin(PROJECTION_YEARS)].copy()
    scenario["Year"] = scenario["Year"].astype(int)
    scenario[ZIJIE_REGIONS] = scenario[ZIJIE_REGIONS].apply(
        pd.to_numeric,
        errors="raise",
    )

    missing_years = sorted(set(PROJECTION_YEARS) - set(scenario["Year"]))
    if missing_years:
        raise ValueError(f"Zijie scenario is missing years: {missing_years}")
    return scenario


def build_aligned_projection(config, scenario_sheet=SCENARIO_SHEET):
    old, baseline_scenario = config["baseline_builder"](scenario_sheet)
    config["baseline_validator"](old, baseline_scenario)
    old = pd.read_csv(StringIO(old.to_csv(index=False)))
    required = {"ISO3", "ZijieRegion", *[str(year) for year in YEARS]}
    missing = required - set(old.columns)
    if missing:
        raise ValueError(
            f"{config['name']} baseline is missing columns: {sorted(missing)}"
        )

    scenario = read_zijie_scenario(
        config["scenario_label"],
        scenario_sheet,
    )
    scenario_by_year = scenario.set_index("Year")
    aligned = old.copy()

    for year in YEARS:
        aligned[str(year)] = pd.to_numeric(aligned[str(year)], errors="raise")

    trend_x = np.asarray(TREND_YEARS, dtype=float)
    trend_x_centered = trend_x - trend_x.mean()
    trend_values = aligned[[str(year) for year in TREND_YEARS]].to_numpy(
        dtype=float
    )
    trend_slopes = (
        trend_values @ trend_x_centered
        / np.square(trend_x_centered).sum()
    )
    trend_2025_unclipped = (
        trend_values.mean(axis=1)
        + trend_slopes * (ALIGNMENT_YEAR - trend_x.mean())
    )
    aligned[str(ALIGNMENT_YEAR)] = np.maximum(trend_2025_unclipped, 0.0)

    for year in RESCALED_YEARS:
        growth_by_region = {
            region: (
                scenario_by_year.at[year, region]
                / scenario_by_year.at[ALIGNMENT_YEAR, region]
            )
            for region in ZIJIE_REGIONS
        }
        aligned[str(year)] = (
            aligned[str(ALIGNMENT_YEAR)]
            * aligned["ZijieRegion"].map(growth_by_region)
        )

    aligned["Trend2019_2024Slope_kt_per_year"] = trend_slopes
    aligned["Trend2025Unclipped_kt"] = trend_2025_unclipped
    aligned["AlignmentFactor_vs_old_2025"] = np.where(
        old[str(ALIGNMENT_YEAR)].ne(0),
        aligned[str(ALIGNMENT_YEAR)] / old[str(ALIGNMENT_YEAR)],
        np.nan,
    )
    aligned["BoundaryAlignmentMethod"] = ALIGNMENT_METHOD

    year_columns = [str(year) for year in YEARS]
    metadata_columns = [column for column in old.columns if column not in year_columns]
    aligned = aligned[
        metadata_columns
        + [
            "Trend2019_2024Slope_kt_per_year",
            "Trend2025Unclipped_kt",
            "AlignmentFactor_vs_old_2025",
            "BoundaryAlignmentMethod",
        ]
        + year_columns
    ]

    validate_projection(old, aligned, scenario, config["name"])
    return old, aligned


def validate_projection(old, aligned, scenario, name):
    historical_years = [str(year) for year in TREND_YEARS]
    if not np.allclose(
        old[historical_years].to_numpy(),
        aligned[historical_years].to_numpy(),
    ):
        raise ValueError(f"{name}: values through 2024 were not retained.")

    expected_2025 = np.maximum(aligned["Trend2025Unclipped_kt"], 0.0)
    trend_difference = (
        aligned[str(ALIGNMENT_YEAR)] - expected_2025
    ).abs().max()
    if trend_difference > 1e-9:
        raise ValueError(
            f"{name}: 2025 does not match the extrapolated trend. "
            f"Max diff: {trend_difference}"
        )

    if aligned[[str(year) for year in YEARS]].lt(0).any().any():
        raise ValueError(f"{name}: aligned projection contains negative values.")

    scenario_by_year = scenario.set_index("Year")
    for region in ZIJIE_REGIONS:
        region_output = aligned[aligned["ZijieRegion"].eq(region)]
        anchor = region_output[str(ALIGNMENT_YEAR)].sum()
        for year in PROJECTION_YEARS:
            expected = (
                anchor
                * scenario_by_year.at[year, region]
                / scenario_by_year.at[ALIGNMENT_YEAR, region]
            )
            difference = region_output[str(year)].sum() - expected
            if abs(difference) > 1e-6:
                raise ValueError(
                    f"{name}: regional check failed for {region}, {year}: "
                    f"{difference}"
                )


def run_workflow(
    scenario_sheet=SCENARIO_SHEET,
    output_dir=OUTPUTS_DIR,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {}
    for config in make_configs(output_dir):
        old, aligned = build_aligned_projection(config, scenario_sheet)
        aligned.to_csv(config["aligned_country"], index=False)
        omnia_output = aggregate_to_omnia_regions(
            pd.read_csv(config["aligned_country"])
        )
        omnia_output.to_csv(config["omnia_totals"], index=False)
        calculate_growth_rates(omnia_output).to_csv(
            config["omnia_growth"],
            index=False,
        )

        print(f"Saved: {config['aligned_country']}")
        print(f"Saved: {config['omnia_totals']}")
        print(f"Saved: {config['omnia_growth']}")
        print(
            f"{config['name'].title()} global 2025, old/aligned kt: "
            f"{old[str(ALIGNMENT_YEAR)].sum():.3f} / "
            f"{aligned[str(ALIGNMENT_YEAR)].sum():.3f}"
        )
        outputs[config["name"]] = {
            "country": config["aligned_country"],
            "omnia": config["omnia_totals"],
            "growth": config["omnia_growth"],
        }
    total_outputs = write_total_outputs(output_dir)
    if total_outputs is not None:
        outputs["total"] = total_outputs
    return outputs


def main():
    run_workflow()


if __name__ == "__main__":
    main()
