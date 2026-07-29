from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MAPS_DIR = BASE_DIR / "maps"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

INPUT_PATH = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"
SUMMARY_PATH = MAPS_DIR / "zijie_region_mapping_summary.csv"


# Zijie's regions follow Bertram et al. (2017), with the UK separated from
# Europe. Region names are matched to the 10-region aluminium scenario workbook.
EU28_ISO3 = {
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN",
    "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX",
    "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE",
    "GBR",
}

ZIJIE_REGION_BY_ISO3 = {
    # Bertram: Mainland China. Hong Kong and Macao are therefore left as ROW.
    "CHN": "China",

    # Zijie modification to Bertram: UK split from Europe.
    "GBR": "UK",

    # Bertram: North America.
    "CAN": "North America",
    "MEX": "North America",
    "USA": "North America",

    # Bertram: Middle East.
    "BHR": "Middle East",
    "OMN": "Middle East",
    "QAT": "Middle East",
    "SAU": "Middle East",
    "ARE": "Middle East",
    "IRN": "Middle East",

    # Bertram: Japan.
    "JPN": "Japan",

    # Bertram: Other Asia.
    "IND": "Other Asia",
    "IDN": "Other Asia",
    "MYS": "Other Asia",
    "PAK": "Other Asia",
    "SGP": "Other Asia",
    "KOR": "Other Asia",
    "TWN": "Other Asia",
    "THA": "Other Asia",
    "VNM": "Other Asia",

    # Bertram: Other Producing Countries. The scenario workbook calls this
    # region "Other main producer".
    "AUS": "Other main producer",
    "AZE": "Other main producer",
    "CMR": "Other main producer",
    "EGY": "Other main producer",
    "FJI": "Other main producer",
    "GIN": "Other main producer",
    "KAZ": "Other main producer",
    "NZL": "Other main producer",
    "RUS": "Other main producer",
    "SLE": "Other main producer",
    "ZAF": "Other main producer",
    "TZA": "Other main producer",
    "ZWE": "Other main producer",

    # Bertram: South America.
    "ARG": "South America",
    "BRA": "South America",
    "DOM": "South America",
    "GUY": "South America",
    "HTI": "South America",
    "JAM": "South America",
    "SUR": "South America",
    "VEN": "South America",
}


EXTRA_EUROPE_ISO3 = {
    "ISL",  # Iceland
    "MKD",  # Macedonia / North Macedonia
    "MDA",  # Moldavia / Moldova
    "NOR",  # Norway
    "SRB",  # Serbia-Montenegro split
    "MNE",  # Serbia-Montenegro split
    "CHE",  # Switzerland
    "TUR",  # Turkey
    "UKR",  # Ukraine
}


def zijie_region_for_iso3(iso3):
    iso3 = str(iso3).strip().upper()

    if iso3 in ZIJIE_REGION_BY_ISO3:
        return ZIJIE_REGION_BY_ISO3[iso3]

    if iso3 in EU28_ISO3 - {"GBR"} or iso3 in EXTRA_EUROPE_ISO3:
        return "Europe"

    return "Rest of World"


def main():
    mapping = pd.read_csv(INPUT_PATH)
    required_columns = {"region", "country_OMNIA", "ISO2", "ISO3"}
    missing = required_columns - set(mapping.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    mapping["ZijieRegion"] = mapping["ISO3"].apply(zijie_region_for_iso3)
    mapping.to_csv(INPUT_PATH, index=False)

    summary = (
        mapping
        .groupby("ZijieRegion", as_index=False)
        .agg(
            Rows=("ISO3", "count"),
            UniqueISO3=("ISO3", "nunique"),
            ISO3List=("ISO3", lambda values: ", ".join(dict.fromkeys(values))),
        )
        .sort_values("ZijieRegion")
    )
    summary.to_csv(SUMMARY_PATH, index=False)

    print(f"Updated: {INPUT_PATH}")
    print(f"Summary saved: {SUMMARY_PATH}")
    print(summary[["ZijieRegion", "Rows", "UniqueISO3"]].to_string(index=False))


if __name__ == "__main__":
    main()
