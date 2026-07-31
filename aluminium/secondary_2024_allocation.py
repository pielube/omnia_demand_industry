from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

SECONDARY_ESTIMATES_PATH = (
    INPUTS_DIR / "secondary_aluminium_production_estimates_2024.xlsx"
)
OMNIA_MAPPING_PATH = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"

ESTIMATE_LAYOUTS = {
    "Estimates": {
        "header": 4,
        "estimate_column": "Point estimate (kt)",
    },
    "Country estimates": {
        "header": 3,
        "estimate_column": "Production estimate (kt)",
    },
}

ZIJIE_REGIONS = [
    "China",
    "North America",
    "Europe",
    "South America",
    "Other Asia",
    "Other main producer",
    "Middle East",
    "Japan",
    "UK",
    "Rest of World",
]


def read_secondary_2024_allocation_weights():
    workbook = pd.ExcelFile(SECONDARY_ESTIMATES_PATH)
    matching_sheets = [
        sheet for sheet in ESTIMATE_LAYOUTS if sheet in workbook.sheet_names
    ]
    if len(matching_sheets) != 1:
        raise ValueError(
            "Could not identify one supported estimates sheet in "
            f"{SECONDARY_ESTIMATES_PATH.name}. Found: {workbook.sheet_names}"
        )
    estimates_sheet = matching_sheets[0]
    layout = ESTIMATE_LAYOUTS[estimates_sheet]
    estimate_column = layout["estimate_column"]
    estimates = pd.read_excel(
        workbook,
        sheet_name=estimates_sheet,
        header=layout["header"],
    )
    required_estimate_columns = {"Country", "ISO3", estimate_column}
    missing = required_estimate_columns - set(estimates.columns)
    if missing:
        raise ValueError(
            "Secondary 2024 estimates are missing columns: "
            f"{sorted(missing)}"
        )

    estimates = estimates[
        ["Country", "ISO3", estimate_column]
    ].rename(
        columns={
            "Country": "SecondaryEstimate2024Country",
            estimate_column: "SecondaryEstimate2024_kt",
        }
    )
    estimates["ISO3"] = estimates["ISO3"].astype(str).str.strip().str.upper()
    estimates["SecondaryEstimate2024_kt"] = pd.to_numeric(
        estimates["SecondaryEstimate2024_kt"],
        errors="raise",
    )

    if estimates["ISO3"].duplicated().any():
        duplicates = estimates.loc[
            estimates["ISO3"].duplicated(keep=False), "ISO3"
        ].tolist()
        raise ValueError(
            f"Secondary 2024 estimates contain duplicate ISO3 codes: {duplicates}"
        )
    if estimates["SecondaryEstimate2024_kt"].isna().any():
        raise ValueError("Secondary 2024 estimates contain blank production values.")
    if estimates["SecondaryEstimate2024_kt"].lt(0).any():
        raise ValueError("Secondary 2024 estimates contain negative production values.")

    mapping = pd.read_csv(OMNIA_MAPPING_PATH)
    required_mapping_columns = {"ISO3", "ZijieRegion"}
    missing = required_mapping_columns - set(mapping.columns)
    if missing:
        raise ValueError(f"OMNIA mapping is missing columns: {sorted(missing)}")

    region_lookup = mapping[["ISO3", "ZijieRegion"]].drop_duplicates()
    conflicting = region_lookup[region_lookup["ISO3"].duplicated(keep=False)]
    if not conflicting.empty:
        raise ValueError(
            "ISO3 codes map to more than one Zijie region:\n"
            f"{conflicting.to_string(index=False)}"
        )

    weights = estimates.merge(
        region_lookup,
        on="ISO3",
        how="left",
        validate="one_to_one",
    )
    unmapped = weights[weights["ZijieRegion"].isna()]
    if not unmapped.empty:
        raise ValueError(
            "Secondary 2024 estimates could not be mapped for ISO3 codes: "
            f"{unmapped['ISO3'].tolist()}"
        )

    weights = weights[weights["SecondaryEstimate2024_kt"].gt(0)].copy()
    missing_regions = sorted(set(ZIJIE_REGIONS) - set(weights["ZijieRegion"]))
    if missing_regions:
        raise ValueError(
            "Secondary 2024 estimates have no positive allocation weight in "
            f"these Zijie regions: {missing_regions}"
        )

    region_totals = weights.groupby("ZijieRegion")[
        "SecondaryEstimate2024_kt"
    ].transform("sum")
    weights["RegionShare2024"] = (
        weights["SecondaryEstimate2024_kt"] / region_totals
    )
    weights["AllocationMethod2024"] = (
        "Zijie 2024 regional total allocated using country shares from "
        "secondary_aluminium_production_estimates_2024.xlsx"
    )

    share_totals = weights.groupby("ZijieRegion")["RegionShare2024"].sum()
    if not np.allclose(share_totals.to_numpy(), 1.0):
        raise ValueError(
            "Secondary 2024 allocation shares do not sum to one by region: "
            f"{share_totals.to_dict()}"
        )

    return weights[
        [
            "ISO3",
            "ZijieRegion",
            "SecondaryEstimate2024Country",
            "SecondaryEstimate2024_kt",
            "RegionShare2024",
            "AllocationMethod2024",
        ]
    ]
