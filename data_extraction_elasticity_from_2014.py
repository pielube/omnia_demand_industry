import re
import numpy as np
import pandas as pd


# -------------------------------------------------------------------
# File paths
# -------------------------------------------------------------------
pop_path = "undesa_pop.xlsx"
gdp_path = "gdp_projection_country_SSP2.xlsx"

cement_url = (
    "https://zenodo.org/records/20397304/files/"
    "1.%20annual_cement_production.csv?download=1"
)

output_path = "cement_demand_with_population_elasticity_from_2014.xlsx"


# -------------------------------------------------------------------
# User settings
# -------------------------------------------------------------------
START_YEAR = 1951
END_YEAR = 2100
BASE_YEAR = 2014
PROJECTION_START_YEAR = BASE_YEAR + 1
GDP_BACKCAST_END_YEAR = 2019
GDP_BACKCAST_CAGR_END_YEAR = 2024

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

    required_columns = {"Country", "ISO2", "ISO3", "OMNIA"}
    missing_columns = required_columns - set(gdp.columns)
    if missing_columns:
        raise ValueError(
            "GDP projection file is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    gdp["ISO3"] = gdp["ISO3"].astype(str).str.strip()
    gdp = remove_global_rows(gdp)

    return gdp


def make_regional_base_intensities(cement_rows, population_rows, gdp, base_year):
    """
    Calculate population-weighted cement intensities by OMNIA region.
    """
    gdp_regions = gdp[["ISO3", "OMNIA"]].dropna(subset=["ISO3", "OMNIA"]).copy()
    gdp_regions["ISO3"] = gdp_regions["ISO3"].astype(str).str.strip()

    cement_base = cement_rows[["ISO3", base_year]].copy()
    population_base = population_rows[["ISO3", base_year]].copy()

    base = (
        cement_base
        .merge(population_base, on="ISO3", suffixes=("_cement", "_population"))
        .merge(gdp_regions, on="ISO3", how="left")
    )

    cement_col = f"{base_year}_cement"
    population_col = f"{base_year}_population"

    base = base[
        base[cement_col].notna() &
        base[population_col].notna() &
        (base[cement_col] > 0) &
        (base[population_col] > 0) &
        base["OMNIA"].notna()
    ].copy()

    regional = (
        base
        .groupby("OMNIA")[[cement_col, population_col]]
        .sum()
    )
    regional["cement_per_capita"] = (
        regional[cement_col] / regional[population_col]
    )

    global_cement_per_capita = (
        base[cement_col].sum() / base[population_col].sum()
        if not base.empty
        else np.nan
    )

    return regional["cement_per_capita"].to_dict(), global_cement_per_capita


def backcast_gdp_to_base_year(gdp, population_rows, base_year):
    """
    Backcast GDP to the base year using country GDP-per-capita CAGR.

    The available GDP file starts in 2019. For a 2014 cement-intensity anchor,
    this estimates 2014-2018 GDP per capita from the 2019-2024 GDP-per-capita
    CAGR, then converts back to total GDP using UN DESA population.
    """
    gdp = gdp.copy()
    gdp_by_iso3 = gdp.set_index("ISO3")
    population_by_iso3 = population_rows.set_index("ISO3")
    backcast_issues = []

    for year in range(base_year, GDP_BACKCAST_END_YEAR):
        if year not in gdp.columns:
            gdp[year] = np.nan

    for idx, row in gdp.iterrows():
        iso3 = row["ISO3"]
        if iso3 not in population_by_iso3.index:
            backcast_issues.append((iso3, "missing population row"))
            continue

        required_columns = [
            GDP_BACKCAST_END_YEAR,
            GDP_BACKCAST_CAGR_END_YEAR,
        ]
        if any(year not in gdp_by_iso3.columns for year in required_columns):
            backcast_issues.append((iso3, "missing GDP CAGR endpoint"))
            continue

        start_gdp = row[GDP_BACKCAST_END_YEAR]
        end_gdp = row[GDP_BACKCAST_CAGR_END_YEAR]
        start_population = population_by_iso3.at[iso3, GDP_BACKCAST_END_YEAR]
        end_population = population_by_iso3.at[iso3, GDP_BACKCAST_CAGR_END_YEAR]

        required_values = [start_gdp, end_gdp, start_population, end_population]
        if any(pd.isna(value) or value <= 0 for value in required_values):
            backcast_issues.append((iso3, "missing/zero GDP CAGR input"))
            continue

        start_gdp_per_capita = start_gdp / start_population
        end_gdp_per_capita = end_gdp / end_population
        cagr_years = GDP_BACKCAST_CAGR_END_YEAR - GDP_BACKCAST_END_YEAR
        growth_factor = (end_gdp_per_capita / start_gdp_per_capita) ** (1 / cagr_years)

        if pd.isna(growth_factor) or growth_factor <= 0:
            backcast_issues.append((iso3, "invalid GDP per capita CAGR"))
            continue

        next_gdp_per_capita = start_gdp_per_capita
        for year in reversed(range(base_year, GDP_BACKCAST_END_YEAR)):
            current_population = population_by_iso3.at[iso3, year]
            if pd.isna(current_population) or current_population <= 0:
                backcast_issues.append((iso3, f"missing/zero population in {year}"))
                break

            current_gdp_per_capita = next_gdp_per_capita / growth_factor
            gdp.at[idx, year] = current_gdp_per_capita * current_population
            next_gdp_per_capita = current_gdp_per_capita

    gdp.columns = [normalise_year_column_name(c) for c in gdp.columns]

    return gdp, backcast_issues


def project_cement_demand_from_base(cement_rows, population_rows, gdp, base_year, end_year):
    """
    Project annual cement demand from a fixed base-year cement intensity.
    """
    projected = cement_rows.copy()

    gdp_by_iso3 = gdp.set_index("ISO3")
    population_by_iso3 = population_rows.set_index("ISO3")

    projection_issues = []
    projection_imputations = []
    regional_base_intensities, global_base_intensity = make_regional_base_intensities(
        cement_rows=cement_rows,
        population_rows=population_rows,
        gdp=gdp,
        base_year=base_year,
    )

    for idx, row in projected.iterrows():
        iso3 = row["ISO3"]

        if iso3 not in gdp_by_iso3.index:
            projection_issues.append((iso3, "missing GDP projection"))
            continue

        if iso3 not in population_by_iso3.index:
            projection_issues.append((iso3, "missing population row"))
            continue

        base_population = population_by_iso3.at[iso3, base_year]
        if pd.isna(base_population) or base_population <= 0:
            projection_issues.append((iso3, f"missing/zero population in {base_year}"))
            continue

        if pd.notna(row[base_year]) and row[base_year] > 0:
            cement_per_capita = row[base_year] / base_population
        else:
            region = gdp_by_iso3.at[iso3, "OMNIA"] if "OMNIA" in gdp_by_iso3.columns else np.nan
            cement_per_capita = regional_base_intensities.get(region, global_base_intensity)

            if pd.isna(cement_per_capita) or cement_per_capita <= 0:
                projection_issues.append((iso3, "no regional base cement intensity"))
                continue

            projection_imputations.append((iso3, f"regional average base intensity from {region}"))

        for year in range(base_year + 1, end_year + 1):
            previous_year = year - 1

            if year not in population_by_iso3.columns:
                projection_issues.append((iso3, f"missing population column {year}"))
                break

            if year not in gdp_by_iso3.columns or previous_year not in gdp_by_iso3.columns:
                projection_issues.append((iso3, f"missing GDP column {previous_year}/{year}"))
                break

            previous_population = population_by_iso3.at[iso3, previous_year]
            current_population = population_by_iso3.at[iso3, year]
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

            projected.at[idx, year] = cement_per_capita * current_population

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
# Backcast GDP to support a 2014 projection anchor
# -------------------------------------------------------------------
gdp, gdp_backcast_issues = backcast_gdp_to_base_year(
    gdp=gdp,
    population_rows=population_rows,
    base_year=BASE_YEAR,
)


# -------------------------------------------------------------------
# Project cement demand from 2014 using elasticity
# -------------------------------------------------------------------
cement_rows, projection_issues, projection_imputations = project_cement_demand_from_base(
    cement_rows=cement_rows,
    population_rows=population_rows,
    gdp=gdp,
    base_year=BASE_YEAR,
    end_year=END_YEAR,
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
# Combine cement demand and population
# -------------------------------------------------------------------
final_df = pd.concat(
    [
        cement_rows,
        population_rows
    ],
    ignore_index=True
)

final_df = remove_global_rows(final_df)


# -------------------------------------------------------------------
# Sort output
# -------------------------------------------------------------------
final_df = final_df.sort_values(
    by=["Country", "Metric"]
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
final_df.to_excel(output_path, index=False)

print(f"Done. File saved as: {output_path}")
print(f"Cement demand rows added: {len(cement_rows)}")
print(f"Population rows added: {len(population_rows)}")
print(f"Final rows: {len(final_df)}")
print(f"Historical cement years retained: {START_YEAR}-{BASE_YEAR}")
print(f"Elasticity projection years filled: {PROJECTION_START_YEAR}-{END_YEAR}")
print(f"GDP backcast years estimated: {BASE_YEAR}-{GDP_BACKCAST_END_YEAR - 1}")
print(f"GDP backcast issues: {len(gdp_backcast_issues)}")
if gdp_backcast_issues:
    print("First GDP backcast issues:")
    for iso3, issue in gdp_backcast_issues[:20]:
        print(f"  {iso3}: {issue}")
print(f"Cement projection regional intensity imputations: {len(projection_imputations)}")
if projection_imputations:
    print("First regional intensity imputations:")
    for iso3, note in projection_imputations[:20]:
        print(f"  {iso3}: {note}")
print(f"Cement projection issues: {len(projection_issues)}")
if projection_issues:
    print("First projection issues:")
    for iso3, issue in projection_issues[:20]:
        print(f"  {iso3}: {issue}")
print("Final columns:")
print(final_df.columns.tolist())
