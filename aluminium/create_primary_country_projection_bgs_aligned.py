from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"

OLD_PROJECTION_PATH = OUTPUTS_DIR / "aluminium_primary_country_projection_2019_2050.csv"
BGS_HISTORY_PATH = INPUTS_DIR / "bgs_primary_aluminium_2020_2024.csv"
ZIJIE_SCENARIO_PATH = INPUTS_DIR / "10 regions Al data.xlsx"

OUTPUT_CSV = (
    OUTPUTS_DIR / "aluminium_primary_country_projection_bgs_aligned_2019_2050.csv"
)
MISALIGNMENT_CSV = (
    OUTPUTS_DIR / "aluminium_primary_bgs_vs_omnia_2019_misalignment.csv"
)
ZIJIE_REBASE_DIAGNOSTIC_CSV = (
    OUTPUTS_DIR / "aluminium_primary_zijie_2024_linear_rebase_diagnostic.csv"
)

SCENARIO_SHEET = "baseline"
SCENARIO_LABEL = "Primary Al ingot (kt)"

BASE_YEAR = 2019
FIRST_BGS_YEAR = 2020
LAST_BGS_YEAR = 2024
FIRST_PROJECTION_YEAR = 2025
END_YEAR = 2050

YEARS = list(range(BASE_YEAR, END_YEAR + 1))
BGS_YEARS = list(range(FIRST_BGS_YEAR, LAST_BGS_YEAR + 1))
ZIJIE_YEARS = list(range(LAST_BGS_YEAR, END_YEAR + 1))
PROJECTION_YEARS = list(range(FIRST_PROJECTION_YEAR, END_YEAR + 1))

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

# A percentage difference alone overstates discrepancies for small producers.
# Both thresholds must be exceeded for a positive-to-positive comparison.
MAJOR_RELATIVE_DIFFERENCE_PCT = 25.0
MAJOR_ABSOLUTE_DIFFERENCE_KT = 50.0

BGS_SOURCE = (
    "British Geological Survey, World Mineral Production 2020-24, "
    "Production of primary aluminium"
)
PROJECTION_METHOD = (
    "BGS 2024 country value rebased to a synthetic Zijie 2024 regional value "
    "linearly back-extrapolated from Zijie 2025-2026; Zijie regional trajectory "
    "applied from 2025 onward"
)
BGS_PUBLISHED_WORLD_TOTAL_KT = {
    2020: 65_400,
    2021: 67_800,
    2022: 69_100,
    2023: 70_700,
    2024: 73_400,
}
BGS_WORLD_TOTAL_ROUNDING_TOLERANCE_KT = 50.0


def read_old_projection():
    old = pd.read_csv(OLD_PROJECTION_PATH)
    required = {
        "Country",
        "ISO2",
        "ISO3",
        "OMNIARegion",
        "ZijieRegion",
        "Metric",
        "Unit",
        "2019",
        "2025",
    }
    missing = required - set(old.columns)
    if missing:
        raise ValueError(f"Old primary projection is missing columns: {sorted(missing)}")

    old["2019"] = pd.to_numeric(old["2019"], errors="raise")
    old["2025"] = pd.to_numeric(old["2025"], errors="raise")
    return old


def read_bgs_history():
    bgs = pd.read_csv(BGS_HISTORY_PATH, keep_default_na=False)
    required = {"BGS_Country", "ISO3", "EstimatedYears", "BGSNotes"}
    required.update(f"{year}_t" for year in BGS_YEARS)
    missing = required - set(bgs.columns)
    if missing:
        raise ValueError(f"BGS history is missing columns: {sorted(missing)}")

    if bgs["ISO3"].duplicated().any():
        duplicates = bgs.loc[bgs["ISO3"].duplicated(keep=False), "ISO3"].tolist()
        raise ValueError(f"BGS history has duplicate ISO3 codes: {duplicates}")

    for year in BGS_YEARS:
        tonnes_column = f"{year}_t"
        bgs[tonnes_column] = pd.to_numeric(bgs[tonnes_column], errors="raise")
        if bgs[tonnes_column].lt(0).any():
            raise ValueError(f"BGS history contains negative values in {tonnes_column}.")
        bgs[f"BGS{year}_kt"] = bgs[tonnes_column] / 1000
        extracted_total = bgs[f"BGS{year}_kt"].sum()
        published_total = BGS_PUBLISHED_WORLD_TOTAL_KT[year]
        if abs(extracted_total - published_total) > BGS_WORLD_TOTAL_ROUNDING_TOLERANCE_KT:
            raise ValueError(
                f"Extracted BGS {year} total ({extracted_total} kt) is not "
                f"consistent with the published rounded total ({published_total} kt)."
            )

    return bgs[
        [
            "BGS_Country",
            "ISO3",
            "EstimatedYears",
            "BGSNotes",
        ]
        + [f"BGS{year}_kt" for year in BGS_YEARS]
    ]


def read_zijie_scenario():
    raw = pd.read_excel(ZIJIE_SCENARIO_PATH, sheet_name=SCENARIO_SHEET, header=None)
    matches = raw.iloc[0].eq(SCENARIO_LABEL)
    if matches.sum() != 1:
        raise ValueError(f"Could not find one block labelled {SCENARIO_LABEL!r}.")

    start_col = int(matches[matches].index[0])
    scenario = raw.iloc[
        1:,
        start_col : start_col + 1 + len(ZIJIE_REGIONS),
    ].copy()
    scenario.columns = ["Year"] + ZIJIE_REGIONS
    scenario = scenario[scenario["Year"].isin(ZIJIE_YEARS)].copy()
    scenario["Year"] = scenario["Year"].astype(int)
    scenario[ZIJIE_REGIONS] = scenario[ZIJIE_REGIONS].apply(
        pd.to_numeric,
        errors="raise",
    )

    missing_years = sorted(set(ZIJIE_YEARS) - set(scenario["Year"]))
    if missing_years:
        raise ValueError(f"Zijie scenario is missing years: {missing_years}")

    scenario = scenario.sort_values("Year").reset_index(drop=True)
    scenario_by_year = scenario.set_index("Year")
    original_2024 = scenario_by_year.loc[LAST_BGS_YEAR, ZIJIE_REGIONS]
    zijie_2025 = scenario_by_year.loc[FIRST_PROJECTION_YEAR, ZIJIE_REGIONS]
    zijie_2026 = scenario_by_year.loc[FIRST_PROJECTION_YEAR + 1, ZIJIE_REGIONS]
    synthetic_2024 = 2 * zijie_2025 - zijie_2026

    nonpositive = synthetic_2024[synthetic_2024.le(0)]
    if not nonpositive.empty:
        raise ValueError(
            "Linear back-extrapolation gives non-positive synthetic Zijie "
            f"2024 values: {nonpositive.to_dict()}"
        )

    scenario.loc[
        scenario["Year"].eq(LAST_BGS_YEAR),
        ZIJIE_REGIONS,
    ] = synthetic_2024.to_numpy()

    diagnostic = pd.DataFrame(
        {
            "ZijieRegion": ZIJIE_REGIONS,
            "OriginalZijie2024_kt": original_2024.to_numpy(),
            "Zijie2025_kt": zijie_2025.to_numpy(),
            "Zijie2026_kt": zijie_2026.to_numpy(),
            "LinearChange2025_2026_kt": (
                zijie_2026 - zijie_2025
            ).to_numpy(),
            "SyntheticZijie2024_kt": synthetic_2024.to_numpy(),
        }
    )
    diagnostic["SyntheticMinusOriginal2024_kt"] = (
        diagnostic["SyntheticZijie2024_kt"]
        - diagnostic["OriginalZijie2024_kt"]
    )
    diagnostic["ImpliedGrowth2024_2025_pct"] = (
        diagnostic["Zijie2025_kt"]
        / diagnostic["SyntheticZijie2024_kt"]
        - 1
    ) * 100
    diagnostic["Method"] = (
        "Synthetic 2024 = 2 * Zijie 2025 - Zijie 2026"
    )

    return scenario, diagnostic


def classify_misalignment(omnia_2019, bgs_2020):
    difference = bgs_2020 - omnia_2019
    absolute_difference = abs(difference)

    if omnia_2019 == 0 and bgs_2020 == 0:
        return "No production in either source", False

    if omnia_2019 == 0:
        major = absolute_difference >= MAJOR_ABSOLUTE_DIFFERENCE_KT
        label = "BGS producer absent from OMNIA 2019"
        return (f"Major: {label}" if major else f"Review: {label}"), major

    if bgs_2020 == 0:
        major = absolute_difference >= MAJOR_ABSOLUTE_DIFFERENCE_KT
        label = "OMNIA 2019 producer absent or nil in BGS 2020"
        return (f"Major: {label}" if major else f"Review: {label}"), major

    relative_difference = absolute_difference / omnia_2019 * 100
    major = (
        absolute_difference >= MAJOR_ABSOLUTE_DIFFERENCE_KT
        and relative_difference >= MAJOR_RELATIVE_DIFFERENCE_PCT
    )
    if major:
        return "Major: difference exceeds absolute and relative thresholds", True
    if relative_difference >= MAJOR_RELATIVE_DIFFERENCE_PCT:
        return "Review: relative threshold exceeded", False
    if absolute_difference >= MAJOR_ABSOLUTE_DIFFERENCE_KT:
        return "Review: absolute threshold exceeded", False
    return "Within thresholds", False


def make_misalignment_report(output):
    report = output[
        [
            "Country",
            "ISO3",
            "OMNIARegion",
            "ZijieRegion",
            "OMNIA2019_kt",
            "HistoricalSource2019",
            "BGS2020_kt",
            "BGSRecordPresent",
            "BGS_Country",
            "EstimatedYears",
            "BGSNotes",
        ]
    ].copy()
    report = report[
        report["OMNIA2019_kt"].gt(0) | report["BGSRecordPresent"]
    ].copy()

    report["Difference_kt"] = report["BGS2020_kt"] - report["OMNIA2019_kt"]
    report["AbsoluteDifference_kt"] = report["Difference_kt"].abs()
    report["Difference_pct_of_OMNIA2019"] = np.where(
        report["OMNIA2019_kt"].ne(0),
        report["Difference_kt"] / report["OMNIA2019_kt"] * 100,
        np.nan,
    )

    classifications = report.apply(
        lambda row: classify_misalignment(
            row["OMNIA2019_kt"],
            row["BGS2020_kt"],
        ),
        axis=1,
    )
    report["MisalignmentStatus"] = [item[0] for item in classifications]
    report["MajorMisalignment"] = [item[1] for item in classifications]
    report["BGS2020Estimated"] = report["EstimatedYears"].apply(
        lambda years: "2020" in str(years).split(";")
    )
    report["MajorRelativeThreshold_pct"] = MAJOR_RELATIVE_DIFFERENCE_PCT
    report["MajorAbsoluteThreshold_kt"] = MAJOR_ABSOLUTE_DIFFERENCE_KT

    return report.sort_values(
        ["MajorMisalignment", "AbsoluteDifference_kt"],
        ascending=[False, False],
    ).reset_index(drop=True)


def build_projection():
    old = read_old_projection()
    bgs = read_bgs_history()
    scenario, rebase_diagnostic = read_zijie_scenario()

    bgs_not_in_omnia = sorted(set(bgs["ISO3"]) - set(old["ISO3"]))
    if bgs_not_in_omnia:
        raise ValueError(f"BGS countries missing from OMNIA projection: {bgs_not_in_omnia}")

    output = old[
        [
            "Country",
            "ISO2",
            "ISO3",
            "OMNIARegion",
            "ZijieRegion",
            "Metric",
            "Unit",
            "2019",
            "2025",
        ]
    ].rename(
        columns={
            "2019": "OMNIA2019_kt",
            "2025": "OldApproach2025_kt",
        }
    )
    output = output.merge(bgs, on="ISO3", how="left", validate="many_to_one")
    output["BGSRecordPresent"] = output["BGS_Country"].notna()
    output["BGS_Country"] = output["BGS_Country"].fillna("")
    output["EstimatedYears"] = output["EstimatedYears"].fillna("")
    output["BGSNotes"] = output["BGSNotes"].fillna("")

    for year in BGS_YEARS:
        output[f"BGS{year}_kt"] = output[f"BGS{year}_kt"].fillna(0)

    for year in YEARS:
        output[year] = 0.0

    output[BASE_YEAR] = output["OMNIA2019_kt"]
    for year in BGS_YEARS:
        output[year] = output[f"BGS{year}_kt"]

    scenario_by_year = scenario.set_index("Year")
    for year in PROJECTION_YEARS:
        growth_by_region = {
            region: (
                scenario_by_year.at[year, region]
                / scenario_by_year.at[LAST_BGS_YEAR, region]
            )
            for region in ZIJIE_REGIONS
        }
        output[year] = (
            output[f"BGS{LAST_BGS_YEAR}_kt"]
            * output["ZijieRegion"].map(growth_by_region)
        )

    output["AlignmentFactor_vs_old_2025"] = np.where(
        output["OldApproach2025_kt"].ne(0),
        output[FIRST_PROJECTION_YEAR] / output["OldApproach2025_kt"],
        np.nan,
    )
    output["HistoricalSource2019"] = "OMNIA INF_Data"
    output.loc[
        output["ISO3"].eq("JPN") & output["OMNIA2019_kt"].gt(0),
        "HistoricalSource2019",
    ] = "Zijie back-extrapolated fallback used by old approach"
    output["HistoricalSource2020_2024"] = BGS_SOURCE
    output["ProjectionMethod2025_2050"] = PROJECTION_METHOD

    report = make_misalignment_report(output)

    output = output[
        [
            "Country",
            "ISO2",
            "ISO3",
            "OMNIARegion",
            "ZijieRegion",
            "Metric",
            "Unit",
            "OMNIA2019_kt",
            "BGSRecordPresent",
            "BGS_Country",
            "EstimatedYears",
            "BGSNotes",
            "AlignmentFactor_vs_old_2025",
            "HistoricalSource2019",
            "HistoricalSource2020_2024",
            "ProjectionMethod2025_2050",
        ]
        + YEARS
    ]

    return output, report, bgs, scenario, rebase_diagnostic


def validate_projection(output, bgs, scenario):
    for year in BGS_YEARS:
        output_total = output[year].sum()
        bgs_total = bgs[f"BGS{year}_kt"].sum()
        if abs(output_total - bgs_total) > 1e-6:
            raise ValueError(
                f"Output {year} total does not match BGS. "
                f"Output={output_total}, BGS={bgs_total}"
            )

    scenario_by_year = scenario.set_index("Year")
    for region in ZIJIE_REGIONS:
        region_output = output[output["ZijieRegion"].eq(region)]
        anchor = region_output[LAST_BGS_YEAR].sum()
        for year in PROJECTION_YEARS:
            expected = (
                anchor
                * scenario_by_year.at[year, region]
                / scenario_by_year.at[LAST_BGS_YEAR, region]
            )
            difference = region_output[year].sum() - expected
            if abs(difference) > 1e-6:
                raise ValueError(
                    f"Aligned total check failed for {region}, {year}: {difference}"
                )


def main():
    output, report, bgs, scenario, rebase_diagnostic = build_projection()
    validate_projection(output, bgs, scenario)

    OUTPUTS_DIR.mkdir(exist_ok=True)
    output.to_csv(OUTPUT_CSV, index=False)
    report.to_csv(MISALIGNMENT_CSV, index=False)
    rebase_diagnostic.to_csv(ZIJIE_REBASE_DIAGNOSTIC_CSV, index=False)

    major = report[report["MajorMisalignment"]]
    print(f"Saved: {OUTPUT_CSV}")
    print(f"Saved: {MISALIGNMENT_CSV}")
    print(f"Saved: {ZIJIE_REBASE_DIAGNOSTIC_CSV}")
    print(f"Rows: {len(output)}")
    print(f"BGS producer records: {len(bgs)}")
    print(f"Major OMNIA 2019 vs BGS 2020 misalignments: {len(major)}")
    if not major.empty:
        print(
            major[
                [
                    "Country",
                    "OMNIA2019_kt",
                    "BGS2020_kt",
                    "Difference_pct_of_OMNIA2019",
                    "MisalignmentStatus",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
