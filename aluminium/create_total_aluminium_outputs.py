from pathlib import Path

import numpy as np
import pandas as pd

from aluminium_projection_utils import (
    YEARS,
    aggregate_to_omnia_regions,
    calculate_growth_rates,
)


IDENTITY_COLUMNS = [
    "Country",
    "ISO2",
    "ISO3",
    "OMNIARegion",
    "ZijieRegion",
]
METRIC = "Primary and secondary aluminium ingot production"
UNIT = "kt"


def build_total_country_projection(primary, secondary):
    required = {*IDENTITY_COLUMNS, *YEARS}
    for name, projection in (
        ("primary", primary),
        ("secondary", secondary),
    ):
        missing = required - set(projection.columns)
        if missing:
            raise ValueError(
                f"{name.title()} projection is missing columns: "
                f"{sorted(missing)}"
            )

    if len(primary) != len(secondary):
        raise ValueError(
            "Primary and secondary country projections have different "
            f"row counts: {len(primary)} and {len(secondary)}."
        )
    if not primary[IDENTITY_COLUMNS].equals(
        secondary[IDENTITY_COLUMNS]
    ):
        raise ValueError(
            "Primary and secondary country rows are not aligned on the "
            "country and region identity columns."
        )

    primary_values = primary[YEARS].apply(pd.to_numeric, errors="raise")
    secondary_values = secondary[YEARS].apply(
        pd.to_numeric,
        errors="raise",
    )
    output = primary[IDENTITY_COLUMNS].copy()
    output["Metric"] = METRIC
    output["Unit"] = UNIT
    output["CalculationMethod"] = (
        "Country-level primary production plus secondary production"
    )
    output[YEARS] = primary_values + secondary_values

    if output[YEARS].lt(0).any().any():
        raise ValueError("Combined aluminium projection contains negatives.")
    expected_totals = primary_values.sum() + secondary_values.sum()
    actual_totals = output[YEARS].sum()
    if not np.allclose(actual_totals.to_numpy(), expected_totals.to_numpy()):
        raise ValueError(
            "Combined country totals do not equal primary plus secondary."
        )
    return output


def write_total_outputs(output_dir, require_inputs=False):
    output_dir = Path(output_dir)
    primary_path = output_dir / "aluminium_primary_country.csv"
    secondary_path = output_dir / "aluminium_secondary_country.csv"
    missing_inputs = [
        path for path in (primary_path, secondary_path) if not path.exists()
    ]
    if missing_inputs:
        if require_inputs:
            raise FileNotFoundError(
                "Cannot build combined aluminium outputs; missing: "
                + ", ".join(str(path) for path in missing_inputs)
            )
        return None

    country_path = output_dir / "aluminium_total_country.csv"
    omnia_path = output_dir / "aluminium_total_omnia.csv"
    growth_path = output_dir / "aluminium_total_omnia_growth_rates.csv"

    primary = pd.read_csv(primary_path)
    secondary = pd.read_csv(secondary_path)
    country = build_total_country_projection(primary, secondary)
    country.to_csv(country_path, index=False)

    omnia = aggregate_to_omnia_regions(country)
    omnia.to_csv(omnia_path, index=False)
    calculate_growth_rates(omnia).to_csv(growth_path, index=False)

    print(f"Saved: {country_path}")
    print(f"Saved: {omnia_path}")
    print(f"Saved: {growth_path}")
    return {
        "country": country_path,
        "omnia": omnia_path,
        "growth": growth_path,
    }


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    write_total_outputs(
        BASE_DIR / "outputs" / "baseline",
        require_inputs=True,
    )
