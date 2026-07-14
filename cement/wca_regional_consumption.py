"""Shared reader and validation for WCA regional cement consumption inputs."""

from __future__ import annotations

import csv
import math
from pathlib import Path


WCA_YEARS = (2020, 2024, 2035, 2050)
WCA_MARKET_TYPES = (
    "Decline then stable",
    "Already stable",
    "Slow growth",
    "Fast growth",
)


def read_wca_regional_consumption(
    path: Path,
) -> list[dict[str, str | float]]:
    """Read the regional WCA table and validate its schema and values."""
    required_columns = [
        "Market type",
        "Region",
        *(f"Consumption {year} (Mtpa)" for year in WCA_YEARS),
    ]
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing_columns = set(required_columns) - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"WCA consumption file is missing columns: {sorted(missing_columns)}"
            )
        raw_rows = list(reader)

    if not raw_rows:
        raise ValueError(f"WCA consumption file is empty: {path}")

    rows: list[dict[str, str | float]] = []
    seen_regions: set[str] = set()
    for line_number, raw_row in enumerate(raw_rows, start=2):
        market_type = raw_row["Market type"].strip()
        region = raw_row["Region"].strip()
        if market_type not in WCA_MARKET_TYPES:
            raise ValueError(
                f"Unknown market type on line {line_number}: {market_type!r}"
            )
        if not region:
            raise ValueError(f"Blank region on line {line_number}")
        if region in seen_regions:
            raise ValueError(f"Duplicate WCA region on line {line_number}: {region}")
        seen_regions.add(region)

        row: dict[str, str | float] = {
            "Market type": market_type,
            "Region": region,
        }
        for year in WCA_YEARS:
            column = f"Consumption {year} (Mtpa)"
            try:
                value = float(raw_row[column])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid {column} value on line {line_number}: "
                    f"{raw_row[column]!r}"
                ) from error
            if not math.isfinite(value) or value <= 0:
                raise ValueError(
                    f"{column} must be positive and finite on line {line_number}"
                )
            row[column] = value
        rows.append(row)

    missing_market_types = set(WCA_MARKET_TYPES) - {
        str(row["Market type"]) for row in rows
    }
    if missing_market_types:
        raise ValueError(
            "WCA consumption file does not represent all market types: "
            f"{sorted(missing_market_types)}"
        )
    return rows


def regional_consumption_by_year(
    rows: list[dict[str, str | float]],
) -> dict[str, dict[int, float]]:
    """Convert validated table rows to region -> year -> Mtpa values."""
    return {
        str(row["Region"]): {
            year: float(row[f"Consumption {year} (Mtpa)"])
            for year in WCA_YEARS
        }
        for row in rows
    }
