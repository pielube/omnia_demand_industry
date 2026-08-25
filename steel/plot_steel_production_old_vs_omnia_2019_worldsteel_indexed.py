"""Plot original and OMNIA-2019-anchored WSA-indexed steel projections."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import StrMethodFormatter
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

ORIGINAL_CSV = OUTPUTS_DIR / "steel_production_omnia.csv"
INDEXED_CSV = (
    OUTPUTS_DIR / "steel_production_omnia_2019_anchored_worldsteel_indexed.csv"
)
AUDIT_CSV = (
    OUTPUTS_DIR
    / "steel_production_omnia_2019_anchored_worldsteel_indexed_audit.csv"
)
OUTPUT_STEM = (
    FIGURES_DIR
    / "steel_production_omnia_old_vs_2019_anchored_worldsteel_indexed_2019_2050"
)

FIRST_YEAR = 2019
LAST_YEAR = 2050
HISTORICAL_YEARS = list(range(2020, 2026))
FUTURE_ANCHOR_YEAR = 2025
FIRST_FUTURE_YEAR = 2026
YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
YEAR_COLUMNS = [str(year) for year in YEARS]
KT_PER_MT = 1000.0

REGION_LABELS = {
    "AFE": "Eastern Africa",
    "AFN": "Northern Africa",
    "AFW": "Western Africa",
    "AFZ": "Southern Africa",
    "NIG": "Nigeria",
    "RUS": "Russian Federation",
    "ASC": "Central Asia",
    "ASE": "Southeast Asia",
    "CHN": "China Mainland",
    "IDN": "Indonesia, Philippines, Viet Nam",
    "IND": "India",
    "ASO": "South Asia",
    "JPN": "Japan",
    "SKT": "South Korea and Taiwan",
    "ANZ": "Australia and New Zealand",
    "USA": "United States",
    "CAN": "Canada",
    "LAM": "Latin America",
    "BRA": "Brazil",
    "MEX": "Mexico",
    "CHL": "Chile",
    "ENE": "Non-EU Eastern Europe",
    "ENW": "Non-EU Western Europe",
    "EUE": "Eastern EU",
    "EUW": "Western EU",
    "EUM": "Mediterranean EU",
    "MEA": "Middle East (Gulf States)",
    "MDA": "Mediterranean Asia",
}

ORIGINAL_COLOR = "#6B7280"
INDEXED_COLOR = "#0072B2"
HISTORICAL_COLOR = "#D55E00"
OMNIA_ANCHOR_COLOR = "#009E73"
HISTORICAL_SPAN_COLOR = "#FDE68A"


def read_projection(path: Path) -> pd.DataFrame:
    """Read and validate one OMNIA production projection."""
    projection = pd.read_csv(path)
    required_columns = ["OMNIARegion", *YEAR_COLUMNS]
    if projection.columns.tolist() != required_columns:
        raise ValueError(
            f"Unexpected columns in {path.name}: {projection.columns.tolist()}"
        )
    if projection["OMNIARegion"].duplicated().any():
        duplicates = projection.loc[
            projection["OMNIARegion"].duplicated(keep=False), "OMNIARegion"
        ].tolist()
        raise ValueError(f"Duplicate regions in {path.name}: {duplicates}")

    projection[YEAR_COLUMNS] = projection[YEAR_COLUMNS].apply(
        pd.to_numeric, errors="raise"
    )
    values = projection[YEAR_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"Invalid production values in {path.name}")
    return projection.set_index("OMNIARegion")


def read_audit() -> pd.DataFrame:
    """Read the calculation audit and validate its plotted values."""
    audit = pd.read_csv(AUDIT_CSV, keep_default_na=False)
    required = {
        "OMNIARegion",
        "RebaseApplied",
        "ConfidenceFlag",
        "LowProductionCoverageFlag",
        "FutureAnchorYear",
        "DerivedOMNIA2025_kt",
        "Post2025ScaleFactor",
        "Rebased2025To2026Change_pct",
        "Original2025To2026Change_pct",
        "HandoffGrowthDifference_pp",
        *{f"Rebased{year}_kt" for year in range(2019, 2026)},
    }
    missing = required - set(audit.columns)
    if missing:
        raise ValueError(f"Audit file is missing columns: {sorted(missing)}")
    if audit["OMNIARegion"].duplicated().any():
        raise ValueError("Duplicate OMNIA regions in indexed-production audit")

    value_columns = [f"Rebased{year}_kt" for year in range(2019, 2026)]
    audit[value_columns] = audit[value_columns].apply(
        pd.to_numeric, errors="raise"
    )
    calculation_columns = [
        "FutureAnchorYear",
        "DerivedOMNIA2025_kt",
        "Post2025ScaleFactor",
        "Rebased2025To2026Change_pct",
        "Original2025To2026Change_pct",
        "HandoffGrowthDifference_pp",
    ]
    audit[calculation_columns] = audit[calculation_columns].apply(
        pd.to_numeric, errors="raise"
    )
    values = audit[value_columns].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid rebased values in indexed-production audit")
    return audit.set_index("OMNIARegion")


def validate_inputs(
    original: pd.DataFrame,
    indexed: pd.DataFrame,
    audit: pd.DataFrame,
) -> list[str]:
    """Validate the rebase invariants and return regions ordered by 2025 output."""
    if original.index.tolist() != indexed.index.tolist():
        raise ValueError("Original and indexed OMNIA regions do not match")
    if set(original.index) != set(REGION_LABELS):
        raise ValueError(
            "Projection regions do not match plot labels: "
            f"{sorted(original.index)} vs {sorted(REGION_LABELS)}"
        )
    if set(audit.index) != set(original.index):
        raise ValueError(
            "Audit does not cover all projection regions: "
            f"{sorted(audit.index)} vs {sorted(original.index)}"
        )
    if not audit["RebaseApplied"].eq("yes").all():
        skipped = audit.index[~audit["RebaseApplied"].eq("yes")].tolist()
        raise ValueError(f"Figure expects every region to be rebased: {skipped}")
    if not audit["FutureAnchorYear"].eq(FUTURE_ANCHOR_YEAR).all():
        raise ValueError("Audit does not use 2025 as every region's future anchor")

    if not np.allclose(
        original["2019"].to_numpy(dtype=float),
        indexed["2019"].to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-8,
    ):
        raise ValueError("Indexed projection does not retain OMNIA 2019 values")

    for year in range(2019, 2026):
        audited = audit[f"Rebased{year}_kt"].reindex(indexed.index).to_numpy(float)
        actual = indexed[str(year)].to_numpy(float)
        if not np.allclose(actual, audited, rtol=0.0, atol=1e-9):
            raise ValueError(f"Audit and indexed projection disagree in {year}")

    derived_anchor = audit["DerivedOMNIA2025_kt"].reindex(indexed.index)
    if not np.allclose(
        indexed["2025"].to_numpy(float),
        derived_anchor.to_numpy(float),
        rtol=0.0,
        atol=1e-9,
    ):
        raise ValueError("Audit and indexed projection disagree at the 2025 anchor")

    expected_scale = indexed["2025"] / original["2025"]
    audited_scale = audit["Post2025ScaleFactor"].reindex(indexed.index)
    if not np.allclose(
        expected_scale.to_numpy(float),
        audited_scale.to_numpy(float),
        rtol=1e-12,
        atol=1e-12,
    ):
        raise ValueError("Audit contains an incorrect post-2025 scale factor")

    original_handoff = (original["2026"] / original["2025"] - 1.0) * 100.0
    indexed_handoff = (indexed["2026"] / indexed["2025"] - 1.0) * 100.0
    audited_original_handoff = audit[
        "Original2025To2026Change_pct"
    ].reindex(indexed.index)
    audited_indexed_handoff = audit[
        "Rebased2025To2026Change_pct"
    ].reindex(indexed.index)
    if not np.allclose(
        original_handoff.to_numpy(float),
        audited_original_handoff.to_numpy(float),
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError("Audit contains an incorrect original 2025-2026 change")
    if not np.allclose(
        indexed_handoff.to_numpy(float),
        audited_indexed_handoff.to_numpy(float),
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError("Audit contains an incorrect rebased 2025-2026 change")
    if not np.allclose(
        indexed_handoff.to_numpy(float),
        original_handoff.to_numpy(float),
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError("The 2025-2026 handoff does not preserve original growth")
    if not np.allclose(
        audit["HandoffGrowthDifference_pp"].to_numpy(float),
        0.0,
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError("Audit reports a non-zero 2025-2026 growth difference")

    future_years = [str(year) for year in range(FIRST_FUTURE_YEAR, LAST_YEAR + 1)]
    original_shape = original[future_years].div(
        original[str(FUTURE_ANCHOR_YEAR)], axis=0
    )
    indexed_shape = indexed[future_years].div(
        indexed[str(FUTURE_ANCHOR_YEAR)], axis=0
    )
    if not np.allclose(
        original_shape.to_numpy(dtype=float),
        indexed_shape.to_numpy(dtype=float),
        rtol=1e-11,
        atol=1e-12,
    ):
        raise ValueError("Post-2025 path is not rebased from the 2025 anchor")

    return indexed["2025"].sort_values(ascending=False).index.tolist()


def plot_comparison(
    original: pd.DataFrame,
    indexed: pd.DataFrame,
    audit: pd.DataFrame,
    regions: list[str],
) -> plt.Figure:
    """Build a four-column comparison for all OMNIA regions."""
    columns = 4
    rows = int(np.ceil(len(regions) / columns))
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(22, 26),
        sharex=True,
        constrained_layout=False,
    )
    axes = np.atleast_1d(axes).ravel()

    historical_columns = [str(year) for year in HISTORICAL_YEARS]
    for axis, region in zip(axes, regions):
        original_values = original.loc[region, YEAR_COLUMNS].to_numpy(float) / KT_PER_MT
        indexed_values = indexed.loc[region, YEAR_COLUMNS].to_numpy(float) / KT_PER_MT

        axis.axvspan(
            2019.5,
            2025.5,
            color=HISTORICAL_SPAN_COLOR,
            alpha=0.25,
            linewidth=0,
            zorder=0,
        )
        axis.plot(
            YEARS,
            original_values,
            color=ORIGINAL_COLOR,
            linestyle="--",
            linewidth=1.8,
            zorder=2,
        )
        axis.plot(
            YEARS,
            indexed_values,
            color=INDEXED_COLOR,
            linewidth=2.2,
            zorder=3,
        )
        axis.scatter(
            HISTORICAL_YEARS,
            indexed.loc[region, historical_columns].to_numpy(float) / KT_PER_MT,
            color=HISTORICAL_COLOR,
            edgecolor="white",
            linewidth=0.55,
            s=25,
            zorder=4,
        )
        axis.scatter(
            [2019],
            [indexed.at[region, "2019"] / KT_PER_MT],
            marker="D",
            color=OMNIA_ANCHOR_COLOR,
            edgecolor="white",
            linewidth=0.65,
            s=37,
            zorder=5,
        )
        low_coverage = audit.at[region, "LowProductionCoverageFlag"] == "yes"
        title = f"{region} - {REGION_LABELS[region]}"
        if low_coverage:
            title += " [low coverage]"
        axis.set_title(
            title,
            loc="left",
            fontsize=9.9,
            color="#9A3412" if low_coverage else "#111827",
            pad=6,
        )
        axis.set_xlim(FIRST_YEAR, LAST_YEAR)
        axis.set_xticks([2019, 2025, 2030, 2040, 2050])
        axis.tick_params(axis="x", labelbottom=True, labelsize=8.3)
        axis.tick_params(axis="y", labelsize=8.3)
        axis.grid(axis="both", color="#D1D5DB", linewidth=0.65, alpha=0.65)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

        low = min(original_values.min(), indexed_values.min())
        high = max(original_values.max(), indexed_values.max())
        padding = max((high - low) * 0.10, high * 0.015, 0.02)
        axis.set_ylim(max(0.0, low - padding), high + padding)
        if high < 1:
            y_format = "{x:,.2f}"
        elif high < 10:
            y_format = "{x:,.1f}"
        else:
            y_format = "{x:,.0f}"
        axis.yaxis.set_major_formatter(StrMethodFormatter(y_format))

    for axis in axes[len(regions) :]:
        axis.set_visible(False)

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=ORIGINAL_COLOR,
            linestyle="--",
            linewidth=1.8,
            label="Original OMNIA projection",
        ),
        Line2D(
            [0],
            [0],
            color=INDEXED_COLOR,
            linewidth=2.2,
            label="OMNIA-2019-anchored projection",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="none",
            markerfacecolor=OMNIA_ANCHOR_COLOR,
            markeredgecolor="white",
            markersize=6,
            label="OMNIA 2019 anchor",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=HISTORICAL_COLOR,
            markeredgecolor="white",
            markersize=6,
            label="WSA-indexed 2020-2025",
        ),
    ]

    figure.suptitle(
        "Steel production: original vs OMNIA-2019-anchored WSA index",
        fontsize=19,
        fontweight="bold",
        y=0.991,
    )
    figure.text(
        0.5,
        0.976,
        "2019 retains OMNIA levels; 2020-2025 follow WSA changes; "
        "2026 onward preserves original post-2025 growth",
        ha="center",
        fontsize=10.8,
        color="#374151",
    )
    figure.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.962),
        ncol=4,
        frameon=False,
        fontsize=9.2,
    )
    figure.supylabel("Crude steel production (Mt)", x=0.012, fontsize=12)
    figure.supxlabel("Year", y=0.018, fontsize=12)
    figure.text(
        0.5,
        0.006,
        "Sources: calibrated OMNIA 2019 production; WSA country production "
        "for 2019-2025. Regional WSA indices use fixed country baskets; "
        "orange titles flag <75% production coverage in a reference vintage.",
        ha="center",
        fontsize=8.8,
        color="#4B5563",
    )
    figure.tight_layout(rect=(0.025, 0.033, 0.995, 0.942), h_pad=1.9, w_pad=1.25)
    return figure


def main() -> None:
    original = read_projection(ORIGINAL_CSV)
    indexed = read_projection(INDEXED_CSV)
    audit = read_audit()
    regions = validate_inputs(original, indexed, audit)

    figure = plot_comparison(original, indexed, audit, regions)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_STEM.with_suffix(".pdf")
    png_path = OUTPUT_STEM.with_suffix(".png")
    figure.savefig(pdf_path, bbox_inches="tight")
    figure.savefig(png_path, dpi=220, bbox_inches="tight")
    plt.close(figure)

    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")
    print(f"Regions plotted: {', '.join(regions)}")


if __name__ == "__main__":
    main()
