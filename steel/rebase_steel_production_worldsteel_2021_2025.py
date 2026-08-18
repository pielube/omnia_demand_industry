"""Rebase selected OMNIA steel projections to 2021-2025 World Steel data.

The original extracted projection and final Excel projection workbook remain
unchanged. This source-specific workflow writes separate outputs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .extract_omnia_region_projections import calculate_growth_rates
except ImportError:
    from extract_omnia_region_projections import calculate_growth_rates


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
MAPS_DIR = BASE_DIR / "maps"
OUTPUTS_DIR = BASE_DIR / "outputs"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

SOURCE_XLSX = (
    INPUTS_DIR / "worldsteel_crude_steel_production_2021_2025.xlsx"
)
SOURCE_MAP_CSV = MAPS_DIR / "worldsteel_2021_2025_country_map.csv"
OMNIA_MAPPING_CSV = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"

INPUT_PROJECTION_CSV = OUTPUTS_DIR / "steel_production_omnia.csv"
OUTPUT_PROJECTION_CSV = (
    OUTPUTS_DIR / "steel_production_omnia_worldsteel_2021_2025_rebased.csv"
)
OUTPUT_GROWTH_CSV = (
    OUTPUTS_DIR
    / "steel_production_omnia_worldsteel_2021_2025_rebased_growth_rates.csv"
)
OUTPUT_AUDIT_CSV = (
    OUTPUTS_DIR / "steel_production_worldsteel_2021_2025_rebase_audit.csv"
)

SOURCE_SHEET = "P1_crude_steel_total_pub"
SOURCE_TITLE = "Total production of crude steel"
SOURCE_YEARS = list(range(2021, 2026))
SOURCE_YEAR_COLUMNS = [str(year) for year in SOURCE_YEARS]
SOURCE_UNIT = "kt crude steel"
SOURCE_LAST_UPDATED = "28 July 2026"
EXPECTED_SOURCE_SHA256 = (
    "743a06460abf0720b8562b098fab8a18376a9d3e9cdc42bef77f07934fc3fa16"
)
EXPECTED_SOURCE_DATA_ROWS = 125
EXPECTED_MAPPED_COUNTRIES = 120
EXCLUDED_SOURCE_ROWS = {
    "Belgium-Luxemburg",
    "Former Yugoslavia",
    "Serbia-Montenegro",
}

BASE_YEAR = 2019
INTERPOLATED_YEAR = 2020
FIRST_OBSERVED_YEAR = 2021
LAST_OBSERVED_YEAR = 2025
END_YEAR = 2050
YEAR_COLUMNS = [str(year) for year in range(BASE_YEAR, END_YEAR + 1)]

EXPECTED_STRICT_REGIONS = {
    "AFN",
    "ANZ",
    "BRA",
    "CAN",
    "CHL",
    "EUE",
    "IDN",
    "IND",
    "JPN",
    "MEA",
    "MEX",
    "NIG",
    "RUS",
    "SKT",
    "USA",
}
EFFECTIVE_SINGLE_COUNTRY_REGIONS = {"CHN"}
EXPECTED_ELIGIBLE_REGIONS = (
    EXPECTED_STRICT_REGIONS | EFFECTIVE_SINGLE_COUNTRY_REGIONS
)


def file_sha256(path: Path) -> str:
    """Return the hexadecimal SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_source_data() -> tuple[pd.DataFrame, pd.Series, str]:
    """Read and validate the World Steel 2021-2025 Excel export."""
    if not SOURCE_XLSX.is_file():
        raise FileNotFoundError(f"Missing World Steel source: {SOURCE_XLSX}")
    source_sha256 = file_sha256(SOURCE_XLSX)
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError(
            "World Steel source workbook hash does not match the reviewed "
            f"export: {source_sha256}"
        )

    title = pd.read_excel(
        SOURCE_XLSX,
        sheet_name=SOURCE_SHEET,
        header=None,
        nrows=1,
        usecols="A",
    ).iloc[0, 0]
    if title != SOURCE_TITLE:
        raise ValueError(f"Unexpected World Steel source title: {title!r}")

    raw = pd.read_excel(
        SOURCE_XLSX,
        sheet_name=SOURCE_SHEET,
        header=2,
        usecols="A:F",
    )
    expected_columns = ["Country", *SOURCE_YEARS]
    if raw.columns.tolist() != expected_columns:
        raise ValueError(f"Unexpected World Steel columns: {raw.columns.tolist()}")

    copyright_rows = raw.index[
        raw["Country"].astype(str).str.startswith("©", na=False)
    ]
    if len(copyright_rows) != 1:
        raise ValueError("Could not identify the World Steel copyright row")
    data = raw.loc[raw.index < copyright_rows[0]].dropna(subset=["Country"]).copy()
    if len(data) != EXPECTED_SOURCE_DATA_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_SOURCE_DATA_ROWS} source data rows, found {len(data)}"
        )
    if data["Country"].duplicated().any():
        duplicates = data.loc[
            data["Country"].duplicated(keep=False), "Country"
        ].tolist()
        raise ValueError(f"Duplicate World Steel country rows: {duplicates}")

    for year in SOURCE_YEARS:
        data[year] = pd.to_numeric(data[year], errors="raise")
    source_values = data[SOURCE_YEARS].to_numpy(dtype=float)
    if not np.isfinite(source_values).all() or (source_values < 0).any():
        raise ValueError("World Steel source contains invalid production values")

    world = data.loc[data["Country"].eq("World")]
    others = data.loc[data["Country"].eq("Others")]
    if len(world) != 1 or len(others) != 1:
        raise ValueError("World Steel source must contain one World and one Others row")
    world = world.iloc[0]
    others = others.iloc[0]

    legacy = data[data["Country"].isin(EXCLUDED_SOURCE_ROWS)]
    if set(legacy["Country"]) != EXCLUDED_SOURCE_ROWS:
        raise ValueError("Missing legacy all-zero rows from World Steel source")
    if not legacy[SOURCE_YEARS].eq(0).all(axis=None):
        raise ValueError("A legacy World Steel aggregate is no longer all-zero")

    countries = data.loc[
        ~data["Country"].isin({"World", "Others", *EXCLUDED_SOURCE_ROWS})
    ].copy()
    if len(countries) != EXPECTED_MAPPED_COUNTRIES:
        raise ValueError(
            f"Expected {EXPECTED_MAPPED_COUNTRIES} usable countries, "
            f"found {len(countries)}"
        )

    for year in SOURCE_YEARS:
        reconstructed_world = countries[year].sum() + others[year]
        if not np.isclose(
            reconstructed_world, world[year], rtol=0.0, atol=1e-5
        ):
            raise ValueError(
                f"Named countries plus Others do not equal World in {year}: "
                f"{reconstructed_world} vs {world[year]} kt"
            )

    metadata = pd.read_excel(
        SOURCE_XLSX,
        sheet_name=SOURCE_SHEET,
        header=None,
        usecols="A:B",
    )
    last_updated_rows = metadata.index[metadata.iloc[:, 0].eq("Last updated:")]
    if len(last_updated_rows) != 1:
        raise ValueError("Could not identify World Steel last-updated metadata")
    last_updated = str(metadata.iloc[last_updated_rows[0], 1])
    if last_updated != SOURCE_LAST_UPDATED:
        raise ValueError(
            f"Unexpected World Steel last-updated value: {last_updated!r}"
        )
    return countries, world, source_sha256


def read_country_map(source: pd.DataFrame) -> tuple[pd.DataFrame, set[str]]:
    """Read the source-name map and validate it against the shared OMNIA map."""
    mapping = pd.read_csv(SOURCE_MAP_CSV, dtype=str, keep_default_na=False)
    required = {"SourceCountry", "ISO3", "OMNIARegion"}
    missing_columns = required - set(mapping.columns)
    if missing_columns:
        raise ValueError(
            f"World Steel map is missing columns: {sorted(missing_columns)}"
        )
    if len(mapping) != EXPECTED_MAPPED_COUNTRIES:
        raise ValueError(
            f"Expected {EXPECTED_MAPPED_COUNTRIES} mapped countries, "
            f"found {len(mapping)}"
        )
    for column in ("SourceCountry", "ISO3"):
        if mapping[column].duplicated().any():
            duplicates = mapping.loc[
                mapping[column].duplicated(keep=False), column
            ].tolist()
            raise ValueError(f"Duplicate {column} values in source map: {duplicates}")

    source_names = set(source["Country"])
    mapped_names = set(mapping["SourceCountry"])
    if source_names != mapped_names:
        raise ValueError(
            "World Steel source/map country mismatch. Missing from map: "
            f"{sorted(source_names - mapped_names)}; extra in map: "
            f"{sorted(mapped_names - source_names)}"
        )

    shared = pd.read_csv(OMNIA_MAPPING_CSV, dtype=str, keep_default_na=False)
    shared_pairs = shared[["ISO3", "region"]].drop_duplicates()
    ambiguous = shared_pairs["ISO3"].duplicated(keep=False)
    if ambiguous.any():
        bad = shared_pairs.loc[ambiguous].to_dict("records")
        raise ValueError(f"ISO3 codes map to multiple OMNIA regions: {bad}")

    checked = mapping[["ISO3", "OMNIARegion"]].merge(
        shared_pairs, on="ISO3", how="left", validate="one_to_one"
    )
    missing_shared = checked["region"].eq("") | checked["region"].isna()
    if missing_shared.any():
        missing = checked.loc[missing_shared, "ISO3"].tolist()
        raise ValueError(f"Mapped ISO3 codes missing from shared map: {missing}")
    mismatch = checked["OMNIARegion"].ne(checked["region"])
    if mismatch.any():
        bad = checked.loc[
            mismatch, ["ISO3", "OMNIARegion", "region"]
        ].to_dict("records")
        raise ValueError(f"Source and shared OMNIA mappings disagree: {bad}")

    shared_members = {
        region: set(group["ISO3"])
        for region, group in shared_pairs.groupby("region", sort=False)
    }
    source_members = {
        region: set(group["ISO3"])
        for region, group in mapping.groupby("OMNIARegion", sort=False)
    }
    strict_regions = {
        region
        for region, members in shared_members.items()
        if members.issubset(source_members.get(region, set()))
    }
    if strict_regions != EXPECTED_STRICT_REGIONS:
        raise ValueError(
            "Strict World Steel coverage changed: "
            f"{sorted(strict_regions)} vs {sorted(EXPECTED_STRICT_REGIONS)}"
        )

    # CHN is an explicit steel-workbook exception: that workbook defines CHN
    # as China Mainland. The source reports China, reports Hong Kong as zero,
    # and has no separate Macao row.
    source_with_map = mapping.merge(
        source,
        left_on="SourceCountry",
        right_on="Country",
        how="left",
        validate="one_to_one",
    )
    hong_kong = source_with_map.loc[source_with_map["ISO3"].eq("HKG")]
    if len(hong_kong) != 1 or not hong_kong[SOURCE_YEARS].eq(0).all(axis=None):
        raise ValueError("CHN exception requires an explicit all-zero Hong Kong row")
    if "CHN" not in set(source_with_map["ISO3"]):
        raise ValueError("CHN exception requires the China source row")

    eligible_regions = strict_regions | EFFECTIVE_SINGLE_COUNTRY_REGIONS
    if eligible_regions != EXPECTED_ELIGIBLE_REGIONS:
        raise ValueError("Unexpected eligible World Steel regions")
    return mapping, eligible_regions


def read_projection() -> pd.DataFrame:
    """Read and validate the original OMNIA steel-production projection."""
    projection = pd.read_csv(INPUT_PROJECTION_CSV)
    required = ["OMNIARegion", *YEAR_COLUMNS]
    if projection.columns.tolist() != required:
        raise ValueError(
            "Steel production projection columns do not match the expected "
            f"2019-2050 layout: {projection.columns.tolist()}"
        )
    if projection["OMNIARegion"].duplicated().any():
        duplicates = projection.loc[
            projection["OMNIARegion"].duplicated(keep=False), "OMNIARegion"
        ].tolist()
        raise ValueError(f"Duplicate OMNIA production regions: {duplicates}")

    projection[YEAR_COLUMNS] = projection[YEAR_COLUMNS].apply(
        pd.to_numeric, errors="raise"
    )
    values = projection[YEAR_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Original production projection has invalid values")
    return projection


def make_observations(
    source: pd.DataFrame,
    mapping: pd.DataFrame,
    eligible_regions: set[str],
) -> pd.DataFrame:
    """Aggregate source countries to the completely covered OMNIA regions."""
    selected = mapping.merge(
        source,
        left_on="SourceCountry",
        right_on="Country",
        how="left",
        validate="one_to_one",
    )
    selected = selected[selected["OMNIARegion"].isin(eligible_regions)].copy()

    records = []
    for region, group in selected.groupby("OMNIARegion", sort=True):
        any_zero = group.loc[group[SOURCE_YEARS].eq(0).any(axis=1), "SourceCountry"]
        record = {
            "OMNIARegion": region,
            "CoverageBasis": (
                "effective_single_country"
                if region in EFFECTIVE_SINGLE_COUNTRY_REGIONS
                else "complete_shared_mapping"
            ),
            "Countries": "; ".join(group["SourceCountry"]),
            "CountriesWithAnyZero": "; ".join(any_zero),
        }
        for year in SOURCE_YEARS:
            record[f"Observed{year}_kt"] = group[year].sum()
        records.append(record)
    observations = pd.DataFrame(records)
    if set(observations["OMNIARegion"]) != eligible_regions:
        raise ValueError("Observation aggregates do not match eligible regions")
    return observations


def build_rebased_projection(
    original: pd.DataFrame,
    observations: pd.DataFrame,
    source_sha256: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Interpolate 2020, insert 2021-2025 history, and rebase the future."""
    rebased = original.copy()
    audit_records = []

    missing_regions = sorted(
        set(observations["OMNIARegion"]) - set(original["OMNIARegion"])
    )
    if missing_regions:
        raise ValueError(f"Eligible regions missing from projection: {missing_regions}")

    for observation in observations.itertuples(index=False):
        region = observation.OMNIARegion
        index = rebased.index[rebased["OMNIARegion"].eq(region)][0]
        old_2019 = float(original.at[index, "2019"])
        old_2025 = float(original.at[index, "2025"])
        if old_2025 <= 0:
            raise ValueError(f"Cannot rebase {region} from non-positive 2025 value")

        observed_2021 = float(observation.Observed2021_kt)
        interpolated_2020 = (old_2019 + observed_2021) / 2.0
        scale_factor = float(observation.Observed2025_kt) / old_2025

        rebased.at[index, "2019"] = old_2019
        rebased.at[index, "2020"] = interpolated_2020
        for year in SOURCE_YEARS:
            rebased.at[index, str(year)] = float(
                getattr(observation, f"Observed{year}_kt")
            )
        for year in range(LAST_OBSERVED_YEAR + 1, END_YEAR + 1):
            rebased.at[index, str(year)] = (
                float(original.at[index, str(year)]) * scale_factor
            )

        audit = {
            "OMNIARegion": region,
            "CoverageBasis": observation.CoverageBasis,
            "Countries": observation.Countries,
            "CountriesWithAnyZero": observation.CountriesWithAnyZero,
            "Original2019_kt": old_2019,
            "Rebased2019_kt": float(rebased.at[index, "2019"]),
            "Original2020_kt": float(original.at[index, "2020"]),
            "Interpolated2020_kt": interpolated_2020,
            "InterpolationMethod2020": "midpoint of old 2019 and observed 2021",
        }
        for year in SOURCE_YEARS:
            original_value = float(original.at[index, str(year)])
            observed_value = float(getattr(observation, f"Observed{year}_kt"))
            audit[f"Original{year}_kt"] = original_value
            audit[f"Observed{year}_kt"] = observed_value
            audit[f"Delta{year}_kt"] = observed_value - original_value
        audit.update(
            {
                "Post2025ScaleFactor": scale_factor,
                "Original2050_kt": float(original.at[index, "2050"]),
                "Rebased2050_kt": float(rebased.at[index, "2050"]),
                "SourceSheet": SOURCE_SHEET,
                "SourceUnit": SOURCE_UNIT,
                "SourceLastUpdated": SOURCE_LAST_UPDATED,
                "SourceWorkbookSHA256": source_sha256,
            }
        )
        audit_records.append(audit)
    return rebased, pd.DataFrame(audit_records)


def validate_rebase(
    original: pd.DataFrame,
    rebased: pd.DataFrame,
    observations: pd.DataFrame,
) -> None:
    """Validate interpolation, observations, and preservation invariants."""
    if original["OMNIARegion"].tolist() != rebased["OMNIARegion"].tolist():
        raise ValueError("OMNIA region order changed during rebasing")

    eligible = set(observations["OMNIARegion"])
    ineligible_mask = ~original["OMNIARegion"].isin(eligible)
    if not np.array_equal(
        original.loc[ineligible_mask, YEAR_COLUMNS].to_numpy(),
        rebased.loc[ineligible_mask, YEAR_COLUMNS].to_numpy(),
    ):
        raise ValueError("An ineligible OMNIA region changed during rebasing")
    if not np.array_equal(original["2019"].to_numpy(), rebased["2019"].to_numpy()):
        raise ValueError("A 2019 production value changed during rebasing")

    original_by_region = original.set_index("OMNIARegion")
    rebased_by_region = rebased.set_index("OMNIARegion")
    observations_by_region = observations.set_index("OMNIARegion")
    future_years = [str(year) for year in range(2026, END_YEAR + 1)]

    for region in eligible:
        expected_2020 = (
            original_by_region.at[region, "2019"]
            + observations_by_region.at[region, "Observed2021_kt"]
        ) / 2.0
        if not np.isclose(
            rebased_by_region.at[region, "2020"],
            expected_2020,
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError(f"Incorrect interpolated 2020 value for {region}")

        for year in SOURCE_YEARS:
            actual = rebased_by_region.at[region, str(year)]
            expected = observations_by_region.at[region, f"Observed{year}_kt"]
            if not np.isclose(actual, expected, rtol=0.0, atol=1e-9):
                raise ValueError(
                    f"Rebased {region} {year} is {actual}; expected {expected} kt"
                )

        original_shape = (
            original_by_region.loc[region, future_years]
            / original_by_region.at[region, "2025"]
        )
        rebased_shape = (
            rebased_by_region.loc[region, future_years]
            / rebased_by_region.at[region, "2025"]
        )
        if not np.allclose(
            original_shape.to_numpy(dtype=float),
            rebased_shape.to_numpy(dtype=float),
            rtol=1e-12,
            atol=1e-12,
        ):
            raise ValueError(f"Post-2025 projection shape changed for {region}")

    values = rebased[YEAR_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Rebased output contains invalid numeric values")


def main() -> None:
    source, world, source_sha256 = read_source_data()
    mapping, eligible_regions = read_country_map(source)
    original = read_projection()
    observations = make_observations(source, mapping, eligible_regions)
    rebased, audit = build_rebased_projection(
        original, observations, source_sha256
    )
    validate_rebase(original, rebased, observations)
    growth = calculate_growth_rates(rebased)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    rebased.to_csv(OUTPUT_PROJECTION_CSV, index=False)
    growth.to_csv(OUTPUT_GROWTH_CSV, index=False)
    audit.to_csv(OUTPUT_AUDIT_CSV, index=False)

    print(f"Saved: {OUTPUT_PROJECTION_CSV}")
    print(f"Saved: {OUTPUT_GROWTH_CSV}")
    print(f"Saved: {OUTPUT_AUDIT_CSV}")
    print(f"World Steel source SHA-256: {source_sha256}")
    print(f"Rebased OMNIA regions: {len(observations)}")
    for year in (2019, 2020, 2021, 2025, END_YEAR):
        original_total = original[str(year)].sum() / 1000.0
        rebased_total = rebased[str(year)].sum() / 1000.0
        print(
            f"Global OMNIA total {year}: {original_total:.3f} -> "
            f"{rebased_total:.3f} Mt"
        )
    print(
        "World Steel source total 2025: "
        f"{float(world[2025]) / 1000.0:.3f} Mt"
    )


if __name__ == "__main__":
    main()
