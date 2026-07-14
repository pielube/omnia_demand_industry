from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MAPS_DIR = BASE_DIR / "maps"
OUTPUTS_DIR = BASE_DIR / "outputs"

INPUT_CSV = OUTPUTS_DIR / "aluminium_primary_country_projection_2019_2050.csv"
OMNIA_MAPPING_CSV = MAPS_DIR / "OMNIA_region_mapping_241120.csv"

TOTALS_CSV = OUTPUTS_DIR / "aluminium_primary_omnia_region_projection_2019_2050.csv"
GROWTH_CSV = OUTPUTS_DIR / "aluminium_primary_omnia_region_growth_2019_2050.csv"

BASE_YEAR = 2019
END_YEAR = 2050
YEARS = [str(year) for year in range(BASE_YEAR, END_YEAR + 1)]


def read_inputs(input_csv=INPUT_CSV):
    projection = pd.read_csv(input_csv)
    mapping = pd.read_csv(OMNIA_MAPPING_CSV)

    projection_required = {"ISO3", *YEARS}
    projection_missing = projection_required - set(projection.columns)
    if projection_missing:
        raise ValueError(
            f"Country projection is missing columns: {sorted(projection_missing)}"
        )

    mapping_required = {"ISO3", "region"}
    mapping_missing = mapping_required - set(mapping.columns)
    if mapping_missing:
        raise ValueError(f"OMNIA mapping is missing columns: {sorted(mapping_missing)}")

    region_counts = mapping.groupby("ISO3")["region"].nunique(dropna=False)
    conflicting_iso3 = region_counts[region_counts.ne(1)].index.tolist()
    if conflicting_iso3:
        raise ValueError(
            "OMNIA mapping assigns an ISO3 code to multiple regions: "
            f"{sorted(conflicting_iso3)}"
        )

    region_lookup = (
        mapping[["ISO3", "region"]]
        .drop_duplicates(subset="ISO3")
        .rename(columns={"region": "OMNIARegionFromMapping"})
    )
    projection = projection.merge(
        region_lookup,
        on="ISO3",
        how="left",
        validate="many_to_one",
    )

    unmapped = projection.loc[
        projection["OMNIARegionFromMapping"].isna(), "ISO3"
    ].tolist()
    if unmapped:
        raise ValueError(f"Countries missing from OMNIA mapping: {sorted(unmapped)}")

    if "OMNIARegion" in projection.columns:
        mismatches = projection.loc[
            projection["OMNIARegion"].ne(projection["OMNIARegionFromMapping"]),
            ["ISO3", "OMNIARegion", "OMNIARegionFromMapping"],
        ]
        if not mismatches.empty:
            raise ValueError(
                "Projection OMNIA regions disagree with the mapping:\n"
                f"{mismatches.to_string(index=False)}"
            )

    projection[YEARS] = projection[YEARS].apply(pd.to_numeric, errors="raise")
    return projection


def build_outputs(projection):
    totals = (
        projection.groupby("OMNIARegionFromMapping", as_index=False)[YEARS]
        .sum()
        .rename(columns={"OMNIARegionFromMapping": "OMNIARegion"})
        .sort_values("OMNIARegion")
        .reset_index(drop=True)
    )

    source_totals = projection[YEARS].sum()
    regional_totals = totals[YEARS].sum()
    max_difference = (regional_totals - source_totals).abs().max()
    if max_difference > 1e-6:
        raise ValueError(
            "OMNIA-region totals do not reproduce the country totals. "
            f"Max difference: {max_difference}"
        )

    growth = totals.copy()
    base_values = totals[str(BASE_YEAR)]
    zero_base = base_values.eq(0)

    nonzero_future = totals.loc[zero_base, YEARS].ne(0).any(axis=1)
    if nonzero_future.any():
        regions = totals.loc[zero_base & nonzero_future, "OMNIARegion"].tolist()
        raise ValueError(
            "Cannot calculate base-year growth for zero-base regions with nonzero "
            f"future values: {regions}"
        )

    growth.loc[~zero_base, YEARS] = (
        totals.loc[~zero_base, YEARS]
        .div(base_values.loc[~zero_base], axis=0)
        .sub(1)
        .mul(100)
    )
    growth.loc[zero_base, YEARS] = 0.0

    return totals, growth, max_difference


def generate_outputs(input_csv, totals_csv, growth_csv):
    projection = read_inputs(input_csv)
    totals, growth, max_difference = build_outputs(projection)

    totals.to_csv(totals_csv, index=False)
    growth.to_csv(growth_csv, index=False)

    print(f"Saved: {totals_csv}")
    print(f"Saved: {growth_csv}")
    print(f"OMNIA regions: {len(totals)}")
    print(f"Years included: {BASE_YEAR}-{END_YEAR}")
    print(f"Max aggregation difference, kt: {max_difference:.3e}")


def main():
    generate_outputs(INPUT_CSV, TOTALS_CSV, GROWTH_CSV)


if __name__ == "__main__":
    main()
