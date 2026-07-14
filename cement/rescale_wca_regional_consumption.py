"""Rescale WCA regional trajectories to mapped observed 2024 production."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from wca_regional_consumption import WCA_YEARS, read_wca_regional_consumption


BASE_DIR = Path(__file__).resolve().parent
ORIGINAL_WCA_PATH = BASE_DIR / "inputs" / "wca_regional_cement_consumption.csv"
COUNTRY_REGION_PATH = BASE_DIR / "maps" / "wca_country_region_mapping.csv"
HISTORICAL_CEMENT_URL = (
    "https://zenodo.org/records/20397304/files/"
    "1.%20annual_cement_production.csv?download=1"
)
OUTPUT_PATH = (
    BASE_DIR / "inputs" / "wca_regional_cement_consumption_rescaled.csv"
)

CALIBRATION_YEAR = 2024
KT_PER_MT = 1000.0


def observed_regional_totals_mt(
    mapping_path: Path,
) -> dict[str, float]:
    """Download and aggregate mapped production in the calibration year."""
    mapping = pd.read_csv(mapping_path, dtype=str, keep_default_na=False)
    required_mapping_columns = {"ISO3", "WCARegion"}
    missing_mapping_columns = required_mapping_columns - set(mapping.columns)
    if missing_mapping_columns:
        raise ValueError(
            "WCA mapping file is missing columns: "
            f"{sorted(missing_mapping_columns)}"
        )

    mapping = mapping[["ISO3", "WCARegion"]].copy()
    mapping["ISO3"] = mapping["ISO3"].str.strip().str.upper()
    mapping["WCARegion"] = mapping["WCARegion"].str.strip()
    if mapping["ISO3"].duplicated().any():
        duplicates = sorted(
            mapping.loc[mapping["ISO3"].duplicated(keep=False), "ISO3"].unique()
        )
        raise ValueError(f"Duplicate ISO3 values in WCA mapping: {duplicates}")

    cement_raw = pd.read_csv(HISTORICAL_CEMENT_URL)
    if "Year" not in cement_raw.columns:
        raise ValueError("Historical cement file has no 'Year' column")
    historical = cement_raw[cement_raw["Year"].eq(CALIBRATION_YEAR)].melt(
        id_vars="Year",
        var_name="raw_country_column",
        value_name="production_kt",
    )
    if historical.empty:
        raise ValueError(
            f"Historical cement file has no data for {CALIBRATION_YEAR}"
        )

    historical["ISO3"] = historical["raw_country_column"].map(
        lambda column: (
            match.group(1)
            if (match := re.match(r"^([A-Z]{3})(?:\s*\(\d+\))?$", str(column).strip()))
            else None
        )
    )
    historical["production_kt"] = pd.to_numeric(
        historical["production_kt"], errors="coerce"
    )
    historical = historical.dropna(subset=["ISO3", "production_kt"])
    historical = historical.merge(mapping, on="ISO3", how="inner", validate="many_to_one")

    totals = (
        historical.groupby("WCARegion")["production_kt"].sum(min_count=1)
        / KT_PER_MT
    )
    if totals.isna().any() or (totals <= 0).any():
        invalid = totals[totals.isna() | (totals <= 0)].index.tolist()
        raise ValueError(f"Invalid observed regional totals for: {invalid}")
    return totals.to_dict()


def build_rescaled_rows() -> list[dict[str, object]]:
    original_rows = read_wca_regional_consumption(ORIGINAL_WCA_PATH)
    observed_totals = observed_regional_totals_mt(COUNTRY_REGION_PATH)

    original_regions = {str(row["Region"]) for row in original_rows}
    missing_totals = sorted(original_regions - set(observed_totals))
    extra_totals = sorted(set(observed_totals) - original_regions)
    if missing_totals or extra_totals:
        raise ValueError(
            "WCA and observed regional coverage differ. "
            f"Missing totals: {missing_totals}; extra totals: {extra_totals}"
        )

    rescaled_rows = []
    for row in original_rows:
        region = str(row["Region"])
        original_anchor = float(
            row[f"Consumption {CALIBRATION_YEAR} (Mtpa)"]
        )
        observed_anchor = float(observed_totals[region])
        factor = observed_anchor / original_anchor

        rescaled: dict[str, object] = {
            "Market type": row["Market type"],
            "Region": region,
            "Calibration year": CALIBRATION_YEAR,
            "Observed regional total 2024 (Mtpa)": round(observed_anchor, 9),
            "Original WCA total 2024 (Mtpa)": round(original_anchor, 9),
            "Rescaling factor": round(factor, 12),
        }
        for year in WCA_YEARS:
            value = float(row[f"Consumption {year} (Mtpa)"]) * factor
            rescaled[f"Consumption {year} (Mtpa)"] = round(value, 9)
        rescaled_rows.append(rescaled)

    return rescaled_rows


def write_rescaled_csv(rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "Market type",
        "Region",
        "Calibration year",
        "Observed regional total 2024 (Mtpa)",
        "Original WCA total 2024 (Mtpa)",
        "Rescaling factor",
        *(f"Consumption {year} (Mtpa)" for year in WCA_YEARS),
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = build_rescaled_rows()
    write_rescaled_csv(rows)
    print(f"Saved: {OUTPUT_PATH}")
    print("Regional calibration factors:")
    for row in rows:
        print(
            f"  {row['Region']}: {float(row['Rescaling factor']):.6f} "
            f"({float(row['Original WCA total 2024 (Mtpa)']):.3f} -> "
            f"{float(row['Observed regional total 2024 (Mtpa)']):.3f} Mtpa)"
        )


if __name__ == "__main__":
    main()
