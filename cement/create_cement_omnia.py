"""Aggregate dynamic-share cement projections to OMNIA regions."""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
OUTPUTS_DIR = BASE_DIR / "outputs"

INPUT_CSV = OUTPUTS_DIR / "cement_country.csv"
OMNIA_MAPPING_CSV = (
    REPO_DIR / "shared_inputs" / "OMNIA_region_mapping_241120.csv"
)

OUTPUT_CSV = OUTPUTS_DIR / "cement_omnia.csv"
GROWTH_OUTPUT_CSV = OUTPUTS_DIR / "cement_omnia_growth_rates.csv"

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

# These two cement-country ISO3 codes are absent from the supplied OMNIA map.
# Assignments follow the map's treatment of comparable neighbouring territories.
MISSING_MAPPING_OVERRIDES = {
    "GUF": "LAM",  # French Guiana; Guadeloupe and Martinique are LAM.
    "MHL": "ASE",  # Marshall Islands; other Pacific island states are ASE.
}


def read_inputs() -> pd.DataFrame:
    source = pd.read_csv(INPUT_CSV)
    mapping = pd.read_csv(OMNIA_MAPPING_CSV, dtype=str, keep_default_na=False)

    source_required = {"ISO3", "Metric", "Unit", *YEARS}
    source_missing = source_required - set(source.columns)
    if source_missing:
        raise ValueError(
            f"Cement projection is missing columns: {sorted(source_missing)}"
        )

    projection = source[source["Metric"].eq("Cement production")].copy()
    if projection.empty:
        raise ValueError(f"No cement production rows found in {INPUT_CSV}")
    if not projection["Unit"].dropna().eq("kt cement").all():
        raise ValueError("Expected cement projection values in 'kt cement'")
    if projection["ISO3"].duplicated().any():
        duplicates = sorted(
            projection.loc[projection["ISO3"].duplicated(keep=False), "ISO3"].unique()
        )
        raise ValueError(f"Cement projection has duplicate ISO3 rows: {duplicates}")

    mapping_required = {"ISO3", "region"}
    mapping_missing = mapping_required - set(mapping.columns)
    if mapping_missing:
        raise ValueError(f"OMNIA mapping is missing columns: {sorted(mapping_missing)}")

    mapping["ISO3"] = mapping["ISO3"].str.strip().str.upper()
    mapping["region"] = mapping["region"].str.strip()
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
        .rename(columns={"region": "OMNIARegion"})
    )
    projection["ISO3"] = projection["ISO3"].astype(str).str.strip().str.upper()
    projection = projection.merge(
        region_lookup,
        on="ISO3",
        how="left",
        validate="one_to_one",
    )

    initially_unmapped = set(
        projection.loc[projection["OMNIARegion"].isna(), "ISO3"]
    )
    unexpected_unmapped = sorted(initially_unmapped - set(MISSING_MAPPING_OVERRIDES))
    if unexpected_unmapped:
        raise ValueError(
            f"Countries missing from OMNIA mapping: {unexpected_unmapped}"
        )
    projection["OMNIARegion"] = projection["OMNIARegion"].fillna(
        projection["ISO3"].map(MISSING_MAPPING_OVERRIDES)
    )
    if projection["OMNIARegion"].isna().any():
        raise ValueError("Some cement countries remain without an OMNIA region")

    projection[YEARS] = projection[YEARS].apply(pd.to_numeric, errors="raise")
    return projection


def build_output(
    projection: pd.DataFrame,
) -> tuple[pd.DataFrame, float]:
    totals = (
        projection.groupby("OMNIARegion", as_index=False)[YEARS]
        .sum()
        .sort_values("OMNIARegion")
        .reset_index(drop=True)
    )

    source_totals = projection[YEARS].sum()
    regional_totals = totals[YEARS].sum()
    max_difference = float((regional_totals - source_totals).abs().max())
    if max_difference > 1e-6:
        raise ValueError(
            "OMNIA-region totals do not reproduce the country totals. "
            f"Max difference: {max_difference}"
        )

    return totals, max_difference


def calculate_growth_rates(projection: pd.DataFrame) -> pd.DataFrame:
    """Create a milestone-year index with 2019 equal to one."""
    indexed = projection.set_index("OMNIARegion").copy()
    source_years = [str(year) for year in SOURCE_MILESTONE_YEARS]
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


def main() -> None:
    projection = read_inputs()
    totals, max_difference = build_output(projection)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    totals.to_csv(OUTPUT_CSV, index=False)
    calculate_growth_rates(totals).to_csv(GROWTH_OUTPUT_CSV, index=False)

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Saved: {GROWTH_OUTPUT_CSV}")
    print(f"Countries aggregated: {projection['ISO3'].nunique()}")
    print(f"OMNIA regions: {len(totals)}")
    print(f"Years included: {BASE_YEAR}-{END_YEAR}")
    print(f"Max aggregation difference, kt cement: {max_difference:.3e}")
    if MISSING_MAPPING_OVERRIDES:
        print(f"Explicit missing-map assignments: {MISSING_MAPPING_OVERRIDES}")


if __name__ == "__main__":
    main()
