"""Validate the TIAM country map and aggregate country projections safely."""

from pathlib import Path

import numpy as np
import pandas as pd


REPO_DIR = Path(__file__).resolve().parent
MAPPING_CSV = REPO_DIR / "shared_inputs" / "tiam_country_countrycode_region.csv"
SUPPLEMENTS_CSV = REPO_DIR / "shared_inputs" / "tiam_country_region_supplements.csv"

BASE_YEAR = 2019
END_YEAR = 2050
YEARS = [str(year) for year in range(BASE_YEAR, END_YEAR + 1)]
MILESTONE_YEARS = [2019, 2023, 2025, 2030, 2035, 2040, 2045, 2050,
                   2060, 2070, 2080, 2090, 2100]
TIAM_REGIONS = (
    "AFR", "AUS", "CAN", "CHI", "CSA", "EEU", "FSU", "IND",
    "JPN", "MEA", "MEX", "ODA", "SKO", "UK", "USA", "WEU",
)


def validate_mapping(mapping: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized map; each ISO3 code must have exactly one row."""
    required = {"ISO3", "TIAMRegion", "Country"}
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"TIAM mapping is missing columns: {sorted(missing)}")
    result = mapping[["ISO3", "TIAMRegion", "Country"]].copy()
    for column in result.columns:
        result[column] = result[column].fillna("").astype(str).str.strip()
    result["ISO3"] = result["ISO3"].str.upper()
    result["TIAMRegion"] = result["TIAMRegion"].str.upper()
    if result.empty:
        raise ValueError("TIAM mapping is empty")
    blank_rows = result.eq("").any(axis=1)
    if blank_rows.any():
        raise ValueError(
            "TIAM mapping contains blank country, code, or region fields: "
            f"{result.loc[blank_rows].to_dict(orient='records')}"
        )
    invalid_codes = result.loc[~result["ISO3"].str.fullmatch(r"[A-Z]{3}"), "ISO3"]
    if not invalid_codes.empty:
        raise ValueError(f"Invalid TIAM ISO3 codes: {sorted(invalid_codes.unique())}")
    invalid_regions = sorted(set(result["TIAMRegion"]) - set(TIAM_REGIONS))
    if invalid_regions:
        raise ValueError(f"Unknown TIAM regions: {invalid_regions}")
    duplicates = result["ISO3"].duplicated(keep=False)
    if duplicates.any():
        duplicate_codes = sorted(result.loc[duplicates, "ISO3"].unique())
        raise ValueError(
            "TIAM mapping contains duplicate or conflicting ISO3 assignments: "
            f"{duplicate_codes}"
        )
    return result.sort_values("ISO3").reset_index(drop=True)


def read_tiam_mapping(
    mapping_path: Path = MAPPING_CSV,
    supplement_path: Path | None = SUPPLEMENTS_CSV,
) -> pd.DataFrame:
    """Combine supplied assignments with documented additions, never overrides."""
    paths = [Path(mapping_path)]
    if supplement_path is not None and Path(supplement_path).exists():
        paths.append(Path(supplement_path))
    frames = []
    for path in paths:
        source = pd.read_csv(path, dtype=str, keep_default_na=False)
        required = {"Country", "Code", "Region"}
        missing = required - set(source.columns)
        if missing:
            raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
        if path != paths[0]:
            if "Reason" not in source.columns or source["Reason"].str.strip().eq("").any():
                raise ValueError("Each supplemental TIAM assignment needs a Reason")
        frames.append(source.rename(columns={"Code": "ISO3", "Region": "TIAMRegion"}))
    return validate_mapping(pd.concat(frames, ignore_index=True))


def _numeric_values(
    projection: pd.DataFrame,
    year_columns: list[str],
    label: str,
) -> pd.DataFrame:
    missing = set(year_columns) - set(projection.columns)
    if missing:
        raise ValueError(f"{label} is missing year columns: {sorted(missing)}")
    values = projection[year_columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{label} contains missing or nonfinite values")
    if values.lt(0).any().any():
        raise ValueError(f"{label} contains negative values")
    return values


def validate_global_totals(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    year_columns: list[str] = YEARS,
    label: str = "Regional and source projections",
) -> None:
    """Reject any loss of annual volume during aggregation or reallocation."""
    years = [str(year) for year in year_columns]
    actual = actual.copy()
    expected = expected.copy()
    actual.columns = actual.columns.map(str)
    expected.columns = expected.columns.map(str)
    actual_totals = _numeric_values(actual, years, label).sum()
    expected_totals = _numeric_values(expected, years, label).sum()
    equal = np.isclose(actual_totals, expected_totals, rtol=1e-10, atol=1e-6)
    if not equal.all():
        differences = (actual_totals - expected_totals).abs()
        raise ValueError(
            f"{label} do not preserve global totals; "
            f"maximum annual difference {differences.max():.12g}, "
            f"years {differences.index[~equal].tolist()}"
        )


def aggregate_country_projection(
    projection: pd.DataFrame,
    mapping: pd.DataFrame,
    iso_column: str = "ISO3",
    year_columns: list[str] = YEARS,
) -> pd.DataFrame:
    """Sum country volumes into all 16 TIAM regions, rejecting unmapped rows."""
    source = projection.copy()
    source.columns = source.columns.map(str)
    years = [str(year) for year in year_columns]
    if iso_column not in source:
        raise ValueError(f"Country projection is missing {iso_column}")
    if source.empty:
        raise ValueError("Country projection is empty")
    source[iso_column] = source[iso_column].fillna("").astype(str).str.strip().str.upper()
    invalid_codes = source.loc[~source[iso_column].str.fullmatch(r"[A-Z]{3}"), iso_column]
    if not invalid_codes.empty:
        raise ValueError(f"Invalid country ISO3 codes: {sorted(invalid_codes.unique())}")
    duplicates = source[iso_column].duplicated(keep=False)
    if duplicates.any():
        raise ValueError(
            "Country projection contains duplicate ISO3 rows: "
            f"{sorted(source.loc[duplicates, iso_column].unique())}"
        )
    checked_mapping = validate_mapping(mapping)
    lookup = checked_mapping.set_index("ISO3")["TIAMRegion"]
    region_assignments = source[iso_column].map(lookup)
    if region_assignments.isna().any():
        unmapped = sorted(source.loc[region_assignments.isna(), iso_column].unique())
        raise ValueError(f"Countries missing from TIAM mapping: {unmapped}")
    source[years] = _numeric_values(source, years, "Country projection")
    totals = (
        source[years]
        .groupby(region_assignments.rename("TIAMRegion"))
        .sum()
        .reindex(TIAM_REGIONS, fill_value=0.0)
        .reset_index()
    )
    validate_global_totals(totals, source, years, "TIAM and country projections")
    return totals


def calculate_growth_rates(projection: pd.DataFrame) -> pd.DataFrame:
    """Index regional volumes to 2019; hold their 2050 index through 2100."""
    source = projection.copy()
    source.columns = source.columns.map(str)
    if "TIAMRegion" not in source:
        raise ValueError("Regional projection is missing TIAMRegion")
    regions = source["TIAMRegion"].fillna("").astype(str).str.strip()
    if regions.eq("").any() or regions.duplicated().any():
        raise ValueError("Growth projection needs unique nonblank TIAM regions")
    source["TIAMRegion"] = regions
    milestone_columns = [str(year) for year in MILESTONE_YEARS if year <= END_YEAR]
    _numeric_values(source, milestone_columns, "Growth projection")
    # Check every available annual value, including years between milestones.
    annual_columns = [year for year in YEARS if year in source.columns]
    source[annual_columns] = _numeric_values(source, annual_columns, "Growth projection")
    indexed = source.set_index("TIAMRegion")
    base = indexed[str(BASE_YEAR)]
    zero_base = base.eq(0)
    invalid_zero_base = zero_base & indexed[annual_columns].ne(0).any(axis=1)
    if invalid_zero_base.any():
        raise ValueError(
            "Cannot calculate growth for zero-base regions with nonzero future values: "
            f"{indexed.index[invalid_zero_base].tolist()}"
        )
    growth = indexed[milestone_columns].div(base.mask(zero_base, 1.0), axis=0)
    growth.loc[zero_base, :] = 1.0
    growth = growth.transpose()
    growth.index = growth.index.astype(int)
    for year in MILESTONE_YEARS:
        if year > END_YEAR:
            growth.loc[year] = growth.loc[END_YEAR]
    growth = growth.loc[MILESTONE_YEARS]
    growth.index.name = "Year"
    return growth.reset_index()
