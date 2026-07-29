import re
from pathlib import Path

import numpy as np
import pandas as pd

from wca_regional_consumption import (
    read_wca_regional_consumption,
    regional_consumption_by_year,
)


# -------------------------------------------------------------------
# File paths
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
MAPS_DIR = BASE_DIR / "maps"
OUTPUTS_DIR = BASE_DIR / "outputs"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

pop_path = SHARED_INPUTS_DIR / "undesa_pop.xlsx"
gdp_path = SHARED_INPUTS_DIR / "gdp_projection_country_SSP2.xlsx"
wca_consumption_path = (
    INPUTS_DIR / "wca_regional_cement_consumption_rescaled.csv"
)

cement_url = (
    "https://zenodo.org/records/20397304/files/"
    "1.%20annual_cement_production.csv?download=1"
)

output_path = OUTPUTS_DIR / "cement_country.csv"
wca_mapping_path = MAPS_DIR / "wca_country_region_mapping.csv"


# -------------------------------------------------------------------
# User settings
# -------------------------------------------------------------------
START_YEAR = 1951
END_YEAR = 2100
BASE_YEAR = 2024
PROJECTION_START_YEAR = BASE_YEAR + 1

KEEP_ONLY_COUNTRIES_WITH_POPULATION = True

DEMAND_METRIC = "Cement production"
DEMAND_UNIT = "kt cement"

POPULATION_METRIC = "Population"
POPULATION_UNIT = ""

ELASTICITY_POINTS = [
    (0.0, 1.264),
    (0.1, 1.1),
    (0.2, 1.109),
    (0.3, 0.6),
    (0.4, 0.336),
    (0.5, 0.18),
    (0.6, -0.027),
    (0.7, -0.041),
    (0.8, -0.252),
]


# Regional cement consumption in Mtpa, loaded from the shared WCA input CSV.
WCA_REGION_CONSUMPTION_MTPA = regional_consumption_by_year(
    read_wca_regional_consumption(wca_consumption_path)
)


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def normalise_year_column_name(col):
    """
    Convert Excel/CSV year headers to integers where possible.
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


def clean_iso3_column_name(col):
    """
    Extract clean ISO3 codes from cement dataset columns.
    """
    col = str(col).strip()

    match = re.match(r"^([A-Z]{3})(?:\s*\(\d+\))?$", col)
    if match:
        return match.group(1)

    return None


def make_output_columns(start_year, end_year):
    """
    Create final output structure without Sector.
    """
    return (
        ["Country", "ISO2", "ISO3", "Metric", "Unit"]
        + list(range(start_year, end_year + 1))
    )


def remove_global_rows(df):
    """
    Remove global rows if present.
    """
    country_cols = [c for c in ["Country", "Location"] if c in df.columns]

    if not country_cols:
        return df.copy()

    mask = pd.Series(False, index=df.index)

    for col in country_cols:
        mask = mask | df[col].astype(str).str.strip().str.lower().eq("global")

    if "ISO3" in df.columns:
        mask = mask | df["ISO3"].astype(str).str.strip().str.upper().eq("WLD")

    if "ISO3_code" in df.columns:
        mask = mask | df["ISO3_code"].astype(str).str.strip().str.upper().eq("WLD")

    return df[~mask].copy()


def cement_income_elasticity(cement_output_per_capita):
    """
    Return cement income elasticity from Dirk's cement-output-per-capita table.

    Cement output per capita is expressed as tonnes per person. Values outside
    the table range are clamped to the nearest endpoint.
    """
    points = np.array(ELASTICITY_POINTS, dtype=float)
    return np.interp(
        cement_output_per_capita,
        points[:, 0],
        points[:, 1],
        left=points[0, 1],
        right=points[-1, 1],
    )


def read_gdp_projection(path):
    """
    Read annual GDP projections and normalise year-like column names.
    """
    gdp = read_excel_normalised(path)

    required_columns = {"ISO3"}
    missing_columns = required_columns - set(gdp.columns)
    if missing_columns:
        raise ValueError(
            "GDP projection file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    gdp["ISO3"] = gdp["ISO3"].astype(str).str.strip()
    gdp = remove_global_rows(gdp)

    return gdp


def wca_region_total_kt(region, year):
    """
    Return WCA regional cement consumption target in kt.

    Values are linearly interpolated between WCA table years. Calls after the
    final table year return the final table value; post-2050 growth is applied
    separately in the projection function.
    """
    points = WCA_REGION_CONSUMPTION_MTPA[region]
    years = sorted(points)

    if year <= years[0]:
        value_mt = points[years[0]]
    elif year >= years[-1]:
        value_mt = points[years[-1]]
    else:
        value_mt = np.interp(
            year,
            years,
            [points[point_year] for point_year in years],
        )

    return value_mt * 1000


def read_wca_region_map(path, country_ref):
    """
    Read and validate the authoritative country-to-WCA-region mapping.
    """
    mapping = pd.read_csv(path, dtype=str, keep_default_na=False)
    required_columns = ["Country", "ISO2", "ISO3", "WCARegion"]
    missing_columns = set(required_columns) - set(mapping.columns)
    if missing_columns:
        raise ValueError(
            "WCA mapping file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    mapping = mapping[required_columns].copy()
    for column in required_columns:
        mapping[column] = mapping[column].str.strip()
    mapping["ISO3"] = mapping["ISO3"].str.upper()

    blank_rows = mapping[
        mapping["ISO3"].eq("") | mapping["WCARegion"].eq("")
    ]
    if not blank_rows.empty:
        raise ValueError(
            "WCA mapping file has blank ISO3 or WCARegion values:\n"
            f"{blank_rows.to_string(index=False)}"
        )

    duplicate_iso3 = sorted(
        mapping.loc[mapping["ISO3"].duplicated(keep=False), "ISO3"].unique()
    )
    if duplicate_iso3:
        raise ValueError(
            "WCA mapping file has duplicate ISO3 values: "
            f"{duplicate_iso3}"
        )

    valid_regions = set(WCA_REGION_CONSUMPTION_MTPA)
    unknown_regions = sorted(set(mapping["WCARegion"]) - valid_regions)
    if unknown_regions:
        raise ValueError(
            "WCA mapping file has regions without WCA demand totals: "
            f"{unknown_regions}"
        )

    missing_regions = sorted(valid_regions - set(mapping["WCARegion"]))
    if missing_regions:
        raise ValueError(
            "WCA mapping file does not represent all WCA regions: "
            f"{missing_regions}"
        )

    required_iso3 = set(
        country_ref["ISO3"].dropna().astype(str).str.strip().str.upper()
    )
    mapped_iso3 = set(mapping["ISO3"])
    missing_iso3 = sorted(required_iso3 - mapped_iso3)
    if missing_iso3:
        raise ValueError(
            "WCA mapping file does not cover all cement countries. "
            f"Missing ISO3 values: {missing_iso3}"
        )

    region_by_iso3 = mapping.set_index("ISO3")["WCARegion"].to_dict()
    return {iso3: region_by_iso3[iso3] for iso3 in sorted(required_iso3)}


def project_cement_demand_wca(
    cement_rows,
    population_rows,
    gdp,
    wca_region_by_iso3,
    start_year,
    end_year,
):
    """
    Project country cement demand with dynamic country shares constrained to WCA
    regional totals.

    Country demand first follows the GDP-per-capita elasticity method. For years
    covered by the WCA table, each country's unconstrained demand is scaled so
    its region exactly matches the WCA regional total. After the final WCA table
    year, regional totals follow the region's unconstrained growth from that
    final table year rather than staying flat.
    """
    projected = cement_rows.copy()
    population_by_iso3 = population_rows.set_index("ISO3")
    gdp_by_iso3 = gdp.set_index("ISO3")
    final_wca_year = max(max(points) for points in WCA_REGION_CONSUMPTION_MTPA.values())

    projected["WCARegion"] = projected["ISO3"].map(wca_region_by_iso3)

    projection_issues = []
    projection_imputations = []

    if projected["WCARegion"].isna().any():
        for iso3 in projected.loc[projected["WCARegion"].isna(), "ISO3"]:
            projection_issues.append((iso3, "missing WCA region mapping"))

    unconstrained = {}
    region_by_projected_iso3 = {}

    for region, region_rows in projected.dropna(subset=["WCARegion"]).groupby("WCARegion"):
        region_rows = region_rows.copy()
        positive_mask = (
            region_rows[BASE_YEAR].notna() &
            (region_rows[BASE_YEAR] > 0)
        )

        positive_iso3 = region_rows.loc[positive_mask, "ISO3"]
        positive_demand = region_rows.loc[positive_mask, BASE_YEAR].sum()
        positive_population = (
            population_by_iso3
            .loc[positive_iso3, BASE_YEAR]
            .dropna()
            .sum()
        )

        regional_intensity = (
            positive_demand / positive_population
            if positive_population > 0
            else np.nan
        )

        for _, row in region_rows.iterrows():
            iso3 = row["ISO3"]
            base_demand = row[BASE_YEAR]

            if iso3 not in population_by_iso3.index:
                projection_issues.append((iso3, "missing population row"))
                continue

            has_gdp_driver = iso3 in gdp_by_iso3.index
            if not has_gdp_driver:
                projection_imputations.append(
                    (iso3, "constant cement intensity; missing GDP projection")
                )

            base_population = population_by_iso3.at[iso3, BASE_YEAR]
            if pd.isna(base_population) or base_population <= 0:
                projection_issues.append((iso3, f"missing/zero population in {BASE_YEAR}"))
                continue

            if pd.notna(base_demand) and base_demand > 0:
                cement_per_capita = base_demand / base_population
            else:
                if pd.isna(regional_intensity) or regional_intensity <= 0:
                    projection_issues.append((iso3, "no WCA base allocation weight"))
                    continue

                cement_per_capita = regional_intensity
                projection_imputations.append(
                    (iso3, f"regional average base intensity from {region}")
                )

            unconstrained[iso3] = {}
            region_by_projected_iso3[iso3] = region

            for year in range(BASE_YEAR + 1, end_year + 1):
                previous_year = year - 1

                if year not in population_by_iso3.columns:
                    projection_issues.append((iso3, f"missing population column {year}"))
                    break

                current_population = population_by_iso3.at[iso3, year]
                if pd.isna(current_population) or current_population <= 0:
                    projection_issues.append((iso3, f"missing/zero population in {year}"))
                    break

                if not has_gdp_driver:
                    unconstrained[iso3][year] = cement_per_capita * current_population
                    continue

                if year not in gdp_by_iso3.columns or previous_year not in gdp_by_iso3.columns:
                    projection_issues.append((iso3, f"missing GDP column {previous_year}/{year}"))
                    break

                previous_population = population_by_iso3.at[iso3, previous_year]
                previous_gdp = gdp_by_iso3.at[iso3, previous_year]
                current_gdp = gdp_by_iso3.at[iso3, year]

                required_values = [
                    previous_population,
                    current_population,
                    previous_gdp,
                    current_gdp,
                ]
                if any(pd.isna(value) or value <= 0 for value in required_values):
                    projection_issues.append((iso3, f"missing/zero driver in {previous_year}/{year}"))
                    break

                previous_gdp_per_capita = previous_gdp / previous_population
                current_gdp_per_capita = current_gdp / current_population

                elasticity = cement_income_elasticity(cement_per_capita)
                cement_per_capita = cement_per_capita * (
                    current_gdp_per_capita / previous_gdp_per_capita
                ) ** elasticity

                unconstrained[iso3][year] = cement_per_capita * current_population

    region_unconstrained_totals = {}
    for iso3, values in unconstrained.items():
        region = region_by_projected_iso3[iso3]
        region_unconstrained_totals.setdefault(region, {})
        for year, value in values.items():
            region_unconstrained_totals[region][year] = (
                region_unconstrained_totals[region].get(year, 0) + value
            )

    region_targets = {}
    for region in region_unconstrained_totals:
        region_targets[region] = {}
        final_table_total = wca_region_total_kt(region, final_wca_year)
        final_unconstrained_total = region_unconstrained_totals[region].get(final_wca_year)

        for year in range(start_year, end_year + 1):
            if year <= final_wca_year:
                region_targets[region][year] = wca_region_total_kt(region, year)
                continue

            current_unconstrained_total = region_unconstrained_totals[region].get(year)
            if (
                pd.isna(final_unconstrained_total) or
                final_unconstrained_total <= 0 or
                pd.isna(current_unconstrained_total) or
                current_unconstrained_total <= 0
            ):
                region_targets[region][year] = final_table_total
                projection_issues.append(
                    (region, f"holding WCA total after {final_wca_year}; missing unconstrained growth")
                )
                continue

            region_targets[region][year] = (
                final_table_total *
                current_unconstrained_total /
                final_unconstrained_total
            )

    for idx, row in projected.iterrows():
        iso3 = row["ISO3"]
        region = row["WCARegion"]

        if pd.isna(region) or iso3 not in unconstrained:
            continue

        for year in range(start_year, end_year + 1):
            unconstrained_country_demand = unconstrained[iso3].get(year)
            unconstrained_region_demand = region_unconstrained_totals.get(region, {}).get(year)
            regional_target = region_targets.get(region, {}).get(year)

            if (
                pd.isna(unconstrained_country_demand) or
                pd.isna(unconstrained_region_demand) or
                pd.isna(regional_target) or
                unconstrained_region_demand <= 0
            ):
                continue

            projected.at[idx, year] = (
                unconstrained_country_demand *
                regional_target /
                unconstrained_region_demand
            )

    projected = projected.drop(columns=["WCARegion"])

    return projected, projection_issues, projection_imputations


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

pop = remove_global_rows(pop)

pop = pop[
    (pop["Time"] >= START_YEAR) &
    (pop["Time"] <= END_YEAR)
].copy()


# -------------------------------------------------------------------
# Build country reference from UN DESA
# -------------------------------------------------------------------
country_ref = (
    pop[["Location", "ISO2_code", "ISO3_code"]]
    .drop_duplicates()
    .dropna(subset=["ISO3_code"])
    .copy()
)

country_ref = country_ref.rename(
    columns={
        "Location": "Country",
        "ISO2_code": "ISO2",
        "ISO3_code": "ISO3",
    }
)

country_ref["Country"] = country_ref["Country"].astype(str).str.strip()
country_ref["ISO2"] = country_ref["ISO2"].astype(str).str.strip()
country_ref["ISO3"] = country_ref["ISO3"].astype(str).str.strip()

country_ref.loc[country_ref["ISO3"] == "NAM", "ISO2"] = "NA"

country_ref = remove_global_rows(country_ref)


# -------------------------------------------------------------------
# Read GDP projection data
# -------------------------------------------------------------------
gdp = read_gdp_projection(gdp_path)


# -------------------------------------------------------------------
# Read cement production data from Zenodo
# -------------------------------------------------------------------
cement_raw = pd.read_csv(cement_url)

cement_raw.columns = [normalise_year_column_name(c) for c in cement_raw.columns]

if "Year" not in cement_raw.columns:
    raise ValueError("Expected a 'Year' column in the cement production file.")

cement_raw = cement_raw[
    (cement_raw["Year"] >= START_YEAR) &
    (cement_raw["Year"] <= BASE_YEAR)
].copy()


# -------------------------------------------------------------------
# Reshape cement data from wide to long
# -------------------------------------------------------------------
cement_long = cement_raw.melt(
    id_vars="Year",
    var_name="raw_country_column",
    value_name="value"
)

cement_long["ISO3"] = cement_long["raw_country_column"].apply(
    clean_iso3_column_name
)

cement_long = cement_long.dropna(subset=["ISO3"]).copy()
cement_long = cement_long.dropna(subset=["value"]).copy()
cement_long = cement_long[
    cement_long["ISO3"].str.upper() != "WLD"
].copy()


# -------------------------------------------------------------------
# Optionally keep only cement countries with matching UN DESA population
# -------------------------------------------------------------------
population_iso3 = set(country_ref["ISO3"].dropna().unique())

if KEEP_ONLY_COUNTRIES_WITH_POPULATION:
    cement_long = cement_long[
        cement_long["ISO3"].isin(population_iso3)
    ].copy()


# -------------------------------------------------------------------
# Restrict country reference to countries present in the cement dataset
# -------------------------------------------------------------------
cement_iso3 = sorted(cement_long["ISO3"].dropna().unique())

country_ref = country_ref[
    country_ref["ISO3"].isin(cement_iso3)
].copy()


# -------------------------------------------------------------------
# Create cement demand rows
# -------------------------------------------------------------------
cement_wide = cement_long.pivot_table(
    index="ISO3",
    columns="Year",
    values="value",
    aggfunc="sum"
).reset_index()

cement_rows = country_ref.merge(
    cement_wide,
    on="ISO3",
    how="left"
)

cement_rows["Metric"] = DEMAND_METRIC
cement_rows["Unit"] = DEMAND_UNIT


# -------------------------------------------------------------------
# Create population rows
# -------------------------------------------------------------------
pop = pop[pop["ISO3_code"].isin(country_ref["ISO3"])].copy()

pop_wide = pop.pivot_table(
    index="ISO3_code",
    columns="Time",
    values="TPopulation1Jan",
    aggfunc="first"
).reset_index()

population_rows = country_ref.merge(
    pop_wide,
    left_on="ISO3",
    right_on="ISO3_code",
    how="left"
)

population_rows = population_rows.drop(columns=["ISO3_code"])

population_rows["Metric"] = POPULATION_METRIC
population_rows["Unit"] = POPULATION_UNIT


# -------------------------------------------------------------------
# Read authoritative WCA country-region mapping
# -------------------------------------------------------------------
wca_region_by_iso3 = read_wca_region_map(wca_mapping_path, country_ref)


# -------------------------------------------------------------------
# Project cement demand using WCA regional table
# -------------------------------------------------------------------
cement_rows, projection_issues, projection_imputations = (
    project_cement_demand_wca(
        cement_rows=cement_rows,
        population_rows=population_rows,
        gdp=gdp,
        wca_region_by_iso3=wca_region_by_iso3,
        start_year=PROJECTION_START_YEAR,
        end_year=END_YEAR,
    )
)


# -------------------------------------------------------------------
# Align both datasets to final structure
# -------------------------------------------------------------------
final_columns = make_output_columns(START_YEAR, END_YEAR)

for df in [cement_rows, population_rows]:
    for col in final_columns:
        if col not in df.columns:
            df[col] = np.nan

cement_rows = cement_rows[final_columns]
population_rows = population_rows[final_columns]


# -------------------------------------------------------------------
# Prepare the cement-only country output
# -------------------------------------------------------------------
final_df = remove_global_rows(cement_rows)


# -------------------------------------------------------------------
# Sort output
# -------------------------------------------------------------------
final_df = final_df.sort_values(
    by=["Country"]
).reset_index(drop=True)


# -------------------------------------------------------------------
# Final checks
# -------------------------------------------------------------------
if list(final_df.columns) != final_columns:
    raise ValueError("Final dataframe columns do not match the required structure.")

if "Sector" in final_df.columns:
    raise ValueError("Sector column remains in the final output.")

if any(isinstance(col, int) and col < START_YEAR for col in final_df.columns):
    raise ValueError("Columns before 1951 remain in the final output.")

if final_df["Country"].astype(str).str.lower().eq("global").any():
    raise ValueError("Global rows remain in the final output.")

if final_df["ISO3"].astype(str).str.upper().eq("WLD").any():
    raise ValueError("WLD/global ISO3 rows remain in the final output.")

if final_df[["Country", "ISO2", "ISO3"]].isna().any().any():
    missing = final_df[
        final_df[["Country", "ISO2", "ISO3"]].isna().any(axis=1)
    ][["Country", "ISO2", "ISO3", "Metric"]]

    raise ValueError(
        "Some rows are missing Country, ISO2 or ISO3 values:\n"
        f"{missing.to_string(index=False)}"
    )


# -------------------------------------------------------------------
# Save output
# -------------------------------------------------------------------
OUTPUTS_DIR.mkdir(exist_ok=True)
final_df.to_csv(output_path, index=False)

print(f"Done. File saved as: {output_path}")
print(f"WCA regional consumption loaded from: {wca_consumption_path}")
print(f"WCA country-region mapping loaded from: {wca_mapping_path}")
print(f"Cement demand rows saved: {len(final_df)}")
print(f"Population rows used in projection: {len(population_rows)}")
print(f"Historical cement years retained: {START_YEAR}-{BASE_YEAR}")
print(f"WCA projection years filled: {PROJECTION_START_YEAR}-{END_YEAR}")
print(f"WCA mapped countries: {len(wca_region_by_iso3)}")
print(f"WCA regional intensity imputations: {len(projection_imputations)}")
if projection_imputations:
    print("First regional intensity imputations:")
    for iso3, note in projection_imputations[:20]:
        print(f"  {iso3}: {note}")
print(f"WCA projection issues: {len(projection_issues)}")
if projection_issues:
    print("First projection issues:")
    for iso3, issue in projection_issues[:20]:
        print(f"  {iso3}: {issue}")
print("WCA regional totals from output, Mt:")
for year in [2024, 2035, 2050, 2100]:
    total_mt = cement_rows[year].sum(skipna=True) / 1000
    print(f"  {year}: {total_mt:.3f}")
print("Final columns:")
print(final_df.columns.tolist())
