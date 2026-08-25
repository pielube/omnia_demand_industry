"""Index OMNIA steel production from its 2019 level using World Steel data.

This workflow creates a separate projection variant.  It never modifies the
original OMNIA production projection or the upstream Excel workbook.

For each OMNIA region ``r`` the requested calculation is::

    new[r, 2019] = original[r, 2019]
    new[r, y] = original[r, 2019] * WSA[r, y] / WSA[r, 2019]
        for y = 2020, ..., 2025
    new[r, y] = new[r, 2025] * original[r, y] / original[r, 2025]
        for y = 2026, ..., 2050

The WSA aggregates use one fixed country basket in every year from 2019 to
2025.  A country is in the basket only when it is mapped in both source
vintages and has reported 2019 and 2020 values.  This prevents changing source
coverage from being interpreted as production growth.
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

HISTORICAL_SOURCE_CSV = (
    INPUTS_DIR / "worldsteel_crude_steel_production_2019_2020.csv"
)
HISTORICAL_SOURCE_PDF = INPUTS_DIR / "Steel-Statistical-Yearbook-2021.pdf"
HISTORICAL_MAP_CSV = (
    MAPS_DIR / "worldsteel_2019_2020_country_map.csv"
)
RECENT_SOURCE_XLSX = (
    INPUTS_DIR / "worldsteel_crude_steel_production_2021_2025.xlsx"
)
RECENT_MAP_CSV = MAPS_DIR / "worldsteel_2021_2025_country_map.csv"
OMNIA_MAPPING_CSV = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"

INPUT_PROJECTION_CSV = OUTPUTS_DIR / "steel_production_omnia.csv"
OUTPUT_PROJECTION_CSV = (
    OUTPUTS_DIR / "steel_production_omnia_2019_anchored_worldsteel_indexed.csv"
)
OUTPUT_GROWTH_CSV = (
    OUTPUTS_DIR
    / "steel_production_omnia_2019_anchored_worldsteel_indexed_growth_rates.csv"
)
OUTPUT_AUDIT_CSV = (
    OUTPUTS_DIR
    / "steel_production_omnia_2019_anchored_worldsteel_indexed_audit.csv"
)

RECENT_SOURCE_SHEET = "P1_crude_steel_total_pub"
RECENT_SOURCE_TITLE = "Total production of crude steel"
RECENT_SOURCE_LAST_UPDATED = "28 July 2026"
EXPECTED_RECENT_SOURCE_SHA256 = (
    "743a06460abf0720b8562b098fab8a18376a9d3e9cdc42bef77f07934fc3fa16"
)
EXPECTED_RECENT_MAP_SHA256 = (
    "5dee682785725cb5d728ee38f0900e3966986631f4982183c240e3012959a4e9"
)
EXPECTED_RECENT_SOURCE_DATA_ROWS = 125
EXPECTED_RECENT_COUNTRIES = 120
EXCLUDED_RECENT_ROWS = {
    "Belgium-Luxemburg",
    "Former Yugoslavia",
    "Serbia-Montenegro",
}

BASE_YEAR = 2019
HISTORICAL_YEARS = list(range(2019, 2026))
INDEXED_YEARS = list(range(2020, 2026))
RECENT_YEARS = list(range(2021, 2026))
FUTURE_ANCHOR_YEAR = 2025
FIRST_PROJECTED_YEAR = 2026
END_YEAR = 2050
YEAR_COLUMNS = [str(year) for year in range(BASE_YEAR, END_YEAR + 1)]
EXPECTED_OMNIA_REGION_COUNT = 28
EXPECTED_FIXED_BASKET_COUNTRIES = 87
LARGE_ANNUAL_CHANGE_THRESHOLD_PCT = 10.0

EXPECTED_HISTORICAL_SOURCE_SHA256 = (
    "efcb4a17eedf48546f1a2bebc751aea74741b30f31d6d84aa39398b2d7e92b0e"
)
EXPECTED_HISTORICAL_MAP_SHA256 = (
    "454b4b8a0029133e5b6a9c24ed7ddaafa087d31f97dab2004e54096581184b3b"
)
EXPECTED_HISTORICAL_PDF_SHA256 = (
    "e51e1919fbf694c8a40189c3d653e836ac9895161b6ab31ee8cd64b158998c36"
)
EXPECTED_HISTORICAL_SOURCE_ROWS = 94
EXPECTED_HISTORICAL_REPORTED_ROWS = 91
HISTORICAL_PUBLISHED_WORLD_KT = {2019: 1_875_330.0, 2020: 1_880_445.0}
HISTORICAL_WORLD_TOLERANCE_KT = 1.0
HISTORICAL_SOURCE_DOCUMENT = "Steel Statistical Yearbook 2021"
HISTORICAL_SOURCE_TABLE = "Table 1: Total Production of Crude Steel"
HISTORICAL_SOURCE_PAGES = "printed pages 1-2; PDF pages 5-6"
HISTORICAL_SOURCE_UNIT = "thousand metric tonnes (kt) crude steel"
HISTORICAL_CONTENTS_FINALISED = "November 2021"

COUNTRY_BASKET_METHOD = (
    "fixed ISO3 intersection of the 2019-2020 and 2021-2025 World Steel "
    "sources, restricted to countries reported in both 2019 and 2020"
)


def file_sha256(path: Path) -> str:
    """Return the hexadecimal SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_yes_no(series: pd.Series, column: str) -> pd.Series:
    """Validate and normalise a yes/no source flag."""
    result = series.astype(str).str.strip().str.lower()
    invalid = ~result.isin({"yes", "no"})
    if invalid.any():
        values = sorted(result.loc[invalid].unique().tolist())
        raise ValueError(f"Unexpected values in {column}: {values}")
    return result


def read_historical_source() -> tuple[pd.DataFrame, str]:
    """Read and validate the reviewed World Steel 2019-2020 extraction."""
    if not HISTORICAL_SOURCE_CSV.is_file():
        raise FileNotFoundError(
            "Missing World Steel 2019-2020 source extraction: "
            f"{HISTORICAL_SOURCE_CSV}"
        )

    source_sha256 = file_sha256(HISTORICAL_SOURCE_CSV)
    if source_sha256 != EXPECTED_HISTORICAL_SOURCE_SHA256:
        raise ValueError(
            "World Steel 2019-2020 source hash does not match the reviewed "
            f"extraction: {source_sha256}"
        )
    if not HISTORICAL_SOURCE_PDF.is_file():
        raise FileNotFoundError(
            f"Missing archived World Steel source PDF: {HISTORICAL_SOURCE_PDF}"
        )
    pdf_sha256 = file_sha256(HISTORICAL_SOURCE_PDF)
    if pdf_sha256 != EXPECTED_HISTORICAL_PDF_SHA256:
        raise ValueError(
            "World Steel 2021 yearbook hash does not match the reviewed PDF: "
            f"{pdf_sha256}"
        )

    source = pd.read_csv(
        HISTORICAL_SOURCE_CSV,
        dtype={"SourceGroup": str, "SourceCountry": str},
        keep_default_na=False,
    )
    required = {
        "SourceGroup",
        "SourceCountry",
        "Production2019_kt",
        "Production2020_kt",
        "Availability2019",
        "Availability2020",
        "CountrySeriesEstimated",
        "ValueEstimated2019",
        "ValueEstimated2020",
    }
    missing = required - set(source.columns)
    if missing:
        raise ValueError(
            "World Steel 2019-2020 source is missing columns: "
            f"{sorted(missing)}"
        )
    if len(source) != EXPECTED_HISTORICAL_SOURCE_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_HISTORICAL_SOURCE_ROWS} historical rows, "
            f"found {len(source)}"
        )
    if source["SourceCountry"].eq("").any():
        raise ValueError("World Steel 2019-2020 source contains a blank country")
    if source["SourceCountry"].duplicated().any():
        duplicates = source.loc[
            source["SourceCountry"].duplicated(keep=False), "SourceCountry"
        ].tolist()
        raise ValueError(f"Duplicate historical source countries: {duplicates}")

    for year in (2019, 2020):
        availability_column = f"Availability{year}"
        value_column = f"Production{year}_kt"
        estimate_column = f"ValueEstimated{year}"

        source[availability_column] = (
            source[availability_column].astype(str).str.strip().str.lower()
        )
        invalid_availability = ~source[availability_column].isin(
            {"reported", "unavailable"}
        )
        if invalid_availability.any():
            values = sorted(
                source.loc[invalid_availability, availability_column]
                .unique()
                .tolist()
            )
            raise ValueError(
                f"Unexpected values in {availability_column}: {values}"
            )

        source[value_column] = pd.to_numeric(
            source[value_column].replace("", np.nan), errors="raise"
        )
        reported = source[availability_column].eq("reported")
        if int(reported.sum()) != EXPECTED_HISTORICAL_REPORTED_ROWS:
            raise ValueError(
                f"Expected {EXPECTED_HISTORICAL_REPORTED_ROWS} reported "
                f"countries in {year}, found {int(reported.sum())}"
            )
        if source.loc[reported, value_column].isna().any():
            countries = source.loc[
                reported & source[value_column].isna(), "SourceCountry"
            ].tolist()
            raise ValueError(
                f"Reported {year} values are missing for countries: {countries}"
            )
        reported_values = source.loc[reported, value_column].to_numpy(dtype=float)
        if not np.isfinite(reported_values).all() or (reported_values < 0).any():
            raise ValueError(f"Reported World Steel {year} values are invalid")
        country_total = float(reported_values.sum())
        published_world = HISTORICAL_PUBLISHED_WORLD_KT[year]
        if not np.isclose(
            country_total,
            published_world,
            rtol=0.0,
            atol=HISTORICAL_WORLD_TOLERANCE_KT,
        ):
            raise ValueError(
                f"Historical country total does not reconcile to the "
                f"published World row in {year}: {country_total} vs "
                f"{published_world} kt"
            )

        source[estimate_column] = normalise_yes_no(
            source[estimate_column], estimate_column
        )

    source["CountrySeriesEstimated"] = normalise_yes_no(
        source["CountrySeriesEstimated"], "CountrySeriesEstimated"
    )
    return source, source_sha256


def read_recent_source() -> tuple[pd.DataFrame, pd.Series, str]:
    """Read and validate the World Steel 2021-2025 Excel export."""
    if not RECENT_SOURCE_XLSX.is_file():
        raise FileNotFoundError(f"Missing World Steel source: {RECENT_SOURCE_XLSX}")
    source_sha256 = file_sha256(RECENT_SOURCE_XLSX)
    if source_sha256 != EXPECTED_RECENT_SOURCE_SHA256:
        raise ValueError(
            "World Steel 2021-2025 source hash does not match the reviewed "
            f"export: {source_sha256}"
        )

    title = pd.read_excel(
        RECENT_SOURCE_XLSX,
        sheet_name=RECENT_SOURCE_SHEET,
        header=None,
        nrows=1,
        usecols="A",
    ).iloc[0, 0]
    if title != RECENT_SOURCE_TITLE:
        raise ValueError(f"Unexpected World Steel source title: {title!r}")

    raw = pd.read_excel(
        RECENT_SOURCE_XLSX,
        sheet_name=RECENT_SOURCE_SHEET,
        header=2,
        usecols="A:F",
    )
    expected_columns = ["Country", *RECENT_YEARS]
    if raw.columns.tolist() != expected_columns:
        raise ValueError(f"Unexpected World Steel columns: {raw.columns.tolist()}")

    # The copyright glyph is decoded differently by some Excel engines, so
    # identify the invariant organisation text instead of that one character.
    copyright_rows = raw.index[
        raw["Country"]
        .astype(str)
        .str.contains("World Steel Association", regex=False, na=False)
    ]
    if len(copyright_rows) != 1:
        raise ValueError("Could not identify the World Steel copyright row")
    data = raw.loc[raw.index < copyright_rows[0]].dropna(subset=["Country"]).copy()
    if len(data) != EXPECTED_RECENT_SOURCE_DATA_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_RECENT_SOURCE_DATA_ROWS} source rows, "
            f"found {len(data)}"
        )
    if data["Country"].duplicated().any():
        duplicates = data.loc[
            data["Country"].duplicated(keep=False), "Country"
        ].tolist()
        raise ValueError(f"Duplicate recent source countries: {duplicates}")

    for year in RECENT_YEARS:
        data[year] = pd.to_numeric(data[year], errors="raise")
    source_values = data[RECENT_YEARS].to_numpy(dtype=float)
    if not np.isfinite(source_values).all() or (source_values < 0).any():
        raise ValueError("World Steel 2021-2025 source has invalid values")

    world = data.loc[data["Country"].eq("World")]
    others = data.loc[data["Country"].eq("Others")]
    if len(world) != 1 or len(others) != 1:
        raise ValueError("Recent source must contain one World and one Others row")
    world = world.iloc[0]
    others = others.iloc[0]

    legacy = data[data["Country"].isin(EXCLUDED_RECENT_ROWS)]
    if set(legacy["Country"]) != EXCLUDED_RECENT_ROWS:
        raise ValueError("Missing all-zero legacy rows from recent source")
    if not legacy[RECENT_YEARS].eq(0).all(axis=None):
        raise ValueError("A legacy World Steel aggregate is no longer all-zero")

    countries = data.loc[
        ~data["Country"].isin({"World", "Others", *EXCLUDED_RECENT_ROWS})
    ].copy()
    if len(countries) != EXPECTED_RECENT_COUNTRIES:
        raise ValueError(
            f"Expected {EXPECTED_RECENT_COUNTRIES} recent countries, "
            f"found {len(countries)}"
        )
    for year in RECENT_YEARS:
        reconstructed = countries[year].sum() + others[year]
        if not np.isclose(reconstructed, world[year], rtol=0.0, atol=1e-5):
            raise ValueError(
                f"Named countries plus Others do not equal World in {year}: "
                f"{reconstructed} vs {world[year]} kt"
            )

    metadata = pd.read_excel(
        RECENT_SOURCE_XLSX,
        sheet_name=RECENT_SOURCE_SHEET,
        header=None,
        usecols="A:B",
    )
    last_updated_rows = metadata.index[metadata.iloc[:, 0].eq("Last updated:")]
    if len(last_updated_rows) != 1:
        raise ValueError("Could not identify source last-updated metadata")
    last_updated = str(metadata.iloc[last_updated_rows[0], 1])
    if last_updated != RECENT_SOURCE_LAST_UPDATED:
        raise ValueError(f"Unexpected last-updated value: {last_updated!r}")

    return countries, world, source_sha256


def read_source_map(path: Path, source_names: set[str], label: str) -> pd.DataFrame:
    """Read a source-name map and validate it against its source rows."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label} country map: {path}")
    mapping = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"SourceCountry", "ISO3", "OMNIARegion"}
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"{label} map is missing columns: {sorted(missing)}")
    for column in ("SourceCountry", "ISO3"):
        if mapping[column].eq("").any() or mapping[column].duplicated().any():
            bad = mapping.loc[
                mapping[column].eq("")
                | mapping[column].duplicated(keep=False),
                column,
            ].tolist()
            raise ValueError(f"Invalid {column} values in {label} map: {bad}")

    mapped_names = set(mapping["SourceCountry"])
    if mapped_names != source_names:
        raise ValueError(
            f"{label} source/map mismatch. Missing from map: "
            f"{sorted(source_names - mapped_names)}; extra in map: "
            f"{sorted(mapped_names - source_names)}"
        )
    return mapping


def read_shared_map() -> pd.DataFrame:
    """Read the authoritative ISO3-to-OMNIA-region map."""
    shared = pd.read_csv(OMNIA_MAPPING_CSV, dtype=str, keep_default_na=False)
    required = {"ISO3", "region"}
    missing = required - set(shared.columns)
    if missing:
        raise ValueError(f"Shared OMNIA map is missing columns: {sorted(missing)}")
    # Some ISO3 codes have multiple country-name aliases in the shared file;
    # only an ISO3 assigned to multiple *regions* is ambiguous here.
    shared = shared[["ISO3", "region"]].drop_duplicates()
    ambiguous = shared["ISO3"].duplicated(keep=False)
    if ambiguous.any():
        bad = shared.loc[ambiguous].to_dict("records")
        raise ValueError(f"ISO3 codes map to multiple OMNIA regions: {bad}")
    return shared


def validate_map_against_shared(
    mapping: pd.DataFrame,
    shared: pd.DataFrame,
    label: str,
) -> None:
    """Require every source ISO3/region pair to agree with the shared map."""
    checked = mapping[["ISO3", "OMNIARegion"]].merge(
        shared[["ISO3", "region"]], on="ISO3", how="left", validate="one_to_one"
    )
    missing = checked["region"].isna() | checked["region"].eq("")
    if missing.any():
        raise ValueError(
            f"{label} ISO3 codes missing from shared map: "
            f"{checked.loc[missing, 'ISO3'].tolist()}"
        )
    mismatch = checked["OMNIARegion"].ne(checked["region"])
    if mismatch.any():
        bad = checked.loc[
            mismatch, ["ISO3", "OMNIARegion", "region"]
        ].to_dict("records")
        raise ValueError(f"{label} and shared mappings disagree: {bad}")


def build_fixed_country_panel(
    historical: pd.DataFrame,
    recent: pd.DataFrame,
    historical_map: pd.DataFrame,
    recent_map: pd.DataFrame,
    shared: pd.DataFrame,
) -> pd.DataFrame:
    """Create the one country cohort used in every regional WSA ratio."""
    old = historical_map[["SourceCountry", "ISO3", "OMNIARegion"]].merge(
        historical,
        on="SourceCountry",
        how="left",
        validate="one_to_one",
    )
    old = old.rename(
        columns={
            "SourceCountry": "SourceCountry2019_2020",
            "OMNIARegion": "OMNIARegion2019_2020",
        }
    )

    new = recent_map[["SourceCountry", "ISO3", "OMNIARegion"]].merge(
        recent,
        left_on="SourceCountry",
        right_on="Country",
        how="left",
        validate="one_to_one",
    )
    new = new.rename(
        columns={
            "SourceCountry": "SourceCountry2021_2025",
            "OMNIARegion": "OMNIARegion2021_2025",
        }
    )

    panel = old.merge(new, on="ISO3", how="inner", validate="one_to_one")
    region_mismatch = panel["OMNIARegion2019_2020"].ne(
        panel["OMNIARegion2021_2025"]
    )
    if region_mismatch.any():
        bad = panel.loc[
            region_mismatch,
            [
                "ISO3",
                "OMNIARegion2019_2020",
                "OMNIARegion2021_2025",
            ],
        ].to_dict("records")
        raise ValueError(f"World Steel maps disagree across vintages: {bad}")

    panel = panel.loc[
        panel["Availability2019"].eq("reported")
        & panel["Availability2020"].eq("reported")
    ].copy()
    panel["OMNIARegion"] = panel["OMNIARegion2019_2020"]
    panel = panel.sort_values(["OMNIARegion", "ISO3"]).reset_index(drop=True)
    if panel.empty:
        raise ValueError("The fixed World Steel country basket is empty")
    if len(panel) != EXPECTED_FIXED_BASKET_COUNTRIES:
        raise ValueError(
            f"Expected {EXPECTED_FIXED_BASKET_COUNTRIES} countries in the "
            f"reviewed fixed basket, found {len(panel)}"
        )

    shared_lookup = shared.set_index("ISO3")["region"]
    expected_regions = panel["ISO3"].map(shared_lookup)
    if expected_regions.isna().any() or not expected_regions.eq(
        panel["OMNIARegion"]
    ).all():
        raise ValueError("Fixed country basket conflicts with the shared map")
    return panel


def join_items(values: pd.Series) -> str:
    """Join unique, nonblank strings in deterministic order."""
    items = sorted({str(value) for value in values if str(value)})
    return "; ".join(items)


def make_regional_observations(
    panel: pd.DataFrame,
    shared: pd.DataFrame,
    historical: pd.DataFrame,
    recent: pd.DataFrame,
    historical_map: pd.DataFrame,
    recent_map: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate the fixed country panel and attach coverage diagnostics."""
    shared_members = {
        region: set(group["ISO3"])
        for region, group in shared.groupby("region", sort=True)
    }
    historical_coverage = historical_map.merge(
        historical[
            [
                "SourceCountry",
                "Production2019_kt",
                "Availability2019",
                "Availability2020",
            ]
        ],
        on="SourceCountry",
        how="left",
        validate="one_to_one",
    )
    recent_coverage = recent_map.merge(
        recent[["Country", 2025]],
        left_on="SourceCountry",
        right_on="Country",
        how="left",
        validate="one_to_one",
    )
    historical_members = set(historical_map["ISO3"])
    recent_members = set(recent_map["ISO3"])
    unavailable_2019 = set(
        historical_coverage.loc[
            historical_coverage["Availability2019"].eq("unavailable"), "ISO3"
        ]
    )
    unavailable_2020 = set(
        historical_coverage.loc[
            historical_coverage["Availability2020"].eq("unavailable"), "ISO3"
        ]
    )
    records: list[dict[str, object]] = []

    for region, group in panel.groupby("OMNIARegion", sort=True):
        basket_members = set(group["ISO3"])
        all_shared_members = shared_members[region]
        missing_members = sorted(all_shared_members - basket_members)
        country_share = len(basket_members) / len(all_shared_members)

        historical_region = historical_coverage.loc[
            historical_coverage["OMNIARegion"].eq(region)
            & historical_coverage["Availability2019"].eq("reported")
        ]
        historical_reported_2019 = float(
            historical_region["Production2019_kt"].sum()
        )
        basket_2019 = float(group["Production2019_kt"].sum())
        historical_production_coverage = (
            basket_2019 / historical_reported_2019
            if historical_reported_2019 > 0
            else np.nan
        )

        recent_region = recent_coverage.loc[
            recent_coverage["OMNIARegion"].eq(region)
        ]
        recent_mapped_2025 = float(recent_region[2025].sum())
        basket_2025 = float(group[2025].sum())
        recent_production_coverage = (
            basket_2025 / recent_mapped_2025
            if recent_mapped_2025 > 0
            else np.nan
        )
        production_coverages = [
            value
            for value in (
                historical_production_coverage,
                recent_production_coverage,
            )
            if np.isfinite(value)
        ]
        minimum_production_coverage = (
            min(production_coverages) if production_coverages else np.nan
        )

        if region == "CHN":
            coverage_basis = "effective_mainland_china"
        elif basket_members == all_shared_members:
            coverage_basis = "complete_shared_mapping"
        else:
            coverage_basis = "fixed_partial_common_country_basket"

        low_country_count_coverage = country_share < 0.25
        any_estimate = group[
            [
                "CountrySeriesEstimated",
                "ValueEstimated2019",
                "ValueEstimated2020",
            ]
        ].eq("yes").any(axis=None)
        if not np.isfinite(minimum_production_coverage):
            confidence_flag = "unassessed_production_coverage"
        elif minimum_production_coverage < 0.75:
            confidence_flag = "low_production_coverage"
        elif minimum_production_coverage < 0.95:
            confidence_flag = "qualified_partial_production_coverage"
        elif any_estimate:
            confidence_flag = "qualified_estimated_source"
        else:
            confidence_flag = "high_production_coverage"

        record: dict[str, object] = {
            "OMNIARegion": region,
            "RebaseApplied": "yes",
            "ExclusionReason": "",
            "CountryBasketMethod": COUNTRY_BASKET_METHOD,
            "CoverageBasis": coverage_basis,
            "BasketCountryCount": len(group),
            "SharedMappingCountryCount": len(all_shared_members),
            "BasketCountryShare": country_share,
            "LowCountryCountCoverageFlag": (
                "yes" if low_country_count_coverage else "no"
            ),
            "HistoricalReportedRegional2019_kt": historical_reported_2019,
            "BasketShareOfReportedHistorical2019Production": (
                historical_production_coverage
            ),
            "RecentMappedRegional2025_kt": recent_mapped_2025,
            "BasketShareOfMappedRecent2025Production": recent_production_coverage,
            "MinimumProductionCoverage": minimum_production_coverage,
            "LowProductionCoverageFlag": (
                "yes"
                if np.isfinite(minimum_production_coverage)
                and minimum_production_coverage < 0.75
                else "no"
            ),
            "SourceEstimateFlag": "yes" if any_estimate else "no",
            "ConfidenceFlag": confidence_flag,
            "BasketISO3": join_items(group["ISO3"]),
            "BasketCountries": join_items(group["SourceCountry2019_2020"]),
            "ExcludedSharedISO3": "; ".join(missing_members),
            "AbsentFrom2019_2020SourceISO3": "; ".join(
                sorted(all_shared_members - historical_members)
            ),
            "AbsentFrom2021_2025SourceISO3": "; ".join(
                sorted(all_shared_members - recent_members)
            ),
            "Unavailable2019ISO3": "; ".join(
                sorted(all_shared_members & unavailable_2019)
            ),
            "Unavailable2020ISO3": "; ".join(
                sorted(all_shared_members & unavailable_2020)
            ),
            "EstimatedCountrySeries": join_items(
                group.loc[
                    group["CountrySeriesEstimated"].eq("yes"),
                    "SourceCountry2019_2020",
                ]
            ),
            "EstimatedValues2019": join_items(
                group.loc[
                    group["ValueEstimated2019"].eq("yes"),
                    "SourceCountry2019_2020",
                ]
            ),
            "EstimatedValues2020": join_items(
                group.loc[
                    group["ValueEstimated2020"].eq("yes"),
                    "SourceCountry2019_2020",
                ]
            ),
        }

        source_columns = {
            2019: "Production2019_kt",
            2020: "Production2020_kt",
            **{year: year for year in RECENT_YEARS},
        }
        for year, column in source_columns.items():
            value = float(group[column].sum())
            record[f"WSA{year}_kt"] = value
            record[f"ZeroValueCountries{year}"] = join_items(
                group.loc[
                    group[column].eq(0), "SourceCountry2019_2020"
                ]
            )

        record["AnyZeroObservationFlag"] = (
            "yes"
            if any(
                bool(record[f"ZeroValueCountries{year}"])
                for year in HISTORICAL_YEARS
            )
            else "no"
        )

        denominator = float(record["WSA2019_kt"])
        if not np.isfinite(denominator) or denominator <= 0:
            record["RebaseApplied"] = "no"
            record["ExclusionReason"] = "non-positive fixed-basket WSA 2019"
            for year in HISTORICAL_YEARS:
                record[f"WSAIndex{year}"] = np.nan
        else:
            for year in HISTORICAL_YEARS:
                record[f"WSAIndex{year}"] = (
                    float(record[f"WSA{year}_kt"]) / denominator
                )
        records.append(record)

    observations = pd.DataFrame(records)
    coverage_columns = [
        "BasketShareOfReportedHistorical2019Production",
        "BasketShareOfMappedRecent2025Production",
    ]
    coverage_values = observations[coverage_columns].to_numpy(dtype=float)
    invalid_coverage = (
        ~np.isfinite(coverage_values)
        | (coverage_values < 0)
        | (coverage_values > 1 + 1e-12)
    )
    if invalid_coverage.any():
        raise ValueError("Invalid production-weighted country-basket coverage")
    return observations


def read_projection() -> pd.DataFrame:
    """Read and validate the original OMNIA steel-production projection."""
    projection = pd.read_csv(INPUT_PROJECTION_CSV)
    required = ["OMNIARegion", *YEAR_COLUMNS]
    if projection.columns.tolist() != required:
        raise ValueError(
            "Steel projection columns do not match the expected layout: "
            f"{projection.columns.tolist()}"
        )
    if len(projection) != EXPECTED_OMNIA_REGION_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_OMNIA_REGION_COUNT} OMNIA regions, "
            f"found {len(projection)}"
        )
    if projection["OMNIARegion"].duplicated().any():
        raise ValueError("Original projection has duplicate OMNIA regions")
    projection[YEAR_COLUMNS] = projection[YEAR_COLUMNS].apply(
        pd.to_numeric, errors="raise"
    )
    values = projection[YEAR_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Original production projection has invalid values")
    return projection


def restore_original_2019_text(
    rebased: pd.DataFrame,
    original: pd.DataFrame,
) -> pd.DataFrame:
    """Preserve the original CSV's exact textual representation of 2019."""
    original_text = pd.read_csv(
        INPUT_PROJECTION_CSV, dtype=str, keep_default_na=False
    )
    if original_text["OMNIARegion"].tolist() != original["OMNIARegion"].tolist():
        raise ValueError("Original text and numeric projection region order differs")
    parsed_2019 = pd.to_numeric(original_text["2019"], errors="raise")
    if not np.array_equal(parsed_2019.to_numpy(), original["2019"].to_numpy()):
        raise ValueError("Could not preserve the exact original 2019 values")

    output = rebased.copy()
    output["2019"] = original_text["2019"]
    return output


def add_missing_region_audits(
    observations: pd.DataFrame,
    original: pd.DataFrame,
    shared: pd.DataFrame,
) -> pd.DataFrame:
    """Add explicit audit rows for any region with no fixed-basket data."""
    observed_regions = set(observations["OMNIARegion"])
    missing_regions = [
        region
        for region in original["OMNIARegion"]
        if region not in observed_regions
    ]
    if not missing_regions:
        return observations

    rows = []
    for region in missing_regions:
        rows.append(
            {
                "OMNIARegion": region,
                "RebaseApplied": "no",
                "ExclusionReason": "no fixed common World Steel country basket",
                "CountryBasketMethod": COUNTRY_BASKET_METHOD,
                "CoverageBasis": "no_common_country_coverage",
                "BasketCountryCount": 0,
                "SharedMappingCountryCount": int(shared["region"].eq(region).sum()),
                "BasketCountryShare": 0.0,
                "LowCountryCountCoverageFlag": "yes",
                "HistoricalReportedRegional2019_kt": np.nan,
                "BasketShareOfReportedHistorical2019Production": np.nan,
                "RecentMappedRegional2025_kt": np.nan,
                "BasketShareOfMappedRecent2025Production": np.nan,
                "MinimumProductionCoverage": np.nan,
                "LowProductionCoverageFlag": "unknown",
                "SourceEstimateFlag": "unknown",
                "ConfidenceFlag": "no_coverage",
                "AnyZeroObservationFlag": "unknown",
                "BasketISO3": "",
                "BasketCountries": "",
                "ExcludedSharedISO3": join_items(
                    shared.loc[shared["region"].eq(region), "ISO3"]
                ),
                "AbsentFrom2019_2020SourceISO3": "",
                "AbsentFrom2021_2025SourceISO3": "",
                "Unavailable2019ISO3": "",
                "Unavailable2020ISO3": "",
            }
        )
    return pd.concat([observations, pd.DataFrame(rows)], ignore_index=True)


def build_rebased_projection(
    original: pd.DataFrame,
    observations: pd.DataFrame,
    source_metadata: dict[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the WSA index history and the requested 2025 future anchor."""
    rebased = original.copy()
    observations_by_region = observations.set_index("OMNIARegion")
    audit_records: list[dict[str, object]] = []

    for index, original_row in original.iterrows():
        region = str(original_row["OMNIARegion"])
        observation = observations_by_region.loc[region]
        apply_rebase = observation["RebaseApplied"] == "yes"
        old_2019 = float(original_row["2019"])
        old_anchor = float(original_row[str(FUTURE_ANCHOR_YEAR)])

        if apply_rebase:
            if old_anchor <= 0:
                raise ValueError(
                    f"Cannot anchor {region} from non-positive original "
                    f"{FUTURE_ANCHOR_YEAR}"
                )
            rebased.at[index, "2019"] = old_2019
            for year in INDEXED_YEARS:
                rebased.at[index, str(year)] = (
                    old_2019 * float(observation[f"WSAIndex{year}"])
                )

            new_anchor = float(rebased.at[index, str(FUTURE_ANCHOR_YEAR)])
            future_scale = new_anchor / old_anchor
            for year in range(FIRST_PROJECTED_YEAR, END_YEAR + 1):
                rebased.at[index, str(year)] = (
                    new_anchor * float(original_row[str(year)]) / old_anchor
                )
        else:
            future_scale = 1.0

        audit = observation.to_dict()
        audit["OMNIARegion"] = region
        audit["Original2019_kt"] = old_2019
        for year in HISTORICAL_YEARS:
            audit[f"Rebased{year}_kt"] = float(rebased.at[index, str(year)])
            if year >= 2020:
                audit[f"Original{year}_kt"] = float(original_row[str(year)])
        audit["DerivedOMNIA2025_kt"] = float(rebased.at[index, "2025"])
        audit["FutureAnchorYear"] = FUTURE_ANCHOR_YEAR
        audit["Post2025ScaleFactor"] = future_scale
        audit["Original2026_kt"] = float(original_row["2026"])
        audit["Rebased2026_kt"] = float(rebased.at[index, "2026"])
        audit["Original2050_kt"] = float(original_row["2050"])
        audit["Rebased2050_kt"] = float(rebased.at[index, "2050"])
        value_2025 = float(rebased.at[index, "2025"])
        value_2026 = float(rebased.at[index, "2026"])
        transition_change = (
            (value_2026 / value_2025 - 1.0) * 100.0
            if value_2025 > 0
            else np.nan
        )
        original_2025 = float(original_row["2025"])
        original_2026 = float(original_row["2026"])
        original_transition_change = (
            (original_2026 / original_2025 - 1.0) * 100.0
            if original_2025 > 0
            else np.nan
        )
        audit["Rebased2025To2026Change_pct"] = transition_change
        audit["Original2025To2026Change_pct"] = original_transition_change
        audit["HandoffGrowthDifference_pp"] = (
            transition_change - original_transition_change
        )
        audit["Large2025To2026ChangeFlag"] = (
            "yes"
            if np.isfinite(transition_change)
            and abs(transition_change) >= LARGE_ANNUAL_CHANGE_THRESHOLD_PCT
            else "no"
        )
        audit["LargeAnnualChangeThreshold_pct"] = (
            LARGE_ANNUAL_CHANGE_THRESHOLD_PCT
        )
        audit["HistoricalFormula"] = (
            "OMNIA2019 * fixed-basket WSAy / fixed-basket WSA2019"
        )
        audit["FutureFormula"] = (
            "Rebased2025 * original_y / original_2025"
        )
        audit.update(source_metadata)
        audit_records.append(audit)

    return rebased, pd.DataFrame(audit_records)


def validate_rebase(
    original: pd.DataFrame,
    rebased: pd.DataFrame,
    audit: pd.DataFrame,
) -> None:
    """Validate the formulas, fixed base year, and projection invariants."""
    if original["OMNIARegion"].tolist() != rebased["OMNIARegion"].tolist():
        raise ValueError("OMNIA region order changed during rebasing")
    if original["OMNIARegion"].tolist() != audit["OMNIARegion"].tolist():
        raise ValueError("Audit region order does not match the projection")
    if not np.array_equal(original["2019"].to_numpy(), rebased["2019"].to_numpy()):
        raise ValueError("A 2019 OMNIA production value changed")

    original_by_region = original.set_index("OMNIARegion")
    rebased_by_region = rebased.set_index("OMNIARegion")
    audit_by_region = audit.set_index("OMNIARegion")
    future_years = [str(year) for year in range(FIRST_PROJECTED_YEAR, END_YEAR + 1)]

    for region in original_by_region.index:
        if audit_by_region.at[region, "RebaseApplied"] != "yes":
            if not np.array_equal(
                original_by_region.loc[region, YEAR_COLUMNS].to_numpy(dtype=float),
                rebased_by_region.loc[region, YEAR_COLUMNS].to_numpy(dtype=float),
            ):
                raise ValueError(f"Excluded region {region} changed")
            continue

        old_2019 = float(original_by_region.at[region, "2019"])
        for year in INDEXED_YEARS:
            expected = old_2019 * float(
                audit_by_region.at[region, f"WSAIndex{year}"]
            )
            actual = float(rebased_by_region.at[region, str(year)])
            if not np.isclose(actual, expected, rtol=1e-13, atol=1e-8):
                raise ValueError(
                    f"Incorrect indexed value for {region} {year}: "
                    f"{actual} vs {expected} kt"
                )

        expected_future = (
            float(rebased_by_region.at[region, "2025"])
            * original_by_region.loc[region, future_years]
            / float(original_by_region.at[region, "2025"])
        )
        if not np.allclose(
            rebased_by_region.loc[region, future_years].to_numpy(dtype=float),
            expected_future.to_numpy(dtype=float),
            rtol=1e-12,
            atol=1e-8,
        ):
            raise ValueError(f"Post-2025 projection shape changed for {region}")

        original_transition = (
            float(original_by_region.at[region, "2026"])
            / float(original_by_region.at[region, "2025"])
            - 1.0
        ) * 100.0
        rebased_transition = (
            float(rebased_by_region.at[region, "2026"])
            / float(rebased_by_region.at[region, "2025"])
            - 1.0
        ) * 100.0
        if not np.isclose(
            rebased_transition,
            original_transition,
            rtol=0.0,
            atol=1e-12,
        ):
            raise ValueError(
                f"2025-2026 growth changed for {region}: "
                f"{rebased_transition} vs {original_transition} percent"
            )
        audit_difference = float(
            audit_by_region.at[region, "HandoffGrowthDifference_pp"]
        )
        if not np.isclose(audit_difference, 0.0, rtol=0.0, atol=1e-12):
            raise ValueError(
                f"Audit reports a non-zero handoff difference for {region}: "
                f"{audit_difference} percentage points"
            )

    output_values = rebased[YEAR_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(output_values).all() or (output_values < 0).any():
        raise ValueError("Rebased output contains invalid values")


def order_audit_columns(audit: pd.DataFrame) -> pd.DataFrame:
    """Put calculation columns first while retaining all diagnostics."""
    preferred = [
        "OMNIARegion",
        "RebaseApplied",
        "ExclusionReason",
        "CountryBasketMethod",
        "CoverageBasis",
        "BasketCountryCount",
        "SharedMappingCountryCount",
        "BasketCountryShare",
        "LowCountryCountCoverageFlag",
        "HistoricalReportedRegional2019_kt",
        "BasketShareOfReportedHistorical2019Production",
        "RecentMappedRegional2025_kt",
        "BasketShareOfMappedRecent2025Production",
        "MinimumProductionCoverage",
        "LowProductionCoverageFlag",
        "SourceEstimateFlag",
        "AnyZeroObservationFlag",
        "ConfidenceFlag",
        "BasketISO3",
        "BasketCountries",
        "ExcludedSharedISO3",
        "AbsentFrom2019_2020SourceISO3",
        "AbsentFrom2021_2025SourceISO3",
        "Unavailable2019ISO3",
        "Unavailable2020ISO3",
        "EstimatedCountrySeries",
        "EstimatedValues2019",
        "EstimatedValues2020",
    ]
    for year in HISTORICAL_YEARS:
        preferred.extend(
            [
                f"WSA{year}_kt",
                f"WSAIndex{year}",
                f"ZeroValueCountries{year}",
            ]
        )
    preferred.append("Original2019_kt")
    for year in HISTORICAL_YEARS:
        preferred.append(f"Rebased{year}_kt")
        if year >= 2020:
            preferred.append(f"Original{year}_kt")
    preferred.extend(
        [
            "DerivedOMNIA2025_kt",
            "FutureAnchorYear",
            "Post2025ScaleFactor",
            "Original2026_kt",
            "Rebased2026_kt",
            "Original2050_kt",
            "Rebased2050_kt",
            "Rebased2025To2026Change_pct",
            "Original2025To2026Change_pct",
            "HandoffGrowthDifference_pp",
            "Large2025To2026ChangeFlag",
            "LargeAnnualChangeThreshold_pct",
            "HistoricalFormula",
            "FutureFormula",
            "HistoricalSourceCSV_SHA256",
            "HistoricalSourcePDF_SHA256",
            "HistoricalMapCSV_SHA256",
            "RecentSourceXLSX_SHA256",
            "RecentMapCSV_SHA256",
            "SharedMapCSV_SHA256",
            "OriginalProjectionCSV_SHA256",
            "HistoricalSourceDocument",
            "HistoricalSourceTable",
            "HistoricalSourcePages",
            "HistoricalSourceUnit",
            "HistoricalContentsFinalised",
            "HistoricalPublishedWorld2019_kt",
            "HistoricalExtractedCountrySum2019_kt",
            "HistoricalCountrySumDelta2019_kt",
            "HistoricalPublishedWorld2020_kt",
            "HistoricalExtractedCountrySum2020_kt",
            "HistoricalCountrySumDelta2020_kt",
            "RecentSourceSheet",
            "RecentSourceUnit",
            "RecentSourceLastUpdated",
        ]
    )
    existing_preferred = [column for column in preferred if column in audit.columns]
    remaining = [column for column in audit.columns if column not in preferred]
    return audit.loc[:, [*existing_preferred, *remaining]]


def main() -> None:
    historical, historical_hash = read_historical_source()
    recent, recent_world, recent_hash = read_recent_source()
    historical_map = read_source_map(
        HISTORICAL_MAP_CSV,
        set(historical["SourceCountry"]),
        "World Steel 2019-2020",
    )
    recent_map = read_source_map(
        RECENT_MAP_CSV,
        set(recent["Country"]),
        "World Steel 2021-2025",
    )
    historical_map_hash = file_sha256(HISTORICAL_MAP_CSV)
    if historical_map_hash != EXPECTED_HISTORICAL_MAP_SHA256:
        raise ValueError(
            "World Steel 2019-2020 map hash does not match the reviewed map: "
            f"{historical_map_hash}"
        )
    recent_map_hash = file_sha256(RECENT_MAP_CSV)
    if recent_map_hash != EXPECTED_RECENT_MAP_SHA256:
        raise ValueError(
            "World Steel 2021-2025 map hash does not match the reviewed map: "
            f"{recent_map_hash}"
        )
    shared = read_shared_map()
    validate_map_against_shared(historical_map, shared, "2019-2020 source")
    validate_map_against_shared(recent_map, shared, "2021-2025 source")

    panel = build_fixed_country_panel(
        historical, recent, historical_map, recent_map, shared
    )
    original = read_projection()
    observations = make_regional_observations(
        panel, shared, historical, recent, historical_map, recent_map
    )
    observations = add_missing_region_audits(observations, original, shared)

    observation_regions = set(observations["OMNIARegion"])
    projection_regions = set(original["OMNIARegion"])
    if observation_regions != projection_regions:
        raise ValueError(
            "WSA audit/projection region mismatch. Missing from audit: "
            f"{sorted(projection_regions - observation_regions)}; extra in "
            f"audit: {sorted(observation_regions - projection_regions)}"
        )
    unapplied = observations.loc[
        observations["RebaseApplied"].ne("yes"),
        ["OMNIARegion", "ExclusionReason"],
    ]
    if not unapplied.empty:
        raise ValueError(
            "The reviewed source is expected to rebase all 28 OMNIA regions; "
            f"unapplied rows: {unapplied.to_dict('records')}"
        )

    extracted_historical_totals = {
        year: float(historical[f"Production{year}_kt"].sum(skipna=True))
        for year in (2019, 2020)
    }

    source_metadata = {
        "HistoricalSourceCSV_SHA256": historical_hash,
        "HistoricalSourcePDF_SHA256": file_sha256(HISTORICAL_SOURCE_PDF),
        "HistoricalMapCSV_SHA256": historical_map_hash,
        "RecentSourceXLSX_SHA256": recent_hash,
        "RecentMapCSV_SHA256": recent_map_hash,
        "SharedMapCSV_SHA256": file_sha256(OMNIA_MAPPING_CSV),
        "OriginalProjectionCSV_SHA256": file_sha256(INPUT_PROJECTION_CSV),
        "HistoricalSourceDocument": HISTORICAL_SOURCE_DOCUMENT,
        "HistoricalSourceTable": HISTORICAL_SOURCE_TABLE,
        "HistoricalSourcePages": HISTORICAL_SOURCE_PAGES,
        "HistoricalSourceUnit": HISTORICAL_SOURCE_UNIT,
        "HistoricalContentsFinalised": HISTORICAL_CONTENTS_FINALISED,
        "HistoricalPublishedWorld2019_kt": HISTORICAL_PUBLISHED_WORLD_KT[2019],
        "HistoricalExtractedCountrySum2019_kt": extracted_historical_totals[2019],
        "HistoricalCountrySumDelta2019_kt": (
            extracted_historical_totals[2019]
            - HISTORICAL_PUBLISHED_WORLD_KT[2019]
        ),
        "HistoricalPublishedWorld2020_kt": HISTORICAL_PUBLISHED_WORLD_KT[2020],
        "HistoricalExtractedCountrySum2020_kt": extracted_historical_totals[2020],
        "HistoricalCountrySumDelta2020_kt": (
            extracted_historical_totals[2020]
            - HISTORICAL_PUBLISHED_WORLD_KT[2020]
        ),
        "RecentSourceSheet": RECENT_SOURCE_SHEET,
        "RecentSourceUnit": "kt crude steel",
        "RecentSourceLastUpdated": RECENT_SOURCE_LAST_UPDATED,
    }
    rebased, audit = build_rebased_projection(
        original, observations, source_metadata
    )
    validate_rebase(original, rebased, audit)
    growth = calculate_growth_rates(rebased)
    audit = order_audit_columns(audit)
    rebased_for_csv = restore_original_2019_text(rebased, original)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    # Seventeen significant digits preserve every input IEEE-754 value when
    # the CSV is read again, including the exact OMNIA 2019 anchors.
    rebased_for_csv.to_csv(
        OUTPUT_PROJECTION_CSV, index=False, float_format="%.17g"
    )
    growth.to_csv(OUTPUT_GROWTH_CSV, index=False, float_format="%.17g")
    audit.to_csv(OUTPUT_AUDIT_CSV, index=False, float_format="%.17g")

    print(f"Saved: {OUTPUT_PROJECTION_CSV}")
    print(f"Saved: {OUTPUT_GROWTH_CSV}")
    print(f"Saved: {OUTPUT_AUDIT_CSV}")
    print(f"Fixed World Steel country basket: {len(panel)} countries")
    print(
        "Rebased OMNIA regions: "
        f"{audit['RebaseApplied'].eq('yes').sum()} / {len(original)}"
    )
    for year in HISTORICAL_YEARS + [2026, END_YEAR]:
        old_total = original[str(year)].sum() / 1000.0
        new_total = rebased[str(year)].sum() / 1000.0
        print(f"Global total {year}: {old_total:.3f} -> {new_total:.3f} Mt")
    max_jump_index = audit["Rebased2025To2026Change_pct"].abs().idxmax()
    print(
        "Largest absolute 2025-2026 regional change: "
        f"{audit.at[max_jump_index, 'OMNIARegion']} "
        f"({audit.at[max_jump_index, 'Rebased2025To2026Change_pct']:.1f}%)"
    )
    print(
        "World Steel published total 2025 (reference only; not the fixed "
        f"basket): {float(recent_world[2025]) / 1000.0:.3f} Mt"
    )


if __name__ == "__main__":
    main()
