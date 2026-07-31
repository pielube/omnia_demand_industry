from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
MAPS_DIR = BASE_DIR / "maps"
SHARED_INPUTS_DIR = BASE_DIR.parent / "shared_inputs"

OMNIA_MAPPING_PATH = SHARED_INPUTS_DIR / "OMNIA_region_mapping_241120.csv"
SECONDARY_PRODUCER_MAP_PATH = MAPS_DIR / "aluminium_secondary_producers_zijie_region_map.csv"
ZIJIE_SCENARIO_PATH = INPUTS_DIR / "10 regions Al data.xlsx"
INF_WORKBOOK_PATH = SHARED_INPUTS_DIR / "VT_OMNIA_IIS_INM_INF_v0.4.xlsx"

SCENARIO_SHEET = "baseline"
SCENARIO_LABEL = "Secondary Al ingot (kt)"
METRIC = "Secondary aluminium ingot production"
UNIT = "kt"

BASE_YEAR = 2019
FIRST_ZIJIE_YEAR = 2024
END_YEAR = 2050
YEARS = list(range(BASE_YEAR, END_YEAR + 1))
ZIJIE_YEARS = list(range(FIRST_ZIJIE_YEAR, END_YEAR + 1))

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


def read_zijie_secondary_scenario():
    raw = pd.read_excel(ZIJIE_SCENARIO_PATH, sheet_name=SCENARIO_SHEET, header=None)
    matches = raw.iloc[0].eq(SCENARIO_LABEL)
    if matches.sum() != 1:
        raise ValueError(f"Could not find one block labelled {SCENARIO_LABEL!r}.")

    start_col = int(matches[matches].index[0])
    scenario = raw.iloc[1:, start_col:start_col + 1 + len(ZIJIE_REGIONS)].copy()
    scenario.columns = ["Year"] + ZIJIE_REGIONS
    scenario = scenario[scenario["Year"].isin(ZIJIE_YEARS)].copy()
    scenario["Year"] = scenario["Year"].astype(int)
    return scenario


def make_country_frame():
    mapping = pd.read_csv(OMNIA_MAPPING_PATH)
    required_columns = {"region", "country_OMNIA", "ISO2", "ISO3", "ZijieRegion"}
    missing = required_columns - set(mapping.columns)
    if missing:
        raise ValueError(f"OMNIA mapping is missing columns: {sorted(missing)}")

    countries = mapping.rename(
        columns={
            "region": "OMNIARegion",
            "country_OMNIA": "Country",
        }
    ).copy()
    countries["Metric"] = METRIC
    countries["Unit"] = UNIT
    return countries


def make_allocation_weights():
    producer_map = pd.read_csv(SECONDARY_PRODUCER_MAP_PATH)
    required_columns = {
        "ISO3",
        "ZijieRegion",
        "SecondaryProduction2019_kt",
        "AllocationMethod",
    }
    missing = required_columns - set(producer_map.columns)
    if missing:
        raise ValueError(f"Secondary producer map is missing columns: {sorted(missing)}")

    weights = producer_map[
        [
            "ISO3",
            "ZijieRegion",
            "SecondaryProduction2019_kt",
            "AllocationMethod",
        ]
    ].copy()
    weights["SecondaryProduction2019_kt"] = pd.to_numeric(
        weights["SecondaryProduction2019_kt"],
        errors="coerce",
    ).fillna(0)
    weights = weights[weights["SecondaryProduction2019_kt"] > 0].copy()
    missing_regions = sorted(set(ZIJIE_REGIONS) - set(weights["ZijieRegion"]))
    if missing_regions:
        raise ValueError(
            "OMNIA-allocated secondary producer map has no countries in "
            f"these Zijie regions: {missing_regions}"
        )

    region_weight_totals = (
        weights
        .groupby("ZijieRegion")["SecondaryProduction2019_kt"]
        .sum()
        .to_dict()
    )

    weights["RegionShare"] = weights.apply(
        lambda row: row["SecondaryProduction2019_kt"] / region_weight_totals[row["ZijieRegion"]],
        axis=1,
    )

    return weights[
        ["ISO3", "ZijieRegion", "SecondaryProduction2019_kt", "RegionShare", "AllocationMethod"]
    ]


def read_omnia_2019_region_totals():
    inf_data = pd.read_excel(
        INF_WORKBOOK_PATH,
        sheet_name="INF_Data",
        header=None,
    )
    region_codes = inf_data.iloc[226, 6:34].tolist()
    totals_kt = (
        pd.to_numeric(inf_data.iloc[231, 6:34], errors="raise") * 1000
    ).tolist()
    return dict(zip(region_codes, totals_kt))


def build_projection():
    countries = make_country_frame()
    scenario = read_zijie_secondary_scenario()
    weights = make_allocation_weights()

    output = countries.merge(
        weights,
        on=["ISO3", "ZijieRegion"],
        how="left",
    )
    output["SecondaryProduction2019_kt"] = output["SecondaryProduction2019_kt"].fillna(0)
    output["RegionShare"] = output["RegionShare"].fillna(0)
    output["AllocationMethod"] = output["AllocationMethod"].fillna(
        "No 2019 secondary producer share; assigned zero"
    )

    for year in YEARS:
        output[year] = 0.0

    output[BASE_YEAR] = output["SecondaryProduction2019_kt"]

    scenario_by_year = scenario.set_index("Year")
    for year in ZIJIE_YEARS:
        output[year] = output.apply(
            lambda row: scenario_by_year.at[year, row["ZijieRegion"]] * row["RegionShare"],
            axis=1,
        )

    for year in range(BASE_YEAR + 1, FIRST_ZIJIE_YEAR):
        fraction = (year - BASE_YEAR) / (FIRST_ZIJIE_YEAR - BASE_YEAR)
        output[year] = output[BASE_YEAR] + (output[FIRST_ZIJIE_YEAR] - output[BASE_YEAR]) * fraction

    output = output[
        [
            "Country",
            "ISO2",
            "ISO3",
            "OMNIARegion",
            "ZijieRegion",
            "Metric",
            "Unit",
            "SecondaryProduction2019_kt",
            "RegionShare",
            "AllocationMethod",
        ] + YEARS
    ]

    return output, scenario


def make_total_checks(output, scenario):
    rows = []
    omnia_targets = read_omnia_2019_region_totals()
    for region, target in omnia_targets.items():
        allocated = output.loc[output["OMNIARegion"].eq(region), BASE_YEAR].sum()
        rows.append(
            {
                "CheckType": "OMNIARegion",
                "ZijieRegion": region,
                "Year": BASE_YEAR,
                "AllocatedTotal_kt": allocated,
                "ZijieTotal_kt": target,
                "Difference_kt": allocated - target,
            }
        )

    for year in ZIJIE_YEARS:
        allocated_total = output[year].sum()
        zijie_total = scenario.loc[scenario["Year"].eq(year), ZIJIE_REGIONS].sum(axis=1).iloc[0]
        rows.append(
            {
                "CheckType": "Global",
                "ZijieRegion": "World",
                "Year": year,
                "AllocatedTotal_kt": allocated_total,
                "ZijieTotal_kt": zijie_total,
                "Difference_kt": allocated_total - zijie_total,
            }
        )

        for region in ZIJIE_REGIONS:
            allocated_region = output.loc[output["ZijieRegion"].eq(region), year].sum()
            zijie_region = scenario.loc[scenario["Year"].eq(year), region].iloc[0]
            rows.append(
                {
                    "CheckType": "Region",
                    "ZijieRegion": region,
                    "Year": year,
                    "AllocatedTotal_kt": allocated_region,
                    "ZijieTotal_kt": zijie_region,
                    "Difference_kt": allocated_region - zijie_region,
                }
            )

    checks = pd.DataFrame(rows)
    max_difference = checks["Difference_kt"].abs().max()
    if max_difference > 1e-6:
        raise ValueError(f"Allocated totals do not match Zijie totals. Max diff: {max_difference}")
    return checks
