from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
MAPS_DIR = BASE_DIR / "maps"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

INF_WORKBOOK_PATH = SHARED_INPUTS_DIR / "VT_OMNIA_IIS_INM_INF_v0.4.xlsx"
OMNIA_MAPPING_PATH = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"
OUTPUT_CSV = MAPS_DIR / "aluminium_primary_producers_zijie_region_map.csv"


COUNTRY_NAME_FIXES = {
    "Iran": "Iran (Islamic Republic of)",
    "Russia": "Russian Federation",
    "Turkey": "Turkey",
    "United Arab Emirates": "United Arab Emirates",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "United States": "United States of America",
    "Venezuela": "Venezuela (Bolivarian Republic of)",
}


def clean_country_name(country):
    country = str(country).strip()
    return COUNTRY_NAME_FIXES.get(country, country)


def main():
    inf_data = pd.read_excel(INF_WORKBOOK_PATH, sheet_name="INF_Data", header=None)
    omnia_mapping = pd.read_csv(OMNIA_MAPPING_PATH)

    if "ZijieRegion" not in omnia_mapping.columns:
        raise ValueError(
            "OMNIA mapping is missing ZijieRegion. Run "
            "add_zijie_regions_to_omnia_mapping.py first."
        )

    # Excel rows 168-208 hold the primary producer country table after the
    # header in row 167.
    primary = inf_data.iloc[167:208, 0:3].copy()
    primary.columns = ["Country_INF_Data", "OMNIARegion_INF_Data", "PrimaryProduction2019_kt"]
    primary = primary.dropna(subset=["Country_INF_Data", "OMNIARegion_INF_Data", "PrimaryProduction2019_kt"])
    primary["PrimaryProduction2019_kt"] = pd.to_numeric(
        primary["PrimaryProduction2019_kt"],
        errors="coerce",
    )
    primary = primary[
        primary["PrimaryProduction2019_kt"].notna() &
        (primary["PrimaryProduction2019_kt"] > 0)
    ].copy()

    primary["CountryForMatch"] = primary["Country_INF_Data"].apply(clean_country_name)

    country_lookup = (
        omnia_mapping
        .drop_duplicates(subset=["country_OMNIA", "region"])
        [["country_OMNIA", "region", "ISO2", "ISO3", "ZijieRegion"]]
        .rename(
            columns={
                "country_OMNIA": "CountryForMatch",
                "region": "OMNIARegion_INF_Data",
            }
        )
    )

    output = primary.merge(
        country_lookup,
        on=["CountryForMatch", "OMNIARegion_INF_Data"],
        how="left",
    )

    missing = output[output["ZijieRegion"].isna()]
    if not missing.empty:
        raise ValueError(
            "Could not map these primary producer rows:\n"
            f"{missing[['Country_INF_Data', 'OMNIARegion_INF_Data']].to_string(index=False)}"
        )

    output = output[
        [
            "Country_INF_Data",
            "CountryForMatch",
            "ISO2",
            "ISO3",
            "OMNIARegion_INF_Data",
            "ZijieRegion",
            "PrimaryProduction2019_kt",
        ]
    ].rename(
        columns={
            "CountryForMatch": "Country_OMNIA",
            "OMNIARegion_INF_Data": "OMNIARegion",
        }
    )

    output = output.sort_values(
        ["ZijieRegion", "PrimaryProduction2019_kt"],
        ascending=[True, False],
    ).reset_index(drop=True)

    output.to_csv(OUTPUT_CSV, index=False)

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Rows: {len(output)}")
    print("Production by Zijie region, kt:")
    print(
        output
        .groupby("ZijieRegion")["PrimaryProduction2019_kt"]
        .sum()
        .sort_index()
        .round(3)
        .to_string()
    )


if __name__ == "__main__":
    main()
