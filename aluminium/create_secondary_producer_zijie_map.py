from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
MAPS_DIR = BASE_DIR / "maps"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

INF_WORKBOOK_PATH = SHARED_INPUTS_DIR / "VT_OMNIA_IIS_INM_INF_v0.4.xlsx"
OMNIA_MAPPING_PATH = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"
OUTPUT_CSV = MAPS_DIR / "aluminium_secondary_producers_zijie_region_map.csv"


COUNTRY_NAME_FIXES = {
    "Russia": "Russian Federation",
    "South Korea": "Republic of Korea",
    "Turkey": "Turkey",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "United States": "United States of America",
    "Vietnam": "Viet Nam",
}


def clean_country_name(country):
    country = str(country).strip()
    return COUNTRY_NAME_FIXES.get(country, country)


def add_record(records, country, omnia_region, production_kt, source):
    production_kt = pd.to_numeric(production_kt, errors="coerce")
    if pd.isna(production_kt) or production_kt <= 0:
        return

    records.append(
        {
            "Country_INF_Data": str(country).strip(),
            "CountryForMatch": clean_country_name(country),
            "OMNIARegion_INF_Data": str(omnia_region).strip(),
            "SecondaryProduction2019_kt": float(production_kt),
            "SourceDetail": source,
        }
    )


def read_secondary_records(inf_data):
    records = []

    # Regional entries that correspond to one country.
    add_record(
        records,
        "China",
        "CHN",
        inf_data.iloc[226, 1] * 1000,
        "INF_Data row 227, China regional secondary total in Mt",
    )
    add_record(
        records,
        "Japan",
        "JPN",
        inf_data.iloc[228, 1] * 1000,
        "INF_Data row 229, Japan regional secondary total in Mt",
    )

    # North America: use US 2019 secondary recovery total and allocate the
    # residual regional total to Canada, following the methodology note.
    north_america_total_kt = inf_data.iloc[231, 1] * 1000
    us_secondary_kt = inf_data.iloc[246, 11]
    add_record(
        records,
        "United States",
        "USA",
        us_secondary_kt,
        "INF_Data row 247, USGS 2019 secondary recovery total in kt",
    )
    add_record(
        records,
        "Canada",
        "CAN",
        north_america_total_kt - us_secondary_kt,
        "INF_Data row 232 regional total minus row 247 US total",
    )

    # Other Asia values are reported in Mt in column D.
    for _, row in inf_data.iloc[251:260, [0, 1, 3]].iterrows():
        country, omnia_region, production_mt = row.tolist()
        add_record(
            records,
            country,
            omnia_region,
            pd.to_numeric(production_mt, errors="coerce") * 1000,
            "INF_Data rows 252-260, Other Asia secondary value in Mt",
        )

    # South America values are reported in Mt in column C.
    for _, row in inf_data.iloc[262:270, [0, 1, 2]].iterrows():
        country, omnia_region, production_mt = row.tolist()
        add_record(
            records,
            country,
            omnia_region,
            pd.to_numeric(production_mt, errors="coerce") * 1000,
            "INF_Data rows 263-270, South America secondary value in Mt",
        )

    # Europe values are reported in kt in column D.
    for _, row in inf_data.iloc[293:343, [0, 1, 3]].iterrows():
        country, omnia_region, production_kt = row.tolist()
        add_record(
            records,
            country,
            omnia_region,
            production_kt,
            "INF_Data rows 294-343, Europe secondary value in kt",
        )

    return pd.DataFrame(records)


def main():
    inf_data = pd.read_excel(INF_WORKBOOK_PATH, sheet_name="INF_Data", header=None)
    omnia_mapping = pd.read_csv(OMNIA_MAPPING_PATH)

    if "ZijieRegion" not in omnia_mapping.columns:
        raise ValueError(
            "OMNIA mapping is missing ZijieRegion. Run "
            "add_zijie_regions_to_omnia_mapping.py first."
        )

    secondary = read_secondary_records(inf_data)

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

    output = secondary.merge(
        country_lookup,
        on=["CountryForMatch", "OMNIARegion_INF_Data"],
        how="left",
    )

    missing = output[output["ZijieRegion"].isna()]
    if not missing.empty:
        raise ValueError(
            "Could not map these secondary producer rows:\n"
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
            "SecondaryProduction2019_kt",
            "SourceDetail",
        ]
    ].rename(
        columns={
            "CountryForMatch": "Country_OMNIA",
            "OMNIARegion_INF_Data": "OMNIARegion",
        }
    )

    output = output.sort_values(
        ["ZijieRegion", "SecondaryProduction2019_kt"],
        ascending=[True, False],
    ).reset_index(drop=True)

    output.to_csv(OUTPUT_CSV, index=False)

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Rows: {len(output)}")
    print("Production by Zijie region, kt:")
    print(
        output
        .groupby("ZijieRegion")["SecondaryProduction2019_kt"]
        .sum()
        .sort_index()
        .round(3)
        .to_string()
    )


if __name__ == "__main__":
    main()
