"""Create TIAM equivalents of aluminium and cement OMNIA regional CSVs."""

from pathlib import Path

import pandas as pd

from tiam_projection_utils import (
    REPO_DIR,
    YEARS,
    aggregate_country_projection,
    calculate_growth_rates,
    read_tiam_mapping,
    validate_global_totals,
)


ALUMINIUM_ZERO_VOLUME_ALIASES = {"GUY", "LIE"}
CEMENT_MISSING_OBSERVATIONS = {
    "MAC": [str(year) for year in range(2019, 2025)],
    "SDN": [str(year) for year in range(2020, 2025)],
}


def read_country_projection(path: Path, sector: str) -> pd.DataFrame:
    """Read sector volumes; cement files also contain population rows."""
    source = pd.read_csv(path)
    if sector == "cement":
        missing = {"Metric", "Unit"} - set(source.columns)
        if missing:
            raise ValueError(f"Cement country projection is missing {sorted(missing)}")
        source = source.loc[source["Metric"].eq("Cement production")].copy()
        if source.empty:
            raise ValueError(f"No cement production rows found in {path}")
        if not source["Unit"].eq("kt cement").all():
            raise ValueError("Expected cement production values in 'kt cement'")
        # Match existing OMNIA sums, which contribute zero for these missing
        # observations. This policy is limited to the known source gaps.
        permitted_missing = pd.DataFrame(False, index=source.index, columns=YEARS)
        for iso3, missing_years in CEMENT_MISSING_OBSERVATIONS.items():
            permitted_missing.loc[source["ISO3"].eq(iso3), missing_years] = True
        source[YEARS] = source[YEARS].mask(source[YEARS].isna() & permitted_missing, 0.0)
    elif sector == "aluminium":
        # Existing source files have two country-name aliases for GUY and LIE.
        # All four rows are zero throughout 2019-2050. Consolidate only these
        # documented zero-volume aliases; nonzero or new duplicates are errors.
        source["ISO3"] = source["ISO3"].fillna("").astype(str).str.strip().str.upper()
        duplicate_rows = source["ISO3"].duplicated(keep=False)
        duplicate_codes = set(source.loc[duplicate_rows, "ISO3"])
        unexpected = duplicate_codes - ALUMINIUM_ZERO_VOLUME_ALIASES
        if unexpected:
            raise ValueError(f"Unexpected duplicate aluminium ISO3 rows: {sorted(unexpected)}")
        if duplicate_codes:
            aliases = source.loc[duplicate_rows]
            volumes = aliases[YEARS].apply(pd.to_numeric, errors="raise")
            if volumes.ne(0).any().any():
                raise ValueError("Duplicate aluminium aliases must all have zero annual volumes")
            if aliases.groupby("ISO3")["OMNIARegion"].nunique(dropna=False).ne(1).any():
                raise ValueError("Duplicate aluminium aliases disagree on their source OMNIA region")
            original = source
            source = source.drop_duplicates(subset="ISO3", keep="first").copy()
            validate_global_totals(source, original, label="Consolidated aluminium aliases")
    return source


def build_outputs(
    mapping: pd.DataFrame,
    repo_dir: Path = REPO_DIR,
) -> dict[Path, pd.DataFrame]:
    """Build every current aluminium/cement regional CSV without writing files."""
    result = {}
    for sector in ("aluminium", "cement"):
        output_dir = Path(repo_dir) / sector / "outputs"
        originals = set(output_dir.rglob("*omnia*.csv"))
        accounted_for = set()
        for omnia_path in sorted(output_dir.rglob("*_omnia.csv")):
            country_path = omnia_path.with_name(omnia_path.name.replace("_omnia.csv", "_country.csv"))
            source = read_country_projection(country_path, sector)
            totals = aggregate_country_projection(source, mapping)
            validate_global_totals(
                totals,
                pd.read_csv(omnia_path),
                label=f"TIAM and OMNIA {omnia_path.relative_to(repo_dir)}",
            )
            tiam_path = omnia_path.with_name(omnia_path.name.replace("omnia", "tiam"))
            result[tiam_path] = totals
            accounted_for.add(omnia_path)
            growth_path = omnia_path.with_name(omnia_path.stem + "_growth_rates.csv")
            if growth_path in originals:
                result[growth_path.with_name(growth_path.name.replace("omnia", "tiam"))] = (
                    calculate_growth_rates(totals)
                )
                accounted_for.add(growth_path)
        unsupported = originals - accounted_for
        if unsupported:
            raise ValueError(
                f"No country-source workflow for OMNIA outputs: {sorted(map(str, unsupported))}"
            )
        if not originals:
            raise ValueError(f"No OMNIA CSV outputs found in {output_dir}")
    return result


def main() -> None:
    outputs = build_outputs(read_tiam_mapping())
    for path, frame in outputs.items():
        frame.to_csv(path, index=False)
        print(f"Saved: {path.relative_to(REPO_DIR)}")


if __name__ == "__main__":
    main()
