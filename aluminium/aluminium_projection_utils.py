from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

OMNIA_MAPPING_CSV = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"

BASE_YEAR = 2019
END_YEAR = 2050
YEARS = [str(year) for year in range(BASE_YEAR, END_YEAR + 1)]
MILESTONE_YEARS = [
    2019,
    2023,
    2025,
    2030,
    2035,
    2040,
    2045,
    2050,
    2060,
    2070,
    2080,
    2090,
    2100,
]
SOURCE_MILESTONE_YEARS = [year for year in MILESTONE_YEARS if year <= END_YEAR]


def add_omnia_regions(projection):
    projection = projection.copy()
    projection.columns = projection.columns.map(str)
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


def aggregate_to_omnia_regions(projection):
    projection = add_omnia_regions(projection)
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

    return totals


def calculate_growth_rates(projection):
    """Create a milestone-year index with 2019 equal to one."""
    indexed = projection.set_index("OMNIARegion").copy()
    source_years = [str(year) for year in SOURCE_MILESTONE_YEARS]
    indexed[source_years] = indexed[source_years].apply(
        pd.to_numeric,
        errors="raise",
    )
    base_values = indexed[str(BASE_YEAR)]
    zero_base = base_values.eq(0)

    nonzero_future = indexed.loc[zero_base, source_years].ne(0).any(axis=1)
    if nonzero_future.any():
        regions = indexed.index[zero_base & nonzero_future].tolist()
        raise ValueError(
            "Cannot calculate growth for zero-base regions with nonzero "
            f"future values: {regions}"
        )

    growth = (
        indexed.loc[:, source_years]
        .div(base_values.loc[~zero_base], axis=0)
        .transpose()
    )
    growth.loc[:, zero_base] = 1.0
    growth.index = growth.index.astype(int)

    for year in MILESTONE_YEARS:
        if year > END_YEAR:
            growth.loc[year] = growth.loc[END_YEAR]

    growth = growth.loc[MILESTONE_YEARS]
    growth.index.name = "Year"
    return growth.reset_index()
