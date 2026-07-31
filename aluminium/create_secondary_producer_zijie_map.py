from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
MAPS_DIR = BASE_DIR / "maps"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

INF_WORKBOOK_PATH = SHARED_INPUTS_DIR / "VT_OMNIA_IIS_INM_INF_v0.4.xlsx"
OMNIA_MAPPING_PATH = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"
PRIMARY_PRODUCER_MAP_PATH = MAPS_DIR / "aluminium_primary_producers_zijie_region_map.csv"
OUTPUT_CSV = MAPS_DIR / "aluminium_secondary_producers_zijie_region_map.csv"

OMNIA_REGION_HEADER_ROW = 226
OMNIA_REGION_TOTAL_ROW = 231
OMNIA_REGION_FIRST_COLUMN = 6
OMNIA_REGION_LAST_COLUMN = 34
EXPECTED_OMNIA_WORLD_TOTAL_KT = 31_750.0


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
            "SecondaryAllocationWeight": float(production_kt),
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


def read_omnia_region_totals(inf_data):
    region_codes = inf_data.iloc[
        OMNIA_REGION_HEADER_ROW,
        OMNIA_REGION_FIRST_COLUMN:OMNIA_REGION_LAST_COLUMN,
    ].tolist()
    totals_mt = pd.to_numeric(
        inf_data.iloc[
            OMNIA_REGION_TOTAL_ROW,
            OMNIA_REGION_FIRST_COLUMN:OMNIA_REGION_LAST_COLUMN,
        ],
        errors="raise",
    ).tolist()
    totals = pd.DataFrame(
        {
            "OMNIARegion": region_codes,
            "OMNIARegionTotal2019_kt": [
                float(value) * 1000 for value in totals_mt
            ],
        }
    )

    if totals["OMNIARegion"].isna().any():
        raise ValueError("OMNIA secondary region header contains blank values.")
    if totals["OMNIARegion"].duplicated().any():
        duplicates = totals.loc[
            totals["OMNIARegion"].duplicated(keep=False),
            "OMNIARegion",
        ].tolist()
        raise ValueError(f"Duplicate OMNIA secondary regions: {duplicates}")
    if totals["OMNIARegionTotal2019_kt"].lt(0).any():
        raise ValueError("OMNIA secondary region totals contain negative values.")

    world_total = totals["OMNIARegionTotal2019_kt"].sum()
    if abs(world_total - EXPECTED_OMNIA_WORLD_TOTAL_KT) > 1e-6:
        raise ValueError(
            "OMNIA secondary region totals do not reproduce the expected "
            f"31.75 Mt. Found {world_total / 1000:.6f} Mt."
        )
    return totals


def map_secondary_weights(secondary, omnia_mapping):
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
    mapped = secondary.merge(
        country_lookup,
        on=["CountryForMatch", "OMNIARegion_INF_Data"],
        how="left",
        validate="many_to_one",
    )

    missing = mapped[mapped["ZijieRegion"].isna()]
    if not missing.empty:
        raise ValueError(
            "Could not map these secondary producer rows:\n"
            f"{missing[['Country_INF_Data', 'OMNIARegion_INF_Data']].to_string(index=False)}"
        )
    return mapped


def make_primary_fallback_weights():
    primary = pd.read_csv(PRIMARY_PRODUCER_MAP_PATH)
    required = {
        "Country_INF_Data",
        "Country_OMNIA",
        "ISO2",
        "ISO3",
        "OMNIARegion",
        "ZijieRegion",
        "PrimaryProduction2019_kt",
    }
    missing = required - set(primary.columns)
    if missing:
        raise ValueError(
            f"Primary producer map is missing columns: {sorted(missing)}"
        )

    primary["PrimaryProduction2019_kt"] = pd.to_numeric(
        primary["PrimaryProduction2019_kt"],
        errors="raise",
    )
    return primary[primary["PrimaryProduction2019_kt"].gt(0)].copy()


def allocate_omnia_totals(
    secondary_weights,
    primary_weights,
    omnia_mapping,
    omnia_totals,
):
    frames = []
    for target in omnia_totals.itertuples(index=False):
        if target.OMNIARegionTotal2019_kt == 0:
            continue

        secondary_rows = secondary_weights[
            secondary_weights["OMNIARegion_INF_Data"].eq(target.OMNIARegion)
            & secondary_weights["SecondaryAllocationWeight"].gt(0)
        ].copy()

        if not secondary_rows.empty:
            candidates = secondary_rows.rename(
                columns={
                    "CountryForMatch": "Country_OMNIA",
                    "OMNIARegion_INF_Data": "OMNIARegion",
                }
            )
            candidates["AllocationWeight"] = candidates[
                "SecondaryAllocationWeight"
            ]
            candidates["WeightSource"] = "Secondary country observation"
            candidates["AllocationMethod"] = (
                "OMNIA 2019 region total allocated using INF_Data "
                "secondary-country weights"
            )
        else:
            primary_rows = primary_weights[
                primary_weights["OMNIARegion"].eq(target.OMNIARegion)
            ].copy()
            if not primary_rows.empty:
                candidates = primary_rows
                candidates["AllocationWeight"] = candidates[
                    "PrimaryProduction2019_kt"
                ]
                candidates["WeightSource"] = "Primary production fallback"
                candidates["SourceDetail"] = (
                    "INF_Data 2019 primary production used only as a "
                    "within-OMNIA-region allocation weight"
                )
                candidates["AllocationMethod"] = (
                    "OMNIA 2019 region total allocated using OMNIA primary-"
                    "production shares; no secondary-country weights available"
                )
            else:
                region_countries = omnia_mapping[
                    omnia_mapping["region"].eq(target.OMNIARegion)
                ].drop_duplicates(subset="ISO3")
                if len(region_countries) != 1:
                    raise ValueError(
                        f"No secondary or primary country weights for "
                        f"{target.OMNIARegion}, which contains "
                        f"{len(region_countries)} countries."
                    )
                candidates = region_countries.rename(
                    columns={
                        "country_OMNIA": "Country_OMNIA",
                        "region": "OMNIARegion",
                    }
                ).copy()
                candidates["Country_INF_Data"] = candidates["Country_OMNIA"]
                candidates["AllocationWeight"] = 1.0
                candidates["WeightSource"] = "Single-country fallback"
                candidates["SourceDetail"] = (
                    "Full OMNIA region total assigned to its only country"
                )
                candidates["AllocationMethod"] = (
                    "OMNIA 2019 region total assigned to the sole country; "
                    "no secondary or primary weight available"
                )

        weight_total = candidates["AllocationWeight"].sum()
        if weight_total <= 0:
            raise ValueError(
                f"Non-positive allocation weight total for {target.OMNIARegion}."
            )
        candidates["OMNIARegionShare"] = (
            candidates["AllocationWeight"] / weight_total
        )
        candidates["OMNIARegionTotal2019_kt"] = (
            target.OMNIARegionTotal2019_kt
        )
        candidates["SecondaryProduction2019_kt"] = (
            candidates["OMNIARegionShare"]
            * candidates["OMNIARegionTotal2019_kt"]
        )
        frames.append(
            candidates[
                [
                    "Country_INF_Data",
                    "Country_OMNIA",
                    "ISO2",
                    "ISO3",
                    "OMNIARegion",
                    "ZijieRegion",
                    "SecondaryProduction2019_kt",
                    "OMNIARegionTotal2019_kt",
                    "OMNIARegionShare",
                    "AllocationWeight",
                    "WeightSource",
                    "AllocationMethod",
                    "SourceDetail",
                ]
            ]
        )

    output = pd.concat(frames, ignore_index=True)
    allocated = (
        output.groupby("OMNIARegion", as_index=False)[
            "SecondaryProduction2019_kt"
        ]
        .sum()
        .rename(columns={"SecondaryProduction2019_kt": "AllocatedTotal_kt"})
    )
    check = omnia_totals.merge(allocated, on="OMNIARegion", how="left")
    check["AllocatedTotal_kt"] = check["AllocatedTotal_kt"].fillna(0)
    check["Difference_kt"] = (
        check["AllocatedTotal_kt"] - check["OMNIARegionTotal2019_kt"]
    )
    max_difference = check["Difference_kt"].abs().max()
    if max_difference > 1e-6:
        raise ValueError(
            "Country allocations do not reproduce OMNIA 2019 region totals. "
            f"Max difference: {max_difference} kt."
        )
    return output


def main():
    inf_data = pd.read_excel(INF_WORKBOOK_PATH, sheet_name="INF_Data", header=None)
    omnia_mapping = pd.read_csv(OMNIA_MAPPING_PATH)

    if "ZijieRegion" not in omnia_mapping.columns:
        raise ValueError(
            "OMNIA mapping is missing ZijieRegion. Run "
            "add_zijie_regions_to_omnia_mapping.py first."
        )

    omnia_totals = read_omnia_region_totals(inf_data)
    secondary_weights = map_secondary_weights(
        read_secondary_records(inf_data),
        omnia_mapping,
    )
    primary_weights = make_primary_fallback_weights()
    output = allocate_omnia_totals(
        secondary_weights,
        primary_weights,
        omnia_mapping,
        omnia_totals,
    )

    output = output.sort_values(
        ["ZijieRegion", "SecondaryProduction2019_kt"],
        ascending=[True, False],
    ).reset_index(drop=True)

    output.to_csv(OUTPUT_CSV, index=False)

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Rows: {len(output)}")
    print(
        "OMNIA 2019 secondary total, Mt: "
        f"{output['SecondaryProduction2019_kt'].sum() / 1000:.3f}"
    )
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
