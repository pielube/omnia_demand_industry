import numpy as np
import pandas as pd
from pathlib import Path

# -------------------------------------------------------------------
# File paths
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"

enduse_path = INPUTS_DIR / "endusedemand.xlsx"
pop_path = INPUTS_DIR / "undesa_pop.xlsx"
total_scrap_path = INPUTS_DIR / "total_scrap.xlsx"

# Final output file: generated directly, with all data included
output_path = OUTPUTS_DIR / "steel_demand_and_scrap.csv"


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def normalise_year_column_name(col):
    """
    Convert Excel year headers to integers where possible.
    This avoids mismatches between year columns read as strings, floats,
    or integers.
    """
    if isinstance(col, str) and col.strip().isdigit():
        return int(col.strip())

    if isinstance(col, float) and col.is_integer():
        return int(col)

    return col


def read_excel_normalised(path, **kwargs):
    """
    Read Excel file and normalise year-like column names.
    """
    df = pd.read_excel(path, **kwargs)
    df.columns = [normalise_year_column_name(c) for c in df.columns]
    return df


def align_to_enduse_structure(df, target_columns):
    """
    Align an input dataframe to the exact structure of endusedemand.xlsx.

    Extra columns, such as Region or 1950 in total_scrap.xlsx, are dropped.
    Missing columns are added as NA.
    Columns are then reordered to match the target structure exactly.
    """
    df = df.copy()

    # Keep only columns that exist in the target structure
    df = df[[c for c in df.columns if c in target_columns]]

    # Add missing target columns
    for col in target_columns:
        if col not in df.columns:
            df[col] = pd.NA

    # Reorder columns exactly as in endusedemand.xlsx
    df = df[list(target_columns)]

    return df


# -------------------------------------------------------------------
# Read original end-use demand file
# -------------------------------------------------------------------
enduse = read_excel_normalised(enduse_path)

# -------------------------------------------------------------------
# Identify year columns in enduse file
# -------------------------------------------------------------------
year_cols = [col for col in enduse.columns if isinstance(col, int)]

# -------------------------------------------------------------------
# Read total scrap file and align to enduse structure
# -------------------------------------------------------------------
total_scrap = read_excel_normalised(total_scrap_path)

scrap_rows = align_to_enduse_structure(
    df=total_scrap,
    target_columns=enduse.columns
)

# -------------------------------------------------------------------
# Read UN DESA population file
# Actual header starts on the second row
# -------------------------------------------------------------------
pop = read_excel_normalised(pop_path, header=1)

pop.columns = [
    "SortOrder", "LocID", "Notes", "ISO3_code", "ISO2_code", "SDMX_code",
    "LocTypeID", "LocTypeName", "ParentID", "Location", "VarID", "Variant",
    "Time", "TPopulation1Jan"
]

# -------------------------------------------------------------------
# Keep only country-level Medium variant data
# -------------------------------------------------------------------
pop = pop[
    (pop["Variant"] == "Medium") &
    (pop["LocTypeName"] == "Country/Area")
].copy()

# -------------------------------------------------------------------
# Build country reference from original enduse file
# This preserves the exact original country names
# -------------------------------------------------------------------
country_ref = (
    enduse[["MISO2_country", "ISO3166-1-Alpha-3"]]
    .drop_duplicates()
    .dropna(subset=["ISO3166-1-Alpha-3"])
    .copy()
)

# Keep only ISO3 codes present in enduse
pop = pop[pop["ISO3_code"].isin(country_ref["ISO3166-1-Alpha-3"])].copy()

# -------------------------------------------------------------------
# Pivot population to wide format
# -------------------------------------------------------------------
pop_wide = pop.pivot(
    index="ISO3_code",
    columns="Time",
    values="TPopulation1Jan"
).reset_index()

# -------------------------------------------------------------------
# Merge with original country reference
# -------------------------------------------------------------------
pop_rows = country_ref.merge(
    pop_wide,
    left_on="ISO3166-1-Alpha-3",
    right_on="ISO3_code",
    how="left"
)

pop_rows = pop_rows.drop(columns=["ISO3_code"])

# -------------------------------------------------------------------
# Create population rows matching original structure
# -------------------------------------------------------------------
population_rows = pd.DataFrame(columns=enduse.columns)

population_rows["MISO2_country"] = pop_rows["MISO2_country"]
population_rows["ISO3166-1-Alpha-3"] = pop_rows["ISO3166-1-Alpha-3"]
population_rows["Sector"] = ""
population_rows["Metric"] = "Population"
population_rows["Unit"] = ""

for year in year_cols:
    if year in pop_rows.columns:
        population_rows[year] = pop_rows[year]

population_rows = population_rows[enduse.columns]

# -------------------------------------------------------------------
# Force the Global population row to be the sum of all country populations
# -------------------------------------------------------------------
global_mask = (
    population_rows["MISO2_country"]
    .astype(str)
    .str.strip()
    .str.lower()
    .eq("global")
)

if global_mask.any():
    country_mask = ~global_mask
    global_idx = population_rows.index[global_mask][0]

    for year in year_cols:
        population_rows.loc[global_idx, year] = (
            population_rows.loc[country_mask, year].sum(skipna=True)
        )

# -------------------------------------------------------------------
# Build a population lookup indexed by ISO3
# -------------------------------------------------------------------
population_lookup = population_rows.set_index("ISO3166-1-Alpha-3")[year_cols]

# -------------------------------------------------------------------
# Create per-capita rows from the ORIGINAL enduse rows only
# Output in t/person rather than kt/person
# -------------------------------------------------------------------
percap_rows_list = []

for _, row in enduse.iterrows():
    iso3 = row["ISO3166-1-Alpha-3"]

    # Skip rows with no ISO3 or no population match
    if pd.isna(iso3) or iso3 not in population_lookup.index:
        continue

    pop_series = population_lookup.loc[iso3, year_cols]

    # Skip if all population values are missing
    if pop_series.isna().all():
        continue

    new_row = row.copy()

    # Update metric and unit
    new_row["Metric"] = "End-use steel consumption per capita [t/person]"
    new_row["Unit"] = "t/person"

    # Divide year by year and convert kt/person to t/person
    for year in year_cols:
        val = row[year]
        pop_val = pop_series[year]

        if pd.isna(val) or pd.isna(pop_val) or pop_val == 0:
            new_row[year] = np.nan
        else:
            new_row[year] = (val / pop_val) * 1000

    percap_rows_list.append(new_row)

percap_rows = pd.DataFrame(percap_rows_list, columns=enduse.columns)

# -------------------------------------------------------------------
# Combine everything directly into the final output
# Structure:
#   1. Original end-use demand
#   2. Population rows
#   3. Per-capita rows
#   4. Total scrap rows
# -------------------------------------------------------------------
final_df = pd.concat(
    [
        enduse,
        population_rows,
        percap_rows,
        scrap_rows
    ],
    ignore_index=True
)

# -------------------------------------------------------------------
# Final structure check
# -------------------------------------------------------------------
if list(final_df.columns) != list(enduse.columns):
    raise ValueError(
        "Final dataframe columns do not match the original endusedemand.xlsx structure."
    )

# -------------------------------------------------------------------
# Save final output
# -------------------------------------------------------------------
OUTPUTS_DIR.mkdir(exist_ok=True)
final_df.to_csv(output_path, index=False)

print(f"Done. File saved as: {output_path}")
print(f"Original end-use rows: {len(enduse)}")
print(f"Population rows added: {len(population_rows)}")
print(f"Per-capita rows added: {len(percap_rows)}")
print(f"Total scrap rows added: {len(scrap_rows)}")
print(f"Final rows: {len(final_df)}")
