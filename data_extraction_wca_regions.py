import re
import numpy as np
import pandas as pd


# -------------------------------------------------------------------
# File paths
# -------------------------------------------------------------------
pop_path = "undesa_pop.xlsx"

cement_url = (
    "https://zenodo.org/records/20397304/files/"
    "1.%20annual_cement_production.csv?download=1"
)

output_path = "cement_demand_with_population_wca_regions.xlsx"
wca_mapping_output_path = "wca_country_region_mapping.csv"


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


# Regional cement consumption from the WCA table extracted to cement.docx.
# Units are Mtpa. The table header has a typo ("20235"), interpreted as 2035.
WCA_REGION_CONSUMPTION_MTPA = {
    "China": {2020: 2411, 2024: 1825, 2035: 1183, 2050: 928},
    "North America": {2020: 115, 2024: 120, 2035: 131, 2050: 138},
    "W Europe": {2020: 131, 2024: 126, 2035: 129, 2050: 125},
    "E Europe & Turkey": {2020: 120, 2024: 127, 2035: 129, 2050: 125},
    "Oceania": {2020: 12, 2024: 12, 2035: 13, 2050: 14},
    "NE Asia": {2020: 97, 2024: 97, 2035: 89, 2050: 85},
    "SE Asia": {2020: 236, 2024: 240, 2035: 275, 2050: 297},
    "North Africa": {2020: 93, 2024: 97, 2035: 111, 2050: 131},
    "Latin America": {2020: 164, 2024: 176, 2035: 202, 2050: 215},
    "CIS": {2020: 97, 2024: 116, 2035: 127, 2050: 136},
    "Middle East": {2020: 196, 2024: 208, 2035: 235, 2050: 254},
    "South Asia": {2020: 392, 2024: 537, 2035: 813, 2050: 908},
    "Sub Saharan Africa": {2020: 130, 2024: 153, 2035: 207, 2050: 308},
}


WCA_REGION_BY_OMNIA = {
    "AFE": "Sub Saharan Africa",
    "AFN": "North Africa",
    "AFW": "Sub Saharan Africa",
    "AFZ": "Sub Saharan Africa",
    "ANZ": "Oceania",
    "ASC": "CIS",
    "ASE": "SE Asia",
    "ASO": "South Asia",
    "BRA": "Latin America",
    "CAN": "North America",
    "CHL": "Latin America",
    "CHN": "China",
    "ENE": "E Europe & Turkey",
    "ENW": "W Europe",
    "EUE": "E Europe & Turkey",
    "EUM": "W Europe",
    "EUW": "W Europe",
    "IDN": "SE Asia",
    "IND": "South Asia",
    "JPN": "NE Asia",
    "LAM": "Latin America",
    "MDA": "Middle East",
    "MEA": "Middle East",
    "MEX": "Latin America",
    "NIG": "Sub Saharan Africa",
    "RUS": "CIS",
    "SKT": "NE Asia",
    "USA": "North America",
}


WCA_REGION_BY_ISO3_OVERRIDE = {
    # WCA-specific split from the broader OMNIA Middle East group.
    "TUR": "E Europe & Turkey",

    # Pacific islands assigned to Oceania rather than the broader OMNIA SE Asia group.
    "COK": "Oceania",
    "FJI": "Oceania",
    "FSM": "Oceania",
    "KIR": "Oceania",
    "MHL": "Oceania",
    "NCL": "Oceania",
    "NRU": "Oceania",
    "NIU": "Oceania",
    "PLW": "Oceania",
    "PNG": "Oceania",
    "PYF": "Oceania",
    "SLB": "Oceania",
    "TON": "Oceania",
    "TUV": "Oceania",
    "VUT": "Oceania",
    "WLF": "Oceania",
    "WSM": "Oceania",

    # Countries and territories absent from the GDP/OMNIA file.
    "AFG": "South Asia",
    "AIA": "Latin America",
    "AND": "W Europe",
    "BES": "Latin America",
    "BMU": "North America",
    "CYM": "Latin America",
    "CUW": "Latin America",
    "DMA": "Latin America",
    "FLK": "Latin America",
    "FRO": "W Europe",
    "GIB": "W Europe",
    "GLP": "Latin America",
    "GRL": "North America",
    "GUF": "Latin America",
    "KNA": "Latin America",
    "LIE": "W Europe",
    "MSR": "Latin America",
    "MTQ": "Latin America",
    "PSE": "Middle East",
    "REU": "Sub Saharan Africa",
    "SHN": "Sub Saharan Africa",
    "SPM": "North America",
    "SXM": "Latin America",
    "SYR": "Middle East",
    "TCA": "Latin America",
    "VGB": "Latin America",
}


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


def wca_region_total_kt(region, year):
    """
    Return WCA regional cement consumption target in kt.

    Values are linearly interpolated between WCA table years and held constant
    after 2050 because the source table stops there.
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


def build_wca_region_map(country_ref):
    """
    Map countries to WCA regions using ISO overrides and OMNIA groups.
    """
    try:
        gdp = read_excel_normalised("gdp_projection_country_SSP2.xlsx")
        omnia_by_iso3 = (
            gdp[["ISO3", "OMNIA"]]
            .dropna(subset=["ISO3", "OMNIA"])
            .assign(ISO3=lambda df: df["ISO3"].astype(str).str.strip())
            .set_index("ISO3")["OMNIA"]
            .to_dict()
        )
    except FileNotFoundError:
        omnia_by_iso3 = {}

    mapping = {}
    unmapped = []

    for iso3 in country_ref["ISO3"]:
        if iso3 in WCA_REGION_BY_ISO3_OVERRIDE:
            mapping[iso3] = WCA_REGION_BY_ISO3_OVERRIDE[iso3]
            continue

        omnia = omnia_by_iso3.get(iso3)
        region = WCA_REGION_BY_OMNIA.get(omnia)
        if region:
            mapping[iso3] = region
        else:
            unmapped.append(iso3)

    return mapping, unmapped


def project_cement_demand_wca(cement_rows, population_rows, country_ref, start_year, end_year):
    """
    Project country cement demand by preserving regional country shares against
    WCA regional totals.
    """
    projected = cement_rows.copy()
    population_by_iso3 = population_rows.set_index("ISO3")
    wca_region_by_iso3, unmapped = build_wca_region_map(country_ref)
    projected["WCARegion"] = projected["ISO3"].map(wca_region_by_iso3)

    projection_issues = [(iso3, "missing WCA region mapping") for iso3 in unmapped]
    projection_imputations = []

    if projected["WCARegion"].isna().any():
        for iso3 in projected.loc[projected["WCARegion"].isna(), "ISO3"]:
            projection_issues.append((iso3, "missing WCA region mapping"))

    base_weights = {}

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

            if pd.notna(base_demand) and base_demand > 0:
                weight = base_demand
            else:
                population = population_by_iso3.at[iso3, BASE_YEAR]
                if pd.isna(population) or population <= 0 or pd.isna(regional_intensity):
                    projection_issues.append((iso3, "no WCA base allocation weight"))
                    continue

                weight = regional_intensity * population
                projection_imputations.append(
                    (iso3, f"regional average base intensity from {region}")
                )

            base_weights[iso3] = weight

    weight_by_region = {}
    for iso3, weight in base_weights.items():
        region = wca_region_by_iso3[iso3]
        weight_by_region[region] = weight_by_region.get(region, 0) + weight

    for idx, row in projected.iterrows():
        iso3 = row["ISO3"]
        region = row["WCARegion"]

        if pd.isna(region) or iso3 not in base_weights:
            continue

        region_weight = weight_by_region.get(region, 0)
        if region_weight <= 0:
            projection_issues.append((iso3, f"zero regional allocation weight for {region}"))
            continue

        country_share = base_weights[iso3] / region_weight

        for year in range(start_year, end_year + 1):
            projected.at[idx, year] = country_share * wca_region_total_kt(region, year)

    projected = projected.drop(columns=["WCARegion"])

    return projected, projection_issues, projection_imputations, wca_region_by_iso3


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
# Project cement demand using WCA regional table
# -------------------------------------------------------------------
cement_rows, projection_issues, projection_imputations, wca_region_by_iso3 = (
    project_cement_demand_wca(
        cement_rows=cement_rows,
        population_rows=population_rows,
        country_ref=country_ref,
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

wca_mapping_df = country_ref[["Country", "ISO2", "ISO3"]].copy()
wca_mapping_df["WCARegion"] = wca_mapping_df["ISO3"].map(wca_region_by_iso3)
wca_mapping_df = wca_mapping_df.sort_values(["WCARegion", "Country"])
wca_mapping_df.to_csv(wca_mapping_output_path, index=False)

print(f"Done. File saved as: {output_path}")
print(f"WCA country-region mapping saved as: {wca_mapping_output_path}")
print(f"Cement demand rows added: {len(cement_rows)}")
print(f"Population rows added: {len(population_rows)}")
print(f"Final rows: {len(final_df)}")
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
