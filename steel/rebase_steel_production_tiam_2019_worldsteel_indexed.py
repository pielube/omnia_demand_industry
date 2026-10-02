"""Index TIAM steel production with the reviewed fixed World Steel basket.

Countries are regrouped into TIAM regions before calculating WSA indices.
The existing OMNIA workflow supplies validated country sources and pure math
and audit helpers. Those helpers temporarily use the column name OMNIARegion
as an adapter; its values are TIAM regions and exported columns use TIAM names.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import numpy as np
import pandas as pd


REPO_DIR = Path(__file__).resolve().parents[1]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from steel import rebase_steel_production_omnia_2019_worldsteel_indexed as wsa
from tiam_projection_utils import (
    MAPPING_CSV,
    SUPPLEMENTS_CSV,
    TIAM_REGIONS,
    YEARS,
    calculate_growth_rates,
    read_tiam_mapping,
    validate_mapping,
)


INPUT_PROJECTION_CSV = wsa.OUTPUTS_DIR / "steel_production_tiam.csv"
OUTPUT_PROJECTION_CSV = wsa.OUTPUTS_DIR / "steel_production_tiam_2019_anchored_worldsteel_indexed.csv"
OUTPUT_GROWTH_CSV = wsa.OUTPUTS_DIR / "steel_production_tiam_2019_anchored_worldsteel_indexed_growth_rates.csv"
OUTPUT_AUDIT_CSV = wsa.OUTPUTS_DIR / "steel_production_tiam_2019_anchored_worldsteel_indexed_audit.csv"


def validate_projection(projection: pd.DataFrame) -> pd.DataFrame:
    """Require one valid baseline row per TIAM region and every annual value."""
    result = projection.copy()
    result.columns = result.columns.map(str)
    if result.columns.tolist() != ["TIAMRegion", *YEARS]:
        raise ValueError("TIAM steel projection must contain TIAMRegion and 2019-2050 in order")
    if result["TIAMRegion"].duplicated().any() or set(result["TIAMRegion"]) != set(TIAM_REGIONS):
        raise ValueError("TIAM steel projection must contain all 16 unique TIAM regions")
    result[YEARS] = result[YEARS].apply(pd.to_numeric, errors="raise")
    values = result[YEARS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("TIAM steel projection contains invalid annual values")
    return result


def read_projection() -> pd.DataFrame:
    return validate_projection(pd.read_csv(INPUT_PROJECTION_CSV, float_precision="round_trip"))


def remap_country_regions(frame: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    """Replace source-vintage region columns without changing country volumes."""
    result = frame.copy()
    assignments = result["ISO3"].map(mapping.set_index("ISO3")["TIAMRegion"])
    if assignments.isna().any():
        missing = sorted(result.loc[assignments.isna(), "ISO3"].unique())
        raise ValueError(f"World Steel countries missing from TIAM mapping: {missing}")
    region_columns = [column for column in result if isinstance(column, str) and column.startswith("OMNIARegion")]
    for column in region_columns:
        result[column] = assignments
    result["OMNIARegion"] = assignments
    return result


def make_tiam_observations(
    panel: pd.DataFrame,
    mapping: pd.DataFrame,
    historical: pd.DataFrame,
    recent: pd.DataFrame,
    historical_map: pd.DataFrame,
    recent_map: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate the unchanged country basket before computing TIAM ratios."""
    checked_mapping = validate_mapping(mapping)
    tiam_panel = remap_country_regions(panel, checked_mapping)
    tiam_historical_map = remap_country_regions(historical_map, checked_mapping)
    tiam_recent_map = remap_country_regions(recent_map, checked_mapping)
    shared = checked_mapping[["ISO3", "TIAMRegion"]].rename(columns={"TIAMRegion": "region"})
    observations = wsa.make_regional_observations(
        tiam_panel, shared, historical, recent, tiam_historical_map, tiam_recent_map
    )
    # Regrouping must preserve the fixed basket's raw totals in every year.
    source_columns = {2019: "Production2019_kt", 2020: "Production2020_kt",
                      **{year: year for year in wsa.RECENT_YEARS}}
    for year, column in source_columns.items():
        if not np.isclose(observations[f"WSA{year}_kt"].sum(), panel[column].sum(), rtol=1e-12, atol=1e-6):
            raise ValueError(f"TIAM regrouping changed the fixed World Steel basket total in {year}")
    return observations.rename(columns={"OMNIARegion": "TIAMRegion"})


def apply_tiam_index(
    original: pd.DataFrame,
    observations: pd.DataFrame,
    metadata: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply and validate historical indices and the 2025 future handoff."""
    original_adapter = original.rename(columns={"TIAMRegion": "OMNIARegion"})
    observations_adapter = observations.rename(columns={"TIAMRegion": "OMNIARegion"})
    rebased, audit = wsa.build_rebased_projection(original_adapter, observations_adapter, metadata or {})
    wsa.validate_rebase(original_adapter, rebased, audit)
    audit = wsa.order_audit_columns(audit)
    audit["HistoricalFormula"] = audit["HistoricalFormula"].str.replace("OMNIA2019", "TIAM2019", regex=False)
    rename_columns = {column: column.replace("OMNIARegion", "TIAMRegion") for column in audit if "OMNIARegion" in column}
    rename_columns["DerivedOMNIA2025_kt"] = "DerivedTIAM2025_kt"
    return rebased.rename(columns={"OMNIARegion": "TIAMRegion"}), audit.rename(columns=rename_columns)


def build_outputs(
    original: pd.DataFrame | None = None,
    mapping: pd.DataFrame | None = None,
) -> dict[Path, pd.DataFrame]:
    """Build all three TIAM indexed outputs; perform no filesystem writes."""
    supplied_original = original is not None
    original = read_projection() if original is None else validate_projection(original)
    # The workbook builder validates all outputs before writing the baseline.
    # Hash its actual CSV serialization rather than any stale on-disk input.
    original_hash = (
        hashlib.sha256(original.to_csv(index=False, float_format="%.17g").encode("utf-8")).hexdigest()
        if supplied_original else wsa.file_sha256(INPUT_PROJECTION_CSV)
    )
    mapping = read_tiam_mapping() if mapping is None else validate_mapping(mapping)
    historical, historical_hash = wsa.read_historical_source()
    recent, _, recent_hash = wsa.read_recent_source()
    historical_map = wsa.read_source_map(wsa.HISTORICAL_MAP_CSV, set(historical["SourceCountry"]), "World Steel 2019-2020")
    recent_map = wsa.read_source_map(wsa.RECENT_MAP_CSV, set(recent["Country"]), "World Steel 2021-2025")
    historical_map_hash = wsa.file_sha256(wsa.HISTORICAL_MAP_CSV)
    recent_map_hash = wsa.file_sha256(wsa.RECENT_MAP_CSV)
    if historical_map_hash != wsa.EXPECTED_HISTORICAL_MAP_SHA256:
        raise ValueError("World Steel historical country map hash differs from the reviewed map")
    if recent_map_hash != wsa.EXPECTED_RECENT_MAP_SHA256:
        raise ValueError("World Steel recent country map hash differs from the reviewed map")
    # Validate the reviewed source-name maps exactly as in the original flow.
    shared_omnia = wsa.read_shared_map()
    wsa.validate_map_against_shared(historical_map, shared_omnia, "2019-2020 source")
    wsa.validate_map_against_shared(recent_map, shared_omnia, "2021-2025 source")
    panel = wsa.build_fixed_country_panel(historical, recent, historical_map, recent_map, shared_omnia)
    observations = make_tiam_observations(panel, mapping, historical, recent, historical_map, recent_map)
    if set(observations["TIAMRegion"]) != set(TIAM_REGIONS):
        raise ValueError("Fixed World Steel basket does not cover all 16 TIAM regions")
    unapplied = observations.loc[observations["RebaseApplied"].ne("yes"), ["TIAMRegion", "ExclusionReason"]]
    if not unapplied.empty:
        raise ValueError(f"TIAM regions lack positive World Steel 2019 denominators: {unapplied.to_dict('records')}")
    extracted_totals = {year: float(historical[f"Production{year}_kt"].sum()) for year in (2019, 2020)}
    metadata = {
        "HistoricalSourceCSV_SHA256": historical_hash,
        "HistoricalSourcePDF_SHA256": wsa.file_sha256(wsa.HISTORICAL_SOURCE_PDF),
        "HistoricalMapCSV_SHA256": historical_map_hash,
        "RecentSourceXLSX_SHA256": recent_hash,
        "RecentMapCSV_SHA256": recent_map_hash,
        "SharedMapCSV_SHA256": wsa.file_sha256(MAPPING_CSV),
        "TIAMMapCSV_SHA256": wsa.file_sha256(MAPPING_CSV),
        "TIAMSupplementCSV_SHA256": wsa.file_sha256(SUPPLEMENTS_CSV),
        "OriginalProjectionCSV_SHA256": original_hash,
        "HistoricalSourceDocument": wsa.HISTORICAL_SOURCE_DOCUMENT,
        "HistoricalSourceTable": wsa.HISTORICAL_SOURCE_TABLE,
        "HistoricalSourcePages": wsa.HISTORICAL_SOURCE_PAGES,
        "HistoricalSourceUnit": wsa.HISTORICAL_SOURCE_UNIT,
        "HistoricalContentsFinalised": wsa.HISTORICAL_CONTENTS_FINALISED,
        "RecentSourceSheet": wsa.RECENT_SOURCE_SHEET,
        "RecentSourceUnit": "kt crude steel",
        "RecentSourceLastUpdated": wsa.RECENT_SOURCE_LAST_UPDATED,
    }
    for year in (2019, 2020):
        metadata[f"HistoricalPublishedWorld{year}_kt"] = wsa.HISTORICAL_PUBLISHED_WORLD_KT[year]
        metadata[f"HistoricalExtractedCountrySum{year}_kt"] = extracted_totals[year]
        metadata[f"HistoricalCountrySumDelta{year}_kt"] = extracted_totals[year] - wsa.HISTORICAL_PUBLISHED_WORLD_KT[year]
    rebased, audit = apply_tiam_index(original, observations, metadata)
    return {OUTPUT_PROJECTION_CSV: rebased,
            OUTPUT_GROWTH_CSV: calculate_growth_rates(rebased),
            OUTPUT_AUDIT_CSV: audit}


def main() -> None:
    original = read_projection()
    outputs = build_outputs(original)
    # Keep each original 2019 CSV token byte-for-byte, alongside %.17g future
    # values. The numeric validation above already proves its anchor is fixed.
    original_text = pd.read_csv(INPUT_PROJECTION_CSV, dtype=str, keep_default_na=False)
    if original_text["TIAMRegion"].tolist() != original["TIAMRegion"].tolist():
        raise ValueError("TIAM baseline text and numeric region orders differ")
    outputs[OUTPUT_PROJECTION_CSV] = outputs[OUTPUT_PROJECTION_CSV].copy()
    outputs[OUTPUT_PROJECTION_CSV]["2019"] = original_text["2019"]
    for path, frame in outputs.items():
        frame.to_csv(path, index=False, float_format="%.17g")
        print(f"Saved: {path.relative_to(REPO_DIR)}")


if __name__ == "__main__":
    main()
